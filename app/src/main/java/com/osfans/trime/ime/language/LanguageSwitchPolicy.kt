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
