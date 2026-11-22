# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from openpyxl import load_workbook
from openai import OpenAI
from dotenv import load_dotenv
import json
import os

load_dotenv(override=True)
client = OpenAI()

EXCEL_FILE = "reference_documents/risk_assessment/risk_assessment.xlsx"
TEXT_FILE = "reference_documents/risk_assessment/risk_assessment.txt"
MAPPING_FILE = "risk_assessment_mapping.json"
MODEL = "gpt-5.5"
SEARCH_ROWS = 30
MIN_FILLED_FIELDS = 3

EXPORT_FIELDS = [
    ("unit", "Work unit"),
    ("activity", "Activity"),
    ("hazard", "Hazard"),
    ("situation", "Dangerous situation"),
    ("damage", "Potential harm"),
    ("severity", "Severity"),
    ("frequency", "Frequency"),
    ("criticality", "Criticality"),
    ("existing_measures", "Existing prevention measures"),
    ("planned_actions", "Planned actions"),
    ("owner", "Responsible"),
    ("deadline", "Deadline"),
    ("status", "Status"),
]

MAPPING_PROMPT = """You are mapping the columns of a workplace risk assessment spreadsheet.

Assign to each column ONE of the following roles, or "ignore" if none applies:
unit, activity, hazard, situation, damage, severity, frequency, criticality,
existing_measures, planned_actions, owner, deadline, status, ignore

Answer with JSON only, no explanation, in exactly this form:
{"1": "unit", "2": "activity", "3": "ignore"}

COLUMN HEADERS:
"""


def count_filled_cells(row):
    filled = 0
    for value in row:
        if value is not None and str(value).strip():
            filled = filled + 1
    return filled


def find_header_row(sheet):
    header_row_number = 0
    best_count = 0

    for number, row in enumerate(sheet.iter_rows(max_row=SEARCH_ROWS, values_only=True), start=1):
        count = count_filled_cells(row)
        if count > best_count:
            best_count = count
            header_row_number = number

    return header_row_number


def read_headers(sheet, row_number):
    values = list(
        sheet.iter_rows(min_row=row_number, max_row=row_number, values_only=True)
    )[0]

    headers = []
    for index, value in enumerate(values, start=1):
        if value is not None and str(value).strip():
            headers.append((index, str(value).strip()))

    return headers


def parse_json_answer(text):
    text = text.strip()
    if text.startswith("```"):
        kept = []
        for line in text.split("\n"):
            if not line.strip().startswith("```"):
                kept.append(line)
        text = "\n".join(kept)
    return json.loads(text)


def ask_model_for_mapping(headers):
    lines = []
    for index, label in headers:
        lines.append(str(index) + ": " + label)

    response = client.responses.create(
        model=MODEL,
        input=MAPPING_PROMPT + "\n".join(lines)
    )
    return parse_json_answer(response.output_text)


def read_metadata(sheet, header_row_number):
    lines = []
    for row in sheet.iter_rows(max_row=header_row_number - 1, values_only=True):
        cells = []
        for value in row:
            if value is not None and str(value).strip():
                cells.append(str(value).strip())
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_situations(sheet, header_row_number, mapping):
    situations = []

    for number, row in enumerate(
        sheet.iter_rows(min_row=header_row_number + 1, values_only=True),
        start=header_row_number + 1
    ):
        situation = {"row": number}
        filled = 0

        for index, value in enumerate(row, start=1):
            role = mapping.get(str(index), "ignore")
            if role == "ignore":
                continue

            if value is None:
                text = ""
            else:
                text = str(value).strip()

            situation[role] = text
            if text:
                filled = filled + 1

        if filled >= MIN_FILLED_FIELDS:
            situations.append(situation)

    return situations


workbook = load_workbook(EXCEL_FILE, data_only=True)
sheet = workbook.worksheets[0]

header_row_number = find_header_row(sheet)
headers = read_headers(sheet, header_row_number)

if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, "r", encoding="utf-8") as file:
        mapping = json.load(file)
    print("Existing mapping loaded")
else:
    mapping = ask_model_for_mapping(headers)

print("Column mapping:")
for index, label in headers:
    print("  ", str(index).rjust(2), label[:36].ljust(36), "->", mapping.get(str(index), "ignore"))
print()

answer = input("Is this mapping correct? (y/n): ")
if answer.strip().lower() != "y":
    print("Aborted. Edit", MAPPING_FILE, "and run again.")
    exit()

with open(MAPPING_FILE, "w", encoding="utf-8") as file:
    json.dump(mapping, file, indent=2, ensure_ascii=False)

metadata = read_metadata(sheet, header_row_number)
situations = extract_situations(sheet, header_row_number, mapping)

lines = []
lines.append("RISK ASSESSMENT")
lines.append("")
lines.append("Document information:")
lines.append(metadata)
lines.append("")
lines.append("Risk situations: " + str(len(situations)))
lines.append("")

for situation in situations:
    lines.append("--- Risk situation, spreadsheet row " + str(situation["row"]) + " ---")
    for key, label in EXPORT_FIELDS:
        value = situation.get(key, "")
        if not value:
            value = "(not specified)"
        lines.append(label + ": " + value)
    lines.append("")

with open(TEXT_FILE, "w", encoding="utf-8") as file:
    file.write("\n".join(lines))

print("Written:", TEXT_FILE, "-", len(situations), "risk situations")