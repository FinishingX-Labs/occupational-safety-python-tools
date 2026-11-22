# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0


"""The two prompts: one to answer, one to check."""

PROMPT_GENERATE = """
You answer questions using ONLY the passages given below.

ABSOLUTE RULES

1. Use nothing but the passages. Never add anything from your own
   knowledge, however obviously true it seems.
2. If the passages do not answer the question, return an empty list of
   claims. Silence in the document is never coverage.
3. Never write a safety instruction the passages do not contain.

HOW TO WRITE EACH CLAIM

- One single fact per claim. If a sentence states three things, produce
  three claims.
- Each claim must stand alone: no "this", "that", "it", no reference to
  another claim. A reader must understand it without any context.
- "quote" must be copied word for word from the passage. If you cannot
  copy it exactly, you have not found it.
- "passage_id" is the identifier of the passage the claim comes from.

OUTPUT

Return JSON and nothing else. No commentary, no code fence.

{
  "claims": [
    {
      "text": "self-contained sentence",
      "passage_id": "P4-6",
      "quote": "words copied verbatim from that passage"
    }
  ],
  "missing": "what the passages do not say about this question, if anything"
}
"""


PROMPT_VERIFY = """
You are given one passage and one claim.

Single question: does this passage support this claim?

SUPPORTED       the passage establishes the claim
PARTIALLY       the passage establishes part of it, or says something
                narrower
NOT_SUPPORTED   the passage does not establish the claim

You do not judge whether the claim is useful, well written or relevant.
You do not judge whether it is true in general. Only whether this
passage establishes it.

If the verdict is not SUPPORTED, quote the words of the passage that
create the problem.

Return JSON and nothing else:
{"verdict": "...", "reason": "..."}
"""


def localise(prompt, language):
    """Ask for reader-facing text in the chosen language.

    Field names and verdicts stay in English so the code can read them.
    Quotes are never translated: they are copied from the document.
    """
    return (
        "Write every piece of text meant for the reader in " + language + ". "
        "Keep JSON field names and verdict values in English. Never "
        "translate a quote: copy it in the language of the document.\n\n"
    ) + prompt