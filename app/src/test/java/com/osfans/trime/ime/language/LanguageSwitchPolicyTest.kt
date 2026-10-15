// SPDX-License-Identifier: GPL-3.0-or-later
package com.osfans.trime.ime.language

import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.shouldBe

class LanguageSwitchPolicyTest : StringSpec({
    val predictor = RuleBasedPredictor()
    val policy = LanguageSwitchPolicy(predictor)

    "committed Latin suffix selects English" {
        listOf("hello", "这是Android", "ABC", "hello, ").forEach {
            predictor.predict(it) shouldBe Language.ENGLISH
        }
    }
    "Chinese including supplementary Han selects Chinese" {
        listOf("你好", "hello世界！ ", "\uD840\uDC00", "", "123", "😀").forEach {
            predictor.predict(it) shouldBe Language.CHINESE
        }
    }
    "pinyin composition wins over Latin-looking preedit and previous English" {
        policy.decide("hello nihao", true, InputLanguageMode.AUTO, Language.CHINESE) shouldBe Language.CHINESE
    }
    "candidate composition never invokes future model inference" {
        val guarded = LanguageSwitchPolicy { error("Must not predict composing text") }
        guarded.decide("nihao", true, InputLanguageMode.AUTO, Language.CHINESE) shouldBe Language.CHINESE
    }
    "force English wins over Chinese context and composition" {
        policy.decide("你好", true, InputLanguageMode.FORCE_ENGLISH, Language.CHINESE) shouldBe Language.ENGLISH
    }
    "force Chinese wins over committed English" {
        policy.decide("hello", false, InputLanguageMode.FORCE_CHINESE, Language.ENGLISH) shouldBe Language.CHINESE
    }
    "returning to automatic restores context decisions" {
        policy.decide("hello", false, InputLanguageMode.FORCE_CHINESE, Language.ENGLISH) shouldBe Language.CHINESE
        policy.decide("hello", false, InputLanguageMode.AUTO, Language.CHINESE) shouldBe Language.ENGLISH
        policy.decide("hello你好", false, InputLanguageMode.AUTO, Language.ENGLISH) shouldBe Language.CHINESE
    }
    "null surrounding text preserves current mode instead of resetting" {
        policy.decide(null, false, InputLanguageMode.AUTO, Language.ENGLISH) shouldBe Language.ENGLISH
        policy.decide(null, false, InputLanguageMode.AUTO, Language.CHINESE) shouldBe Language.CHINESE
    }
    "manual override still works when editor refuses surrounding text" {
        policy.decide(null, false, InputLanguageMode.FORCE_ENGLISH, Language.CHINESE) shouldBe Language.ENGLISH
        policy.decide(null, false, InputLanguageMode.FORCE_CHINESE, Language.ENGLISH) shouldBe Language.CHINESE
    }
})
