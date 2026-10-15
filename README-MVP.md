# Android 中英文自动切换 MVP

基于 Trime v3.3.12 和万象拼音基础版，使用离线字符规则选择 `ascii_mode`。不训练模型，不调用网络 API，不修改 Rime C++。

- 实现：[mvp/auto-language 分支](https://github.com/kongfukeyong/trime/tree/mvp/auto-language)
- [完整设计、代码、按键接入位置、手动验收与临时方案说明](docs/MVP.md)
- [编译和安装步骤、工具链与原生库来源](docs/build-mvp.md)
- [万象方案、词库、长句模型、许可证及固定校验和](docs/wanxiang-mvp.md)
- [GitHub 构建记录](https://github.com/kongfukeyong/trime/actions/workflows/mvp-build.yml)

键盘顶部提供 **自动 / 强制中文 / 强制英文**。自动模式读取光标前 128 个字符；正在拼音组合时保持中文，已提交英文后缀倾向英文。手动选择优先并保存在本地。它是可替换的规则基线，尚不具备下一词的语义预测能力。

资源生成在 `app/src/main/assets/rime/`，被 Git 忽略；首次构建需按文档下载、校验并导入。实际离线资源约 492 MB，其中已有长句语法模型约 398 MB，模型只用于 Rime 中文候选，不用于语言判断。

APK 包名 `com.osfans.trime.debug`。构建成功的工作流会上传 arm64-v8a / x86_64 APK 与测试报告。APK 构建、安装以及输入功能测试各自的验证状态请以交付验证记录为准。
