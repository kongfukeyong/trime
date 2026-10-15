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
