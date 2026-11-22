# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0


from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPT_RISK_ROW, PROMPT_RISK_DOCUMENT
import json
import os

load_dotenv(override=True)
client = OpenAI()

EXCEL_FILE = "risk_assessment.xlsx"
OUTPUT_FILE = "risk_assessment_reviewed.xlsx"
MAPPING_FILE = "column_mapping.json"
DOCUMENT_SHEET = "AI review"
MODEL = "gpt-5.5"
SEARCH_ROWS = 30
MIN_FILLED_FIELDS = 3
SITUATION_LIMIT = None          # set to a small number to limit a test run

CLIENT_COUNTRY = "FR"

LEGAL_STORES = {
    "FR": os.environ.get("LEGAL_STORE_FR"),
    "DE": os.environ.get("LEGAL_STORE_DE"),
}

COUNTRY_NAMES = {
    "FR": "France",
    "DE": "Germany",
}

FIELD_LABELS = [
    ("unit", "Work unit"),
    ("activity", "Activity"),
    ("hazard", "Hazard"),
    ("situation", "Dangerous situation"),
    ("damage", "Potential harm"),
    ("severity", "Severity (assigned by the assessor)"),
    ("frequency", "Frequency (assigned by the assessor)"),
    ("criticality", "Criticality (assigned by the assessor)"),
    ("existing_measures", "Existing prevention measures"),
    ("planned_actions", "Planned improvement actions"),
    ("owner", "Responsible person"),
    ("deadline", "Deadline"),
    ("status", "Status"),
]

MAPPING_PROMPT = """You are mapping the columns of a workplace risk assessment spreadsheet.

Assign to each column ONE of the following roles, or "ignore" if none applies:
unit, activity, hazard, situation, damage, severity, frequency, criticality,
existing_measures, planned_actions, owner, deadline, status, ignore

Definitions:
- unit: work unit, department, area or site
- activity: job, position or task
- hazard: the hazard itself
- situation: the dangerous situation or exposure described
- damage: the potential harm or injury
- severity, frequency, criticality: the rating columns
- existing_measures: prevention measures already in place
- planned_actions: improvement actions still to be carried out
- owner: person or role responsible for an action
- deadline: due date of an action
- status: progress of an action

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


def show_mapping(headers, mapping):
    print("Proposed column mapping:")
    print()
    for index, label in headers:
        role = mapping.get(str(index), "ignore")
        print("  Column", str(index).rjust(2), "|", label[:38].ljust(38), "->", role)
    print()


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


def field(situation, key):
    value = situation.get(key, "")
    if not value:
        return "(empty)"
    return value


def format_situation(situation):
    lines = []
    for key, label in FIELD_LABELS:
        lines.append(label + ": " + field(situation, key))
    return "\n".join(lines)


def build_prompt(base_prompt, store_id, country_name):
    if store_id:
        header = (
            "APPLICABLE JURISDICTION: " + country_name + ". "
            "Cite only texts applicable in this jurisdiction.\n\n"
        )
    else:
        header = (
            "NO REGULATORY CORPUS IS AVAILABLE for this analysis. "
            "You have no retrieved documents. Every suggestion must therefore be labelled "
            "[TO VERIFY]. Never label anything [SOURCED].\n\n"
        )

    return header + base_prompt


def call_model(full_input, store_id):
    if store_id:
        response = client.responses.create(
            model=MODEL,
            input=full_input,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [store_id]
            }]
        )
    else:
        response = client.responses.create(
            model=MODEL,
            input=full_input
        )

    return response.output_text.strip()


def analyse_situation(situation, store_id, prompt):
    return call_model(prompt + format_situation(situation), store_id)


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


def summarise_situations(situations):
    lines = []

    for situation in situations:
        parts = [
            "Row " + str(situation["row"]),
            field(situation, "unit"),
            field(situation, "activity"),
            "hazard: " + field(situation, "hazard"),
            "S=" + field(situation, "severity") + " F=" + field(situation, "frequency"),
            "existing: " + field(situation, "existing_measures")[:70],
            "action: " + field(situation, "planned_actions")[:70],
            "owner: " + field(situation, "owner"),
            "deadline: " + field(situation, "deadline"),
        ]
        lines.append(" | ".join(parts))

    return "\n".join(lines)


def analyse_document(metadata, situations, store_id, prompt):
    document_text = (
        "DOCUMENT METADATA:\n" + metadata +
        "\n\nRISK SITUATIONS (" + str(len(situations)) + " in total):\n" +
        summarise_situations(situations)
    )

    return call_model(prompt + document_text, store_id)


# ---------------------------------------------------------------- main

store_id = LEGAL_STORES.get(CLIENT_COUNTRY)
country_name = COUNTRY_NAMES.get(CLIENT_COUNTRY, CLIENT_COUNTRY)

if store_id:
    print("Jurisdiction:", country_name, "| corpus available")
else:
    print("Jurisdiction:", country_name, "| NO CORPUS - degraded mode, all suggestions unverified")
print()

values_workbook = load_workbook(EXCEL_FILE, data_only=True)
values_sheet = values_workbook.worksheets[0]

header_row_number = find_header_row(values_sheet)
headers = read_headers(values_sheet, header_row_number)

print("Header row detected:", header_row_number)
print()

if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, "r", encoding="utf-8") as file:
        mapping = json.load(file)
    print("Existing mapping loaded from", MAPPING_FILE)
    print()
else:
    mapping = ask_model_for_mapping(headers)

show_mapping(headers, mapping)

answer = input("Is this mapping correct? (y/n): ")

if answer.strip().lower() != "y":
    print("Mapping not confirmed. You can edit", MAPPING_FILE, "by hand and run again.")
    exit()

with open(MAPPING_FILE, "w", encoding="utf-8") as file:
    json.dump(mapping, file, indent=2, ensure_ascii=False)

situations = extract_situations(values_sheet, header_row_number, mapping)
print()
print("Risk situations extracted:", len(situations))

suggestion_column = 0
for index, label in headers:
    if index > suggestion_column:
        suggestion_column = index
suggestion_column = suggestion_column + 2

if os.path.exists(OUTPUT_FILE):
    output_workbook = load_workbook(OUTPUT_FILE)
    print("Resuming from", OUTPUT_FILE)
else:
    output_workbook = load_workbook(EXCEL_FILE)
    print("Creating", OUTPUT_FILE)

output_sheet = output_workbook.worksheets[0]
output_sheet.cell(row=header_row_number, column=suggestion_column,
                  value="AI suggestions (" + country_name + ")")

row_prompt = build_prompt(PROMPT_RISK_ROW, store_id, country_name)
processed = 0

print()

for situation in situations:
    if SITUATION_LIMIT is not None and processed >= SITUATION_LIMIT:
        break

    cell = output_sheet.cell(row=situation["row"], column=suggestion_column)

    if cell.value is not None and str(cell.value).strip():
        continue

    cell.value = analyse_situation(situation, store_id, row_prompt)
    output_workbook.save(OUTPUT_FILE)

    processed = processed + 1
    print("Row", situation["row"], "analysed")

print()
print("Row-level analysis done:", processed, "situations")
print()

if DOCUMENT_SHEET in output_workbook.sheetnames:
    print("Document review already present in sheet:", DOCUMENT_SHEET, "- skipped")
else:
    print("Running document-level review...")

    metadata = read_metadata(values_sheet, header_row_number)
    document_prompt = build_prompt(PROMPT_RISK_DOCUMENT, store_id, country_name)
    review = analyse_document(metadata, situations, store_id, document_prompt)

    review_sheet = output_workbook.create_sheet(DOCUMENT_SHEET)
    review_sheet.column_dimensions["A"].width = 110

    review_sheet["A1"] = "Document-level review - " + country_name
    review_sheet["A1"].font = Font(bold=True, size=12)

    line_number = 3
    for line in review.split("\n"):
        review_sheet.cell(row=line_number, column=1, value=line).alignment = Alignment(wrap_text=True)
        line_number = line_number + 1

    output_workbook.save(OUTPUT_FILE)
    print("Document review written to sheet:", DOCUMENT_SHEET)

print()
print("Finished:", OUTPUT_FILE)