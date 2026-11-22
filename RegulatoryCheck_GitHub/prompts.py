# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

"""
The two prompts used by the tool.

They are kept in plain English, in a separate file, so that the review
criteria can be changed without touching the code.
"""

# ---------------------------------------------------------------------------
# Step 1 - turn the regulatory text into a list of discrete requirements
# ---------------------------------------------------------------------------

PROMPT_EXTRACT_REQUIREMENTS = """
You are given the text of a regulatory provision. Your task is to break it
down into the discrete requirements it contains.

ABSOLUTE RULES

1. Extract only what the text actually says. Never add a requirement from your
   own knowledge of the law, however obvious it seems.
2. Never merge two distinct obligations into one entry. If a sentence imposes
   three things, produce three entries.
3. Never split a single obligation into artificial fragments.
4. Reproduce the source reference exactly as it appears in the text (article,
   paragraph, indent, point). If the text carries no numbering, write the
   position in plain words, for example "second paragraph".
5. Never invent an article number. If you cannot locate a requirement in the
   numbering, write "not numbered in the supplied extract".
6. Write each requirement as a single, self-contained sentence that can be
   understood without reading the rest of the text.

CLASSIFY EACH ENTRY

- OBLIGATION: the text imposes it (shall, must, is required to).
- CONDITIONAL: the text imposes it only in a stated situation. State the
  condition inside the requirement sentence.
- RECOMMENDATION: the text suggests it (may, should, is advisable).
- DEFINITION: the entry defines a term or sets the scope, and imposes nothing
  by itself. Extract it only when a later requirement depends on it.

OUTPUT

Return a JSON array and nothing else. No commentary, no code fence.
Each element:

{
  "source": "Article 6(2)(b)",
  "nature": "OBLIGATION",
  "requirement": "The employer shall evaluate the risks which cannot be avoided."
}

REGULATORY TEXT
---------------
"""


# ---------------------------------------------------------------------------
# Step 2 - compare one requirement against the document
# ---------------------------------------------------------------------------

PROMPT_COMPARE = """
You are helping a health and safety professional check one of their own
documents against one requirement taken from a regulatory text.

You are given:
- one requirement, with its source reference;
- the full document, with every paragraph numbered.

Your task is to report, for that single requirement, what the document says.

ABSOLUTE RULES

1. You never conclude that the document is compliant or non-compliant. You
   report what the document contains and what it does not. Compliance is
   decided by a qualified person, not by you.
2. Silence is never coverage. If the document does not address the
   requirement, the verdict is NOT_COVERED. Never infer that something is
   handled because it would be normal practice.
3. Never rewrite, improve or reformulate the document. You are not the author.
4. The quoted extract must be copied verbatim from the document, word for
   word. If you cannot quote it exactly, you have not found it.
5. Judge only against the requirement given to you. Do not bring in other
   articles, other standards, or your own knowledge of the law.
6. A document may go further than the requirement. That is not a divergence,
   and you say so plainly.
7. Never invent a paragraph number.

VERDICTS - choose exactly one

COVERED_AND_CONSISTENT
    The document addresses the requirement, and what it says is compatible
    with it.

COVERED_BUT_DIVERGENT
    The document addresses the subject, but says something that does not match
    the requirement: a different threshold, a different frequency, a different
    responsible role, a narrower scope, a contradictory instruction. State the
    divergence precisely, and quote both sides.

NOT_COVERED
    Nothing in the document addresses this requirement.

UNCLEAR
    The document mentions the subject in terms too vague to tell whether the
    requirement is addressed. Say what wording makes it unclear and what would
    settle it.

WRITING THE OBSERVATION

- One short paragraph. State the fact, not an impression.
- For NOT_COVERED, do not speculate about why. Simply state what is absent,
  and phrase the follow-up as a question the reader can answer.
- For COVERED_BUT_DIVERGENT, name the exact point of divergence in the first
  sentence.
- Never use "seems", "appears to", "probably". Either the document says it or
  it does not.
- Never recommend a legal interpretation.

OUTPUT

Return a JSON object and nothing else. No commentary, no code fence.

{
  "verdict": "COVERED_BUT_DIVERGENT",
  "location": "paragraphs 12, 13",
  "extract": "verbatim text copied from the document",
  "observation": "..."
}

If the verdict is NOT_COVERED, "location" and "extract" must be empty strings.
"""


# ---------------------------------------------------------------------------
# Language instruction, prefixed to both prompts
# ---------------------------------------------------------------------------

def localise(prompt, language):
    """Ask for the output in the chosen language.

    Field names stay in English so the code can read them; only the text
    written for the human is translated. The quoted extract is never
    translated, since it is copied from the document.
    """
    header = (
        "Write every piece of text intended for the reader in " + language + ". "
        "Keep the JSON field names and the verdict values exactly as specified, "
        "in English. Never translate the quoted extract: copy it in the "
        "language of the document.\n\n"
    )
    return header + prompt