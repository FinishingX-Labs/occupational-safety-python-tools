# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from extraction import run_extraction
from compliance import run_compliance, load_rows, count_existing_results
from export_notes import run_export
from filter_deck import run_filter
from config import CSV_FILE, FORCE_EXTRACTION, DEFAULT_LANGUAGE
import os

LANGUAGES = {
    "1": "French",
    "2": "English",
    "3": "German",
}


def ask_language():
    print("Language for the explanations written in the speaker notes:")
    for key in sorted(LANGUAGES):
        print("  " + key + " - " + LANGUAGES[key])

    answer = input("Choice [1]: ").strip()
    return LANGUAGES.get(answer, DEFAULT_LANGUAGE)


def ask_regenerate():
    if not os.path.exists(CSV_FILE):
        return False

    existing = count_existing_results(load_rows(CSV_FILE))
    if existing == 0:
        return False

    print()
    print(existing, "slides already have results, written in a previous run.")
    print("They will keep their original language unless you regenerate them.")
    answer = input("Regenerate them in the language chosen? This costs credits (y/n): ")
    return answer.strip().lower() == "y"


def ask_question():
    print()
    print("You can extract only the slides answering a specific question.")
    print("Leave empty to keep the whole presentation.")
    return input("Your question: ").strip()


language = ask_language()
regenerate = ask_regenerate()
question = ask_question()

print()
print("=== STEP 1: extraction ===")

if FORCE_EXTRACTION or not os.path.exists(CSV_FILE):
    if not run_extraction():
        exit()
else:
    print("Skipped:", CSV_FILE, "already exists.")
    print("Set FORCE_EXTRACTION = True in config.py to rebuild it.")

print()
print("=== STEP 2: compliance check ===")
run_compliance(language, regenerate)

print()
print("=== STEP 3: full annotated presentation ===")
run_export()

if question:
    print()
    print("=== STEP 4: filtered presentation ===")
    run_filter(question, language)

print()
print("=== Pipeline finished ===")