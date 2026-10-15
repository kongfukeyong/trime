# MVP 构建与验证

本页只记录构建事实。APK 静态验证、规则单元测试与 Android 安装/输入法运行验证是不同层次；目前没有连接的 ADB 设备，不能声称安装或端到端输入通过。

## 工具链

| 项目 | 固定值 |
| --- | --- |
| 源码 / 原生库来源 | Trime v3.3.12，官方 release `e09ac711` |
| Android Gradle Plugin | 9.2.1 |
| Gradle wrapper | 9.4.1 bin |
| Java | JDK 21（本地 Temurin 21.0.12.1） |
| Android SDK | platform android-36、build-tools 36.0.0 |
| Kotlin / KSP | 2.3.21 / 2.3.6 |
| 资源导入工具 | Python 3.11+，PyYAML 6.0.3 |
| MVP ABI | arm64-v8a、x86_64 |

上游为 AGP 9.3.0 / Gradle 9.5.1。本机整包依赖下载严重停滞后，经授权改为已缓存的 AGP 9.2.1 / Gradle 9.4.1；没有改变 IME、Rime 或万象技术选型。后续分段下载也取得并核验了 Gradle 9.5.1，但项目仍保持上述固定工具链，避免本地与 CI 漂移。

## 干净 Windows 构建

以下命令在仓库根目录执行，需要 PowerShell、curl.exe、JDK21、Python 和 Android SDK。构建期间允许下载依赖；APK 不允许申请 INTERNET 权限。

```powershell
python -m pip install 'PyYAML==6.0.3'
sdkmanager 'platforms;android-36' 'build-tools;36.0.0'
python scripts/download-wanxiang.py
python scripts/import-wanxiang.py
python scripts/verify-wanxiang.py
./scripts/build-mvp.ps1 -JavaHome $env:JAVA_HOME -AndroidSdk $env:ANDROID_HOME -OutputDir outputs -RunTests
```

逐条检查命令退出码。`build-mvp.ps1` 自身也先执行严格资源验证，缺失模型、资源哈希不一致或依赖不全会立即失败。不要把 `import-wanxiang.py --allow-missing-model` 的暂存结果当作可打包资源。

参数：

| 参数 | 用途 |
| --- | --- |
| `-JavaHome` | 必填，JDK21 安装目录 |
| `-AndroidSdk` | 必填，SDK 根目录 |
| `-OutputDir` | APK 与报告目录；默认仓库同级 `outputs`，CI 建议显式传入 |
| `-Gradle` | 可选，已有 `gradle.bat` 的绝对路径；默认仓库 wrapper |
| `-ProxyUrl` | 可选，下载与 Gradle HTTP(S) 代理；不要在 CI 固定本机地址 |
| `-RunTests` | 同时运行 `:app:testDebugUnitTest` |

JDK、SDK 和可选 Gradle 安装路径通过参数传入，可复用本机已有工具链，无需使用特定个人目录。

## 原生库与资源来源

`prepare-mvp-native.ps1` 只从固定的 [官方 v3.3.12 release](https://github.com/osfans/trime/releases/tag/v3.3.12) 下载 APK，使用 [GitHub release API](https://api.github.com/repos/osfans/trime/releases/tags/v3.3.12) 返回并固定在脚本内的 SHA-256 校验整包，失败即停止。没有在应用内添加下载逻辑。

| 官方 APK ABI | 固定 SHA-256 |
| --- | --- |
| arm64-v8a | `c727d509cbae8ba6a6b3616f57ea299d46bb13072812342811d03aea0bc3cb98` |
| x86_64 | `0b32fee993f59614a69269aea30f817c48d7af67b35965ed4eb107e68340ee6f` |

提取内容为每个 ABI 的 `.so` 和 arm64 官方 APK 全部 `assets/shared/` fallback。逐文件 SHA 和来源 URL 写入 `app/build/mvp-prebuilt/provenance.json`。本地两个官方 APK 均已通过整包 SHA 和 apksigner v1/v2 验证，证书 SHA-256 均为 `39f51b81bc3e0eeb7c3ae381755e33bdbf6bd9f4623719ca9ed82392f81a06a8`。重打包后的 debug APK 使用本地 debug 签名，不能当作官方签名升级包。

`-PmvpPrebuiltDir=app/build/mvp-prebuilt` 是显式开关；此模式跳过 CMake，保留原始 `.so` 字节，使用 `stageMvpAssets` 将资源复制至 `app/build/generated/mvpAssets`。真实源码资源优先，官方 shared 数据兜底。小于 256 字节、trim 后以 `../../../../data/rime/` 开头的 Windows/archive 符号链接占位文件会被排除。检查 stage 内真实 `shared/default.yaml` 与所有占位文件，再生成 checksums.json；不改写源码 assets。构建脚本也检查最终 APK 的同一问题。

## 完整 C++ 源码构建回退

不传 `mvpPrebuiltDir` 即保留上游源码构建流程；上游旧的 `app/prebuilt` 目录机制也保留，因此完整源码构建时应确保该目录不存在。MVP 使用 `app/build/mvp-prebuilt`，不会自动触发旧机制。

源码归档本身不含子模块内容。需要可用 Git checkout、递归子模块以及真实符号链接；Windows 应启用开发者模式/符号链接权限，或者在 Linux/WSL 的原生文件系统中重新 clone。不要把 Windows 的几字节 symlink 占位当作 YAML。

```sh
git submodule update --init --recursive
# 上游 Makefile 的 patch-apply 等价步骤；只对尚未应用的干净子模块执行一次。
git apply --directory=app/src/main/jni/librime-lua-deps patches/lua.patch
sdkmanager 'ndk;28.0.13004108' 'cmake;3.31.6' 'platforms;android-36' 'build-tools;36.0.0'
./gradlew :app:assembleDebug -PbuildABI=arm64-v8a,x86_64
```

Windows 使用 `./gradlew.bat`，并确保 OpenCC 脚本调用的 `python3` 可执行。本机已有 NDK 28.2.13676358 / CMake 3.22.1，若要显式覆盖则添加 `-PndkVersion=28.2.13676358 -PcmakeVersion=3.22.1`，但该组合未做完整 C++ 构建验证。上游源码默认值仍是 NDK 28.0.13004108 / CMake 3.31.6。完整子模块 C++ 构建尚未实际执行，不声称此回退已经通过。

## 验证记录与产物

2026-10-15 09:07（Asia/Shanghai），本地 `build-mvp.ps1 -RunTests` 完成并退出 0，Gradle 输出 `BUILD SUCCESSFUL in 1m 19s`，59 个任务中 17 个实际执行、42 个复用缓存。主代码 Kotlin/Java 编译、双 ABI 打包及完整 JVM 单元测试均通过：**9 个测试类、44 项测试、0 失败、0 错误、0 跳过**，包含 `LanguageSwitchPolicyTest` 的 9 项语言切换用例。详见 outputs/unit-test-summary.json 和 app/build/reports/tests/testDebugUnitTest/。

此前一次命令已产出 APK，但因上游四个旧测试文件的 Kotlin 兼容/API 失配导致整体失败；主代理/测试代理修复后才取得上述成功结果。原失败日志保存在 outputs/build-mvp-before-test-fix.log，没有将失败命令当作测试通过。

本次基于共享工作目录构建。生成的 `BuildConfig.BUILD_COMMIT_HASH` 为 `e5920554d89d428d414266764741eb966ad31551`（配置时读取）；构建结束时主代理已将工作目录改动提交为 `1e7f839914da20b559172992cb8a89483f85f1b2`。因此不要将本机 APK 说成对 `1e7f839` 的干净检出重建；该提交的云构建由主代理另行追踪。

实际 `stageMvpAssets` / `generateDataChecksums` / `mergeDebugAssets` 已通过。独立复核确认 14 个路径占位均替换为官方真实数据、68 个万象资源 SHA 一致、114 个暂存文件与 checksums.json 一致，且没有四层路径占位；报告为 outputs/stage-validation.json。`shared/default.yaml` SHA-256 为 `dd55653a991f9418eb425ee2112666f82e3e753c5ce3ed5702dd243041a45382`。CI 的 dangling symlink 也由 staging 显式排除，再使用官方 fallback；本机此次验证的是 Windows 路径文本占位形态。

最终 APK 均为 `com.osfans.trime.debug`，版本名 3.3.12、版本号 20260901、最低 SDK21。以下文件已复制至仓库同级 outputs：

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| com.osfans.trime-v3.3.12-mvp-arm64-v8a-debug.apk | 410129863 | `13416938830bfd8f3cf1536cbf41f35bc1f2fdd52db24b2d5fb34c3ff1c7b941` |
| com.osfans.trime-v3.3.12-mvp-x86_64-debug.apk | 410209571 | `7d21c4bed30db489a35766893fcdaeee154d09531812dd8bc30529cd840b89de` |

两个 APK 的 apksigner v1/v2 签名验证、zipalign、原生 `.so` 与官方提取文件 SHA 一致性、全部 68 个万象文件 SHA、114 个 assets 校验项及真实 default.yaml 检查均通过。无 INTERNET 权限；保留上游依赖合并的 ACCESS_NETWORK_STATE（仅查询网络状态）。本机 debug 签名证书 SHA-256 为 `d3e2d64b928983f82cfa9eba768eeabd6b99d7f908fd1209b211b8e5fca185ba`。这些是可供安装验证的已签名 APK，不代表已在 Android 上成功安装/运行。

outputs 包含两个 debug APK、`build-mvp.log`、`apk-sha256.txt`、`native-provenance.json`、`apk-validation.json`、`stage-validation.json` 与 `unit-test-summary.json`。构建脚本仅在 Gradle 与所有 APK 静态校验成功后复制两个 APK。已有 APK 可单独调用 `./scripts/verify-mvp-apks.ps1 -AndroidSdk $env:ANDROID_HOME -OutputDir ../outputs` 校验，无需重跑 Gradle（apksigner 仍需 JAVA_HOME）。本机过程状态另外写入仓库同级 `work/build-status.txt`。

`adb devices -l` 当前为空。仅发现 Wear OS AVD 配置，没有可用的已运行手机模拟器；没有安装或启动本次 APK，也没有验证系统 IME 切换、实际 Rime 部署、候选上屏、隐私输入或目标设备兼容性。取得 APK 后仍需真机/手机模拟器端到端验证。
