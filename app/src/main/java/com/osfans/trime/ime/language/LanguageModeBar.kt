// SPDX-License-Identifier: GPL-3.0-or-later
package com.osfans.trime.ime.language

import android.content.Context
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import com.osfans.trime.R

/** Always visible, including when the theme hides Trime's normal input bar. */
class LanguageModeBar(context: Context, onModeSelected: (InputLanguageMode) -> Unit) : LinearLayout(context) {
    private val labels = listOf(R.string.language_auto, R.string.language_force_chinese, R.string.language_force_english)
    private val buttons = InputLanguageMode.entries.mapIndexed { index, mode ->
        Button(context).apply {
            id = View.generateViewId()
            text = context.getString(labels[index])
            textSize = 13f
            isAllCaps = false
            setPadding(0, 0, 0, 0)
            setOnClickListener { onModeSelected(mode) }
            addView(this, LayoutParams(0, LayoutParams.MATCH_PARENT, 1f))
        }
    }

    init {
        id = View.generateViewId()
        orientation = HORIZONTAL
    }

    fun update(mode: InputLanguageMode, isAscii: Boolean) {
        buttons.forEachIndexed { index, button ->
            val selected = InputLanguageMode.entries[index] == mode
            button.isSelected = selected
            val label = context.getString(labels[index])
            val language = if (isAscii) "EN" else "中"
            button.text = when {
                selected && mode == InputLanguageMode.AUTO -> "✓ $label · $language"
                selected -> "✓ $label"
                else -> label
            }
            button.contentDescription = if (selected) {
                context.getString(R.string.language_current_mode, label, language)
            } else {
                label
            }
        }
    }
}
