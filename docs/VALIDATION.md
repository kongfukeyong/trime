# MVP 交付验证

验证日期：2026-10-15。实现基于 Trime v3.3.12；不修改 Rime/JNI C++。

## 本地构建与测试：通过

- `build-mvp.ps1 -RunTests` 退出 0，主应用 Kotlin/Java 编译和两个 ABI 的 debug APK 打包通过。
- 9 个测试类共 **44 项通过，0 失败、0 错误、0 跳过**；其中语言切换策略 9 项。
- 两包的 apksigner、zipalign、官方原生库字节 SHA、68 个万象资源 SHA 和 114 项 assets 校验均通过。
- 最终 APK 不申请 `android.permission.INTERNET`。模型和词库均随包提供，运行时不下载资源。
- 本地生成的 BuildConfig 标记源码提交 `e5920554d89d428d414266764741eb966ad31551`；后续 `1e7f839` 只改首次启动 QA 和文档，未改产品源码。

产物在仓库同级 `outputs/`，包名 `com.osfans.trime.debug`，使用 debug 签名。

| ABI | 字节数 | SHA-256 |
| --- | ---: | --- |
| arm64-v8a | 410,129,863 | `13416938830bfd8f3cf1536cbf41f35bc1f2fdd52db24b2d5fb34c3ff1c7b941` |
| x86_64 | 410,209,571 | `7d21c4bed30db489a35766893fcdaeee154d09531812dd8bc30529cd840b89de` |

证据：`outputs/build-mvp.log`、`outputs/unit-test-summary.json`、`outputs/apk-validation.json`、`outputs/apk-sha256.txt`，以及 `app/build/reports/tests/testDebugUnitTest/index.html`。

## 云端干净构建：通过

[运行 38664007863](https://github.com/kongfukeyong/trime/actions/runs/38664007863) 从提交 `1e7f839914da20b559172992cb8a89483f85f1b2` 构建，Windows 构建任务成功，44 项测试通过。两个 APK 的静态校验全部通过。云端 debug 密钥、构建时间与本地不同，因此 APK 哈希不同；模拟器测试使用下列云端 x86_64 包。

| ABI | 云端 APK SHA-256 |
| --- | --- |
| arm64-v8a | `6eaaebdd9e41238b65ecac76e8d9262577a5515d1396a6d6e6275529a3f0f4ee` |
| x86_64 | `0bb404a5b8910300b0bbb27149e1ce409bf6c08ddede7bf1a8263e80be90b059` |

云端日志和报告已保存在 `outputs/ci-build-116191989659.log`、`outputs/ci-build-evidence/apk-validation.json` 和 `outputs/ci-build-evidence/unit-tests-index.html`。GitHub artifact 名称为 `trime-offline-language-mvp`，保留 14 天；本地交付文件不受该期限影响。

## Android 端到端验证：部分通过，复测中

第一次 [API 35 模拟器验收](https://github.com/kongfukeyong/trime/actions/runs/38664007863) 已验证 x86_64 APK 安装、启动、输入法启用、真实向导选择应用专用存储、万象成功部署、schema/prism/table 生成及部署模型 SHA。设备 crash buffer 为空。

模式条在截图中正常显示；旧 `uiautomator dump` 只返回活动编辑器窗口，未包含 IME 窗口，导致测试在模式条断言处停止。输入切换用例当时为 NOT_RUN。正在修复测试窗口读取并复用同一云端 APK 复测。

原始证据：`outputs/ci-smoke-38664007863/emulator-smoke/summary.json`、`mode-bar.png`、`mode-bar.xml`、`deployed-model-sha256.txt`、`logcat.txt`。

脚本使用真实物理按键事件经过 IME 接口，模式按钮通过 UI 点击；软键盘字母触摸、手势、跨应用和 ARM 真机兼容性不在该脚本覆盖范围内。

## MVP 临时方案

`RuleBasedPredictor` 只根据已提交文本后缀判断语言，不能预测语义上下一词。中文后想开始英文词或英文后想开始中文词时，使用强制按钮；拼音组合保护和手动覆盖在未来替换 ONNX 实现时保留。已有万象长句模型只用于中文候选，与语言判断器独立。

首次安装、编译复现、完整源码及接口代码分别见 [MVP.md](MVP.md)、[build-mvp.md](build-mvp.md)、[改动清单](CHANGED-FILES.md)、[完整目录](DIRECTORY-TREE.txt)。
