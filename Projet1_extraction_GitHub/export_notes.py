# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0


from pptx import Presentation
from config import (
    PPTX_FILE, OUTPUT_PPTX_FILE, CSV_FILE, CSV_DELIMITER,
    SLIDE_NUMBER_COLUMN, LEGAL_COLUMN, INTERNAL_COLUMN, RISK_COLUMN,
)
import csv
import os

MARKER = "----- AI REVIEW -----"

SECTIONS = [
    (LEGAL_COLUMN, "LEGAL COMPLIANCE"),
    (INTERNAL_COLUMN, "INTERNAL DOCUMENTS"),
    (RISK_COLUMN, "RISK ASSESSMENT"),
]


def load_results(path):
    results = {}

    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        for row in reader:
            number = str(row[SLIDE_NUMBER_COLUMN]).strip()
            results[number] = row

    return results


def build_note(row):
    parts = []

    for column, title in SECTIONS:
        value = row.get(column, "").strip()
        if value:
            parts.append("[" + title + "]")
            parts.append(value)
            parts.append("")

    if not parts:
        return ""

    return MARKER + "\n\n" + "\n".join(parts).rstrip()


def strip_previous_review(text):
    position = text.find(MARKER)
    if position == -1:
        return text.rstrip()
    return text[:position].rstrip()


def run_export():
    if not os.path.exists(CSV_FILE):
        print("File not found:", CSV_FILE)
        return False

    results = load_results(CSV_FILE)
    presentation = Presentation(PPTX_FILE)

    written = 0

    for number, slide in enumerate(presentation.slides, start=1):
        row = results.get(str(number))
        if row is None:
            continue

        note = build_note(row)
        if not note:
            continue

        notes_frame = slide.notes_slide.notes_text_frame
        original = strip_previous_review(notes_frame.text)

        if original:
            notes_frame.text = original + "\n\n" + note
        else:
            notes_frame.text = note

        written = written + 1

    presentation.save(OUTPUT_PPTX_FILE)
    print("Notes written on", written, "slides ->", OUTPUT_PPTX_FILE)
    return True


if __name__ == "__main__":
    run_export()