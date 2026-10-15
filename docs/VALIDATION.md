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

## Android 端到端验证：进行中

[独立云端构建与全新 API 35 模拟器验收](https://github.com/kongfukeyong/trime/actions/runs/38664007863) 将安装 x86_64 包，通过真实首次启动向导选择应用专用存储，验证万象编译部署、模型校验、模式条、拼音候选上屏、英文续写及两种手动覆盖。此处尚不声明安装或输入行为通过，完成后更新实际结果。

脚本使用真实物理按键事件经过 IME 接口，模式按钮通过 UI 点击；软键盘字母触摸、手势、跨应用和 ARM 真机兼容性不在该脚本覆盖范围内。

## MVP 临时方案

`RuleBasedPredictor` 只根据已提交文本后缀判断语言，不能预测语义上下一词。中文后想开始英文词或英文后想开始中文词时，使用强制按钮；拼音组合保护和手动覆盖在未来替换 ONNX 实现时保留。已有万象长句模型只用于中文候选，与语言判断器独立。

首次安装、编译复现、完整源码及接口代码分别见 [MVP.md](MVP.md)、[build-mvp.md](build-mvp.md)、[改动清单](CHANGED-FILES.md)、[完整目录](DIRECTORY-TREE.txt)。
