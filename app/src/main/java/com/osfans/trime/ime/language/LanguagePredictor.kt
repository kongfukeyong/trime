// SPDX-License-Identifier: GPL-3.0-or-later
package com.osfans.trime.ime.language

enum class Language { CHINESE, ENGLISH }

/** Only committed text before the cursor belongs here; never pass raw pinyin. */
fun interface LanguagePredictor {
    fun predict(context: String): Language
}
