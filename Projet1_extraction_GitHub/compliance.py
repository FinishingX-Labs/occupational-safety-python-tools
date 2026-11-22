# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPT_LEGAL, PROMPT_INTERNAL, PROMPT_RISK_COVERAGE
from config import (
    CSV_FILE, CSV_DELIMITER, COMPLIANCE_MODEL, DEFAULT_LANGUAGE,
    COMPLIANCE_SLIDE_LIMIT, MIN_CONTENT_LENGTH, COLUMNS,
    SLIDE_NUMBER_COLUMN, SLIDE_CONTENT_COLUMN, IMAGE_TEXT_COLUMN,
    LEGAL_COLUMN, INTERNAL_COLUMN, RISK_COLUMN,
)
import csv
import os

load_dotenv(override=True)
client = OpenAI()

LEGAL_STORE_ID = os.environ.get("LEGAL_STORE_ID")
INTERNAL_STORE_ID = os.environ.get("INTERNAL_STORE_ID")
RISK_STORE_ID = os.environ.get("RISK_STORE_ID")

RESULT_COLUMNS = [LEGAL_COLUMN, INTERNAL_COLUMN, RISK_COLUMN]


def localise(prompt, language):
    header = (
        "OUTPUT LANGUAGE: write your entire answer in " + language + ". "
        "This overrides any other language instruction below. "
        "Keep the verdict keywords and the labels in square brackets in English, "
        "exactly as written, and translate everything else.\n\n"
    )
    return header + prompt


def check(prompt, store_id, text, language):
    if not store_id:
        return "No reference corpus available for this check."

    response = client.responses.create(
        model=COMPLIANCE_MODEL,
        input=localise(prompt, language) + text,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [store_id]
        }]
    )
    return response.output_text.strip()


def load_rows(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        rows = list(reader)

    for row in rows:
        for column in COLUMNS:
            if column not in row or row[column] is None:
                row[column] = ""

    return rows


def save_rows(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS, delimiter=CSV_DELIMITER)
        writer.writeheader()
        writer.writerows(rows)


def count_existing_results(rows):
    count = 0
    for row in rows:
        for column in RESULT_COLUMNS:
            if row[column].strip():
                count = count + 1
                break
    return count


def clear_results(rows):
    for row in rows:
        for column in RESULT_COLUMNS:
            row[column] = ""


def run_compliance(language=DEFAULT_LANGUAGE, regenerate=False):
    try:
        open(CSV_FILE, "a").close()
    except PermissionError:
        print("Please close", CSV_FILE, "in Excel before running this script.")
        return False

    rows = load_rows(CSV_FILE)

    if regenerate:
        clear_results(rows)
        save_rows(CSV_FILE, rows)
        print("Previous results cleared.")

    print("Explanations will be written in:", language)
    processed = 0

    for row in rows:
        if COMPLIANCE_SLIDE_LIMIT is not None and processed >= COMPLIANCE_SLIDE_LIMIT:
            break

        if row[LEGAL_COLUMN].strip() and row[RISK_COLUMN].strip():
            continue

        content = (row[SLIDE_CONTENT_COLUMN] + "\n" + row[IMAGE_TEXT_COLUMN]).strip()
        if len(content) < MIN_CONTENT_LENGTH:
            continue

        if not row[LEGAL_COLUMN].strip():
            row[LEGAL_COLUMN] = check(PROMPT_LEGAL, LEGAL_STORE_ID, content, language)

        if not row[INTERNAL_COLUMN].strip():
            row[INTERNAL_COLUMN] = check(PROMPT_INTERNAL, INTERNAL_STORE_ID, content, language)

        if not row[RISK_COLUMN].strip():
            row[RISK_COLUMN] = check(PROMPT_RISK_COVERAGE, RISK_STORE_ID, content, language)

        save_rows(CSV_FILE, rows)
        processed = processed + 1
        print("Slide", row[SLIDE_NUMBER_COLUMN], "checked")

    print("Compliance done:", processed, "slides checked")
    return True


if __name__ == "__main__":
    run_compliance()