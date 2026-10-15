# 相对 Trime v3.3.12 的改动文件

功能说明见 [MVP.md](MVP.md)。以下为已提交实现清单（不包含本目录清单自身）；生成的万象资源不提交 Git，详见资源 manifest。Rime/JNI C++ 没有修改。

```text
M	.github/workflows/commit-ci.yml
A	.github/workflows/mvp-build.yml
M	.gitignore
A	README-MVP.md
M	app/src/main/java/com/osfans/trime/ime/core/InputView.kt
M	app/src/main/java/com/osfans/trime/ime/core/TrimeInputMethodService.kt
M	app/src/main/java/com/osfans/trime/ime/keyboard/CommonKeyboardActionListener.kt
A	app/src/main/java/com/osfans/trime/ime/language/LanguageModeBar.kt
A	app/src/main/java/com/osfans/trime/ime/language/LanguagePredictor.kt
A	app/src/main/java/com/osfans/trime/ime/language/LanguageSwitchPolicy.kt
A	app/src/main/java/com/osfans/trime/ime/language/RuleBasedPredictor.kt
M	app/src/main/java/com/osfans/trime/ime/switches/SwitchOptionWindow.kt
A	app/src/main/res/values-zh-rCN/language_mvp.xml
A	app/src/main/res/values/language_mvp.xml
A	app/src/test/java/com/osfans/trime/ime/language/LanguageSwitchPolicyTest.kt
M	build-logic/convention/src/main/kotlin/DataChecksumsPlugin.kt
M	build-logic/convention/src/main/kotlin/NativeAppConventionPlugin.kt
M	build-logic/convention/src/main/kotlin/NativeBaseConventionPlugin.kt
M	build-logic/convention/src/main/kotlin/OpenCCDataPlugin.kt
M	build-logic/convention/src/main/kotlin/ProjectExtensions.kt
A	docs/MVP.md
A	docs/build-mvp.md
A	docs/wanxiang-assets.manifest.json
A	docs/wanxiang-mvp.md
A	docs/wanxiang-resources.lock.json
A	docs/wanxiang-validation.json
M	gradle/libs.versions.toml
M	gradle/wrapper/gradle-wrapper.properties
A	scripts/build-mvp.ps1
A	scripts/download-wanxiang.py
A	scripts/import-wanxiang.py
A	scripts/prepare-mvp-native.ps1
A	scripts/qa/README.md
A	scripts/qa/build-editor.py
A	scripts/qa/editor/AndroidManifest.xml
A	scripts/qa/editor/MainActivity.java
A	scripts/qa/emulator-smoke.py
A	scripts/verify-wanxiang.py
```
