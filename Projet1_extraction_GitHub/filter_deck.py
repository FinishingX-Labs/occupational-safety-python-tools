# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from pptx import Presentation
from pptx.util import Inches, Pt
from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPT_SLIDE_SELECTION, PROMPT_RECOMMENDATIONS
from config import (
    PPTX_FILE, FILTERED_PPTX_FILE, CSV_FILE, CSV_DELIMITER,
    COMPLIANCE_MODEL, MAX_SELECTION_PREVIEW,
    SLIDE_NUMBER_COLUMN, SLIDE_CONTENT_COLUMN, IMAGE_TEXT_COLUMN,
    LEGAL_COLUMN, INTERNAL_COLUMN, RISK_COLUMN,
)
import csv
import json
import os

load_dotenv(override=True)
client = OpenAI()

MARKER = "----- AI REVIEW -----"

SECTIONS = [
    (LEGAL_COLUMN, "LEGAL COMPLIANCE"),
    (INTERNAL_COLUMN, "INTERNAL DOCUMENTS"),
    (RISK_COLUMN, "RISK ASSESSMENT"),
]

MAX_SUMMARY_LINES = 6


def load_results(path):
    results = {}
    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        for row in reader:
            number = str(row[SLIDE_NUMBER_COLUMN]).strip()
            results[number] = row
    return results


def parse_json_answer(text):
    text = text.strip()
    if text.startswith("```"):
        kept = []
        for line in text.split("\n"):
            if not line.strip().startswith("```"):
                kept.append(line)
        text = "\n".join(kept)
    return json.loads(text)


def select_slides(question, results):
    lines = []
    for number in sorted(results, key=int):
        row = results[number]
        content = (row[SLIDE_CONTENT_COLUMN] + " " + row[IMAGE_TEXT_COLUMN]).strip()
        content = " ".join(content.split())
        lines.append("Slide " + number + ": " + content[:MAX_SELECTION_PREVIEW])

    full_input = (
        PROMPT_SLIDE_SELECTION +
        "REQUEST:\n" + question + "\n\nSLIDES:\n" + "\n".join(lines)
    )

    response = client.responses.create(model=COMPLIANCE_MODEL, input=full_input)
    answer = parse_json_answer(response.output_text)

    numbers = []
    for value in answer.get("slides", []):
        numbers.append(int(value))

    return sorted(set(numbers))


def collect_findings(results, numbers):
    findings = []

    for position, number in enumerate(numbers, start=1):
        row = results.get(str(number))
        if row is None:
            continue
        for column, title in SECTIONS:
            value = row.get(column, "").strip()
            if value:
                findings.append("Slide " + str(position) + " - " + title + ": " + value)

    return findings


def build_recommendations(results, selected, language):
    findings = collect_findings(results, selected)

    if not findings:
        print("No review findings on the selected slides - summary slide skipped.")
        return ""

    full_input = (
        PROMPT_RECOMMENDATIONS +
        "LANGUAGE: " + language + "\n\nFINDINGS:\n" + "\n\n".join(findings)
    )

    response = client.responses.create(model=COMPLIANCE_MODEL, input=full_input)
    return response.output_text.strip()


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


def pick_blank_layout(presentation):
    layouts = presentation.slide_layouts
    if len(layouts) > 6:
        return layouts[6]
    return layouts[len(layouts) - 1]


def add_recommendations_slide(presentation, text, language):
    titles = {
        "French": "A retenir",
        "English": "Key actions",
        "German": "Wichtigste Massnahmen",
    }
    title = titles.get(language, "Key actions")

    slide = presentation.slides.add_slide(pick_blank_layout(presentation))

    margin = Inches(1.0)
    width = presentation.slide_width - (margin * 2)

    title_box = slide.shapes.add_textbox(margin, Inches(0.9), width, Inches(1.0))
    title_frame = title_box.text_frame
    title_frame.word_wrap = True
    title_frame.text = title
    title_frame.paragraphs[0].runs[0].font.size = Pt(32)
    title_frame.paragraphs[0].runs[0].font.bold = True

    body_box = slide.shapes.add_textbox(
        margin, Inches(2.2), width, presentation.slide_height - Inches(3.0)
    )
    body_frame = body_box.text_frame
    body_frame.word_wrap = True

    lines = []
    for line in text.split("\n"):
        cleaned = line.strip()
        if cleaned:
            lines.append(cleaned)

    lines = lines[:MAX_SUMMARY_LINES]

    first = True
    for line in lines:
        if first:
            paragraph = body_frame.paragraphs[0]
            first = False
        else:
            paragraph = body_frame.add_paragraph()

        paragraph.text = "•  " + line
        paragraph.font.size = Pt(20)
        paragraph.space_after = Pt(14)


def keep_only(presentation, numbers):
    keep = set(numbers)
    slide_id_list = presentation.slides._sldIdLst
    elements = list(slide_id_list)

    for index in range(len(elements) - 1, -1, -1):
        if (index + 1) not in keep:
            slide_id_list.remove(elements[index])


def run_filter(question, language):
    if not os.path.exists(CSV_FILE):
        print("File not found:", CSV_FILE)
        return False

    results = load_results(CSV_FILE)

    print("Selecting relevant slides...")
    selected = select_slides(question, results)

    if not selected:
        print("No slide matches this request. Nothing was produced.")
        return False

    print("Slides selected:", selected)

    presentation = Presentation(PPTX_FILE)

    for number, slide in enumerate(presentation.slides, start=1):
        if number not in selected:
            continue

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

    keep = list(selected)

    print("Building the summary slide...")
    recommendations = build_recommendations(results, selected, language)

    if recommendations:
        add_recommendations_slide(presentation, recommendations, language)
        keep.append(len(presentation.slides))

    keep_only(presentation, keep)

    presentation.save(FILTERED_PPTX_FILE)
    print("Written:", FILTERED_PPTX_FILE, "-", len(selected), "slides + summary")
    return True


if __name__ == "__main__":
    run_filter(input("Your question: "), "French")