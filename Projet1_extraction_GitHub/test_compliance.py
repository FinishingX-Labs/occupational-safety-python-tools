# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPT_LEGAL, PROMPT_INTERNAL
import os

load_dotenv(override=True)
client = OpenAI()

LEGAL_STORE_ID = os.environ.get("LEGAL_STORE_ID")
INTERNAL_STORE_ID = os.environ.get("INTERNAL_STORE_ID")
MODEL = "gpt-5.5"

SLIDE_TEXT = (
    "En cas de decouverte d'un colis suspect, eloignez-vous immediatement, "
    "n'y touchez pas et prevenez les forces de l'ordre en composant le 17."
)


def check(prompt, store_id, text):
    response = client.responses.create(
        model=MODEL,
        input=prompt + text,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [store_id]
        }]
    )
    return response.output_text.strip()


print("=== LEGAL CHECK ===")
print(check(PROMPT_LEGAL, LEGAL_STORE_ID, SLIDE_TEXT))
print()
print("=== INTERNAL CHECK ===")
print(check(PROMPT_INTERNAL, INTERNAL_STORE_ID, SLIDE_TEXT))