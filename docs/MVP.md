# Trime + 万象拼音：离线中英文自动切换 MVP

本项目以 Trime **v3.3.12**（上游提交 `e09ac7114fa067904ed358e82d499516cb423ff4`）为固定基线，在 Java/Kotlin 层实现规则判断与手动覆盖。保留 Rime 引擎和现有 JNI，不修改 C++。新增代码不请求网络，不调用大模型 API，不训练模型。

## 行为与边界

- 普通文本框：每次可输入按键进入 Rime 之前，最多读取光标前 **128 个 UTF-16 字符**。
- `statusCached.isComposing` 或 `getRawInput()` 非空时认定为 Rime 组合状态，自动模式强制保持中文，不把 `nihao` 等拼音当作已提交英文。
- 已提交上下文末尾为 ASCII 英文字母时选择英文；末尾为中文、空文本或无法分类字符时选择中文。跳过末尾的空格与常见标点，`hello ` 仍保持英文。
- 上下文读取返回 `null` 或抛出异常时保留当前语言，不记录输入内容。
- 三态按钮始终显示在键盘顶部：**自动 / 强制中文 / 强制英文**。选择持久化到本地 SharedPreferences。传统键盘的中英切换键也进入强制模式；点击“自动”恢复判断。
- 手动切到英文时，如有未完成的拼音，先通过 Rime 提交当前组合，再切换，避免丢失正在输入的内容。
- 密码、邮箱、数字、电话及明确要求 ASCII 的输入框沿用原有英文约束，也不读取周边文字；强制中文仅对普通文本框生效。`TYPE_NULL` 不读取周边文字，手动覆盖仍然可用。
- 判断作用于下一次按键；移动光标、粘贴后，下次按键会读取新位置的上下文。

**这是字符规则基线，不是下一词语义预测。** 例如中文后面想输入一个英文词时，需要先点“强制英文”；英文后面想输入中文时，点“强制中文”。未知词不会被识别为“英语而非拼音”。万象长句语言模型只参与 Rime 中文候选排序，与本项目的中英文判断器是两个独立部分。

## 目录与关键改动

完整文件目录见 `DIRECTORY-TREE.txt`。主要结构如下：

```text
trime/
├── app/
│   ├── src/main/java/com/osfans/trime/
│   │   ├── core/                         # 原有 Rime/JNI API，未修改
│   │   └── ime/
│   │       ├── language/
│   │       │   ├── LanguagePredictor.kt  # Language 与稳定接口
│   │       │   ├── RuleBasedPredictor.kt # 纯 Kotlin 字符规则
│   │       │   ├── LanguageSwitchPolicy.kt # 组合保护、手动优先、null 降级
│   │       │   └── LanguageModeBar.kt    # 三态切换 UI
│   │       ├── core/TrimeInputMethodService.kt
│   │       ├── core/InputView.kt
│   │       ├── keyboard/CommonKeyboardActionListener.kt
│   │       └── switches/SwitchOptionWindow.kt
│   ├── src/main/assets/rime/             # 万象方案、词库、Lua、离线语言模型
│   ├── src/main/res/values/language_mvp.xml
│   ├── src/main/res/values-zh-rCN/language_mvp.xml
│   └── src/test/java/com/osfans/trime/ime/language/
│       └── LanguageSwitchPolicyTest.kt
├── build-logic/convention/               # 可选官方原生库构建路径
├── scripts/                             # 构建时资源准备；不在 APK 中执行
└── docs/
    ├── MVP.md
    ├── build-mvp.md
    └── wanxiang-mvp.md
```

| 文件 | 改动目的 |
|---|---|
| `LanguagePredictor.kt` | 保留 `predict(context: String): Language`，以后替换实现不改调用入口 |
| `RuleBasedPredictor.kt` | 离线、无 Android 依赖的规则实现 |
| `LanguageSwitchPolicy.kt` | 按手动覆盖 → 拼音保护 → 上下文判断的优先级决策 |
| `TrimeInputMethodService.kt` | 主线程捕获 InputConnection、后台读取文字，串行 Rime 作业内决定并设置 `ascii_mode`，处理实体键盘 |
| `CommonKeyboardActionListener.kt` | 软键盘 `processKey` 之前调用同一入口，覆盖文本型按键和传统中英键 |
| `InputView.kt`、`LanguageModeBar.kt` | 显示三态模式条，跟随 Rime 状态与手动模式刷新 |
| `SwitchOptionWindow.kt` | 原有方案菜单里的中英选项同样作为手动覆盖，防止下次自动判断立即撤销 |
| `language_mvp.xml` | 中英文 UI 文案 |
| `LanguageSwitchPolicyTest.kt` | 验证规则、组合保护、强制覆盖、返回自动、读取失败时的降级 |

## InputMethodService 接入

实际类为 `TrimeInputMethodService : LifecycleInputMethodService()`，后者继承 Android `InputMethodService`。

软键盘路径：`CommonKeyboardActionListener.onKey()` → `service.postInputJob { ... }` → `service.prepareLanguageForKey(this)` → `RimeApi.processKey(...)`。

```kotlin
service.postInputJob {
    if (service.hookKeyboard(keyEventCode, m)) return@postInputJob
    if (m and (KeyEvent.META_CTRL_ON or KeyEvent.META_ALT_ON or KeyEvent.META_META_ON) == 0) {
        if (!service.prepareLanguageForKey(this)) return@postInputJob
    }
    if (processKey(value, modifiers)) return@postInputJob
    // 原有特殊按键处理保留。
}
```

实体键盘路径：`TrimeInputMethodService.forwardKeyEvent()`，同样在 `processKey` 前判断；KeyUp 与 Ctrl/Alt/Meta 快捷键跳过判断。

```kotlin
postInputJob {
    if (!modifiers.release && !modifiers.ctrl && !modifiers.alt && !modifiers.meta) {
        if (!prepareLanguageForKey(this)) return@postInputJob
    }
    processKey(keyVal, modifiers, isVirtual = false)
}
```

`prepareLanguageForKey()` 先从现有 `RimeApi.getRuntimeOption("ascii_mode")`、`statusCached`、`getRawInput()` 取得状态，再在 Android 主线程捕获当前连接，在 IO 线程调用 `getTextBeforeCursor(128, 0)`，避免目标编辑器响应缓慢时阻塞键盘界面。只在目标模式不同于当前模式时调用 `setRuntimeOption("ascii_mode", targetAscii)`。整个判断与当前按键位于同一个串行 Rime 作业里。

编辑器中的周边文字属于 Android `InputConnection`，无法通过 Rime JNI 获取；JNI 提供的是引擎内部的拼音输入、候选与选项。这两个来源必须分开，才能保护尚未上屏的拼音。

首次部署时，Android 可能在资源复制和 Rime 初始化完成前请求键盘。`onCreateInputView()` 通过 `runOnReady` 异步等待后创建视图，并补发当前编辑器状态，避免提前加载主题引发崩溃；等待期间不占据编辑器触摸区域。

## 编译与安装

具体工具链版本、预编译原生库准备步骤、Gradle 命令见 [build-mvp.md](build-mvp.md)。万象来源、许可证、固定版本、校验和与部署目录见 [wanxiang-mvp.md](wanxiang-mvp.md)。

APK 包名为 `com.osfans.trime.debug`，与正式版 Trime 可以共存。安装时使用：

```powershell
adb install -r <生成的-debug.apk>
adb shell ime enable com.osfans.trime.debug/com.osfans.trime.ime.core.TrimeInputMethodService
adb shell ime set com.osfans.trime.debug/com.osfans.trime.ime.core.TrimeInputMethodService
```

也可以在 Android 设置中手动启用并选择本输入法。首次打开 Trime，在设置向导中选择“应用专用存储”（App-specific storage），依次完成启用、选择输入法，再等待万象部署完成。本 MVP 的资源已内置，不需要选择外部同步目录。普通文本框中打开键盘，确认顶部有三态模式条。

## 手动验收流程

1. 空文本框选择“自动”，输入 `nihao`：应产生中文候选，逐键输入过程中不切到英文；选中“你好”上屏。
2. 点“强制英文”，输入 `hello`：应直接上屏英文；继续输入时不被自动切回中文。
3. 将光标放在已提交 `hello` 后，点“自动”，输入 `world`：应继续英文。
4. 将光标放在已提交“你好”后，点“自动”，输入 `zhongwen`：应出现中文候选。
5. 在 `hello` 后点“强制中文”，输入 `nihao`：应继续使用拼音，手动选择优先于英文上下文。
6. 在拼音组合期间点“强制英文”：原组合应先提交，然后进入英文，不能静默丢失拼音。
7. 切换应用、重新打开键盘：手动模式保留；点“自动”能恢复判断。
8. 密码／数字输入框：保持原有 ASCII 输入行为。普通输入框读取周边文字失败时仍可用手动按钮纠正。

## 后续替换点（本次不实现）

- `RuleBasedPredictor` 是临时规则：可以替换为实现相同接口的本地 ONNX 推理类；`LanguageSwitchPolicy` 中的手动覆盖与拼音保护应保留。
- 128 字符窗口、标点过滤、未知字符默认中文均是 MVP 常量，尚无词级置信度、迟滞或语义预测。
- 手动选择是全局持久化偏好；没有按应用独立配置。
- 为缩短首个 APK 构建时间提供的官方原生库路径是 MVP 构建便利选项；完整源码构建仍使用上游锁定的子模块。
- 本项目未新增运行时联网功能。开发时下载开源源码、词库与 Gradle 依赖需要网络；准备完毕后的输入判断和候选计算均在设备上执行。

## 源码基线与远程 Fork

远程 Fork：[kongfukeyong/trime](https://github.com/kongfukeyong/trime)。实现分支：[mvp/auto-language](https://github.com/kongfukeyong/trime/tree/mvp/auto-language)。该分支直接基于真正的上游 `v3.3.12` 提交，保留上游历史、许可证与子模块 SHA；本地 `origin` 指向 Fork，`upstream` 指向 osfans/trime。

```powershell
git clone --branch mvp/auto-language https://github.com/kongfukeyong/trime.git
cd trime
```

按构建文档准备资源，再运行构建。生成的 `assets/rime/` 已被 Git 忽略，避免把 398 MB 的语法模型提交到普通仓库。固定来源、长度和 SHA-256 由 `wanxiang-resources.lock.json` 管理。GitHub Actions 在同一分支执行资源校验、APK 构建与单元测试；工作流是否通过、APK 是否安装运行，以交付验证报告中的实际证据为准。

上游参考：[Trime](https://github.com/osfans/trime/tree/v3.3.12)、[万象拼音](https://github.com/amzxyz/rime-wanxiang)。

## LanguagePredictor 与 RuleBasedPredictor 完整代码

### LanguagePredictor.kt

```kotlin
// SPDX-License-Identifier: GPL-3.0-or-later
package com.osfans.trime.ime.language

enum class Language { CHINESE, ENGLISH }

/** Only committed text before the cursor belongs here; never pass raw pinyin. */
fun interface LanguagePredictor {
    fun predict(context: String): Language
}

```

### RuleBasedPredictor.kt

```kotlin
// SPDX-License-Identifier: GPL-3.0-or-later
package com.osfans.trime.ime.language

/** MVP baseline. Replace this class with local model inference behind LanguagePredictor. */
class RuleBasedPredictor : LanguagePredictor {
    override fun predict(context: String): Language {
        // Ignore word separators so "hello " can continue in English.
        // Digits and other scripts deliberately fall back to Chinese in this MVP.
        val text = context.trimEnd { it.isWhitespace() || it in ",.!?;:，。！？；：、\"'()（）" }
        if (text.isEmpty()) return Language.CHINESE
        val last = Character.codePointBefore(text, text.length)
        return when {
            last in 'a'.code..'z'.code || last in 'A'.code..'Z'.code -> Language.ENGLISH
            else -> Language.CHINESE
        }
    }
}

```

### LanguageSwitchPolicy.kt

```kotlin
// SPDX-License-Identifier: GPL-3.0-or-later
package com.osfans.trime.ime.language

enum class InputLanguageMode { AUTO, FORCE_CHINESE, FORCE_ENGLISH }

/** Engine safety and manual overrides stay in place when the predictor is replaced. */
class LanguageSwitchPolicy(private val predictor: LanguagePredictor) {
    fun decide(
        context: String?,
        isPinyinComposing: Boolean,
        mode: InputLanguageMode,
        current: Language,
    ): Language = when (mode) {
        InputLanguageMode.FORCE_CHINESE -> Language.CHINESE
        InputLanguageMode.FORCE_ENGLISH -> Language.ENGLISH
        InputLanguageMode.AUTO -> when {
            isPinyinComposing -> Language.CHINESE
            context == null -> current // Editor declined surrounding-text access.
            else -> predictor.predict(context)
        }
    }
}

```

