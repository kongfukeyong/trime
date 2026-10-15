// SPDX-FileCopyrightText: 2015 - 2024 Rime community
//
// SPDX-License-Identifier: GPL-3.0-or-later

package com.osfans.trime.data.theme

import com.osfans.trime.data.theme.model.GeneralStyle
import com.osfans.trime.util.yaml.Yaml
import com.osfans.trime.util.yaml.get
import io.kotest.core.spec.style.BehaviorSpec
import io.kotest.matchers.shouldBe
import io.kotest.matchers.shouldNotBe

class GeneralStyleTest :
    BehaviorSpec({
        Given("Correct style YAML in the current format") {
            // Decode on the host JVM without starting the native Rime engine.
            val node = Yaml.parseToYamlNode(
                """
                style:
                  auto_caps: false
                  candidate_font: [han.ttf]
                """.trimIndent(),
            )

            When("loaded") {
                val generalStyle = GeneralStyle.decode(requireNotNull(node["style"]))

                Then("it should not be null") {
                    generalStyle shouldNotBe null
                    generalStyle.autoCaps shouldBe false

                    generalStyle.candidateFont shouldBe listOf("han.ttf")
                }
            }
        }

        Given("Missing or invalid style values") {
            val node = Yaml.parseToYamlNode(
                """
                style:
                  auto_caps:
                  candidate_font:
                  comment_position: aaaa
                  enter_labels:
                """.trimIndent(),
            )

            When("loaded") {
                val generalStyle = GeneralStyle.decode(requireNotNull(node["style"]))

                Then("with default value without exception") {
                    generalStyle.autoCaps shouldBe false
                    generalStyle.candidateBorder shouldBe 0
                    generalStyle.candidateFont shouldBe emptyList()
                    generalStyle.commentPosition shouldBe GeneralStyle.CommentPosition.RIGHT
                    generalStyle.enterLabel shouldNotBe null
                    generalStyle.enterLabel.go shouldBe "go"
                }
            }
        }
    })
