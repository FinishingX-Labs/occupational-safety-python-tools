# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0



from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openai import OpenAI
from dotenv import load_dotenv
from prompts import (
    PROMPT_REVIEW_ENTRY,
    PROMPT_GRID_ONLY,
    PROMPT_STANDARD_ONLY,
    PROMPT_GRID_AND_STANDARD,
)
from datetime import date
import json
import os

load_dotenv(override=True)
client = OpenAI()

EXCEL_FILE = "AUDIT_TEST_ISO14001_findings.xlsx"
OUTPUT_FILE = "iso14001_reviewed.xlsx"
MAPPING_FILE = "column_mapping.json"
SCALE_FILE = "rating_scale.txt"
MODEL = "gpt-5.5"
DEFAULT_LANGUAGE = "French"

REFERENCE_STORE_ID = os.environ.get("REFERENCE_STORE_ID")

SEARCH_ROWS = 60
MIN_REQUIREMENT_ROWS = 3
MIN_REQUIREMENT_LENGTH = 45
MAX_SECTION_LENGTH = 160
ENTRY_LIMIT = None          # set to a small number for a test run

ANSWER_ROLES = ["applicable", "actual_score", "evidence", "comment", "improvement"]

FIELD_LABELS = [
    ("applicable", "Applicable"),
    ("weight", "Weight of this question in the chapter total, in points"),
    ("actual_score", "Result recorded by the auditor, on the rating scale above"),
    ("evidence", "Objective evidence recorded"),
    ("comment", "Auditor's comment"),
    ("improvement", "Improvement, action or deadline recorded"),
]

LANGUAGES = {
    "1": "French",
    "2": "English",
    "3": "German",
}

SOURCES = {
    "1": "GRID",
    "2": "STANDARD",
    "3": "BOTH",
    "4": "NONE",
}

STATUS_COLORS = {
    "BEFORE_ISSUE": "F8CBAD",
    "WORTH_REVIEWING": "FFE699",
    "OK": "C6E0B4",
    "UNKNOWN": "D9D9D9",
}

INTERFACE = {
    "French": {
        "sheet": "Relecture IA",
        "status_header": "Relecture — statut",
        "obs_header": "Relecture — observations",
        "title": "Relecture assistée de l'audit",
        "file": "Fichier analysé",
        "date": "Date",
        "scale": "Échelle déclarée",
        "req_source": "Source des exigences",
        "source_grid": "énoncées dans la grille",
        "source_standard": "lues dans le corpus de référence",
        "source_both": "énoncées dans la grille et vérifiées dans le corpus",
        "disclaimer": "Cet outil relit le dossier d'audit. Il n'évalue pas l'organisme audité et ne propose aucune note.",
        "summary": "Synthèse",
        "columns": ["Onglet", "Ligne", "Article", "Exigence", "Observations"],
        "labels": {
            "BEFORE_ISSUE": "À corriger avant diffusion",
            "WORTH_REVIEWING": "À revoir",
            "OK": "Rien à signaler",
            "UNKNOWN": "Non analysé",
        },
    },
    "English": {
        "sheet": "AI review",
        "status_header": "Review — status",
        "obs_header": "Review — observations",
        "title": "Assisted audit review",
        "file": "File analysed",
        "date": "Date",
        "scale": "Declared rating scale",
        "req_source": "Source of the requirements",
        "source_grid": "stated in the grid",
        "source_standard": "read from the reference corpus",
        "source_both": "stated in the grid and checked against the corpus",
        "disclaimer": "This tool reviews the audit record. It does not assess the audited organisation and proposes no score.",
        "summary": "Summary",
        "columns": ["Sheet", "Row", "Clause", "Requirement", "Observations"],
        "labels": {
            "BEFORE_ISSUE": "To correct before issue",
            "WORTH_REVIEWING": "Worth reviewing",
            "OK": "Nothing to report",
            "UNKNOWN": "Not analysed",
        },
    },
    "German": {
        "sheet": "KI-Prüfung",
        "status_header": "Prüfung — Status",
        "obs_header": "Prüfung — Anmerkungen",
        "title": "Unterstützte Prüfung des Audits",
        "file": "Analysierte Datei",
        "date": "Datum",
        "scale": "Erklärte Bewertungsskala",
        "req_source": "Quelle der Anforderungen",
        "source_grid": "im Raster angegeben",
        "source_standard": "aus dem Referenzkorpus gelesen",
        "source_both": "im Raster angegeben und mit dem Korpus abgeglichen",
        "disclaimer": "Dieses Werkzeug prüft die Auditunterlagen. Es bewertet nicht die auditierte Organisation und schlägt keine Bewertung vor.",
        "summary": "Zusammenfassung",
        "columns": ["Registerblatt", "Zeile", "Abschnitt", "Anforderung", "Anmerkungen"],
        "labels": {
            "BEFORE_ISSUE": "Vor Freigabe zu korrigieren",
            "WORTH_REVIEWING": "Zu überprüfen",
            "OK": "Nichts zu vermelden",
            "UNKNOWN": "Nicht analysiert",
        },
    },
}

MAPPING_PROMPT = """You are mapping the columns of a completed audit grid.

Assign to each column ONE of the following roles, or "ignore" if none applies:
question, applicable, weight, actual_score, evidence, comment, improvement, ignore

Definitions:
- question: the audit question, requirement or criterion being assessed, or its reference when the text is not given
- applicable: whether the item applies to the audited organisation
- weight: the share of the chapter total allocated to this item, in points. Not a performance value.
- actual_score: the result, score, rating or classification recorded by the auditor
- evidence: the objective evidence recorded — documents, records, observations
- comment: the auditor's own comment, note or justification, when it is a column distinct from the evidence
- improvement: the improvement, recommended action, owner or deadline recorded by the auditor

Several columns may share the same role. Use "ignore" for anything administrative such as initials, time spent or internal codes.

Answer with JSON only, no explanation, in exactly this form:
{"1": "question", "2": "applicable", "3": "ignore"}

COLUMN HEADERS:
"""


def ask_language():
    print("Language of the review written into the file:")
    for key in sorted(LANGUAGES):
        print("  " + key + " - " + LANGUAGES[key])
    answer = input("Choice [1]: ").strip()
    return LANGUAGES.get(answer, DEFAULT_LANGUAGE)


def ask_requirement_source():
    print()
    print("Where are the requirements the audit is reviewed against?")
    print("  1 - Stated in the grid")
    print("  2 - Only in the standard, the grid cites references such as '6.1.3'")
    print("  3 - Both: stated in the grid and available as a standard")
    print("  4 - Neither")
    answer = input("Choice [1]: ").strip()
    return SOURCES.get(answer, "GRID")


def status_from_label(text):
    clean = str(text).strip()
    for lang in INTERFACE:
        for status, label in INTERFACE[lang]["labels"].items():
            if label == clean:
                return status
    return None


def count_requirement_rows(sheet):
    count = 0
    for row in sheet.iter_rows(max_row=min(sheet.max_row, SEARCH_ROWS), max_col=4, values_only=True):
        for value in row:
            if value is None:
                continue
            if len(str(value).strip()) >= MIN_REQUIREMENT_LENGTH:
                count = count + 1
                break
    return count


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
    values = list(sheet.iter_rows(min_row=row_number, max_row=row_number, values_only=True))[0]
    headers = []
    for index, value in enumerate(values, start=1):
        if value is not None and str(value).strip():
            headers.append((index, " ".join(str(value).split())))
    return headers


def header_signature(headers):
    parts = []
    for index, label in headers:
        parts.append(str(index) + ":" + label)
    return " | ".join(parts)


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
    response = client.responses.create(model=MODEL, input=MAPPING_PROMPT + "\n".join(lines))
    return parse_json_answer(response.output_text)


def show_mapping(sheet_name, header_row, headers, mapping):
    print("Sheet:", sheet_name, "| header row:", header_row)
    for index, label in headers:
        print("   ", str(index).rjust(2), label[:40].ljust(40), "->", mapping.get(str(index), "ignore"))
    print()


def columns_for(mapping, role):
    found = []
    for index, assigned in mapping.items():
        if assigned == role:
            found.append(int(index))
    return sorted(found)


def cell_texts(sheet, row_number, mapping, role):
    parts = []
    for column in columns_for(mapping, role):
        value = sheet.cell(row=row_number, column=column).value
        if value is not None and str(value).strip():
            parts.append(" ".join(str(value).split()))
    return " | ".join(parts)


def extract_entries(sheet, header_row, mapping, source):
    entries = []
    current_section = ""
    text_in_grid = source in ["GRID", "BOTH"]

    for row_number in range(header_row + 1, sheet.max_row + 1):
        question = cell_texts(sheet, row_number, mapping, "question")
        if not question:
            continue

        answered = False
        for role in ANSWER_ROLES:
            if cell_texts(sheet, row_number, mapping, role):
                answered = True

        if not answered:
            if text_in_grid and len(question) > MAX_SECTION_LENGTH:
                continue
            current_section = question
            continue

        entry = {
            "sheet": sheet.title,
            "row": row_number,
            "section": current_section,
            "question": question,
            "answered": answered,
        }
        for role, label in FIELD_LABELS:
            entry[role] = cell_texts(sheet, row_number, mapping, role)

        entries.append(entry)

    return entries


def get_rating_scale(entries):
    if os.path.exists(SCALE_FILE):
        with open(SCALE_FILE, "r", encoding="utf-8") as file:
            scale = file.read().strip()
        if scale:
            print("Rating scale loaded from", SCALE_FILE)
            return scale

    values = []
    for entry in entries:
        value = entry.get("actual_score", "")
        if value and value not in values:
            values.append(value)

    print("Result values found in the grid:", sorted(values))
    print("Describe the rating scale in one line, for example:")
    print("  C = conform, NC-minor = minor nonconformity, NC-major = major, OFI = opportunity")
    scale = input("Scale: ").strip()

    with open(SCALE_FILE, "w", encoding="utf-8") as file:
        file.write(scale)

    return scale


def format_entry(entry, mapping, scale, language, source):
    if source == "STANDARD":
        requirement_line = "Reference of the requirement, to be retrieved from the corpus: " + entry["question"]
    else:
        requirement_line = "Requirement assessed: " + entry["question"]

    lines = [
        "RATING SCALE: " + scale,
        "OUTPUT LANGUAGE: " + language,
        "",
        "Clause: " + (entry["section"] or "(not identified)"),
        requirement_line,
    ]

    missing = []
    for role, label in FIELD_LABELS:
        if columns_for(mapping, role):
            lines.append(label + ": " + (entry[role] or "(empty)"))
        else:
            missing.append(label)

    if missing:
        lines.append("")
        lines.append("ABSENT FROM THIS GRID: " + "; ".join(missing))

    return "\n".join(lines)


def review_prompt_prefix(source):
    if source == "STANDARD":
        return PROMPT_STANDARD_ONLY
    if source == "BOTH":
        return PROMPT_GRID_AND_STANDARD
    return PROMPT_GRID_ONLY


def review_entry(entry, mapping, scale, language, source):
    full_input = (
        review_prompt_prefix(source)
        + PROMPT_REVIEW_ENTRY
        + format_entry(entry, mapping, scale, language, source)
    )

    if source in ["STANDARD", "BOTH"]:
        response = client.responses.create(
            model=MODEL,
            input=full_input,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [REFERENCE_STORE_ID]
            }]
        )
    else:
        response = client.responses.create(model=MODEL, input=full_input)

    return response.output_text.strip()


def read_status(review):
    for line in review.split("\n"):
        clean = line.strip()
        if clean.upper().startswith("STATUS:"):
            return clean.split(":", 1)[1].strip().upper()
    return "UNKNOWN"


def read_observations(review):
    lines = []
    for line in review.split("\n"):
        clean = line.strip()
        if clean.startswith("-"):
            lines.append(clean.lstrip("- ").strip())
    return "\n".join(lines)


def review_columns(mapping):
    last = 0
    for index in mapping:
        if int(index) > last:
            last = int(index)
    return last + 2, last + 3


def source_label(words, source):
    if source == "STANDARD":
        return words["source_standard"]
    if source == "BOTH":
        return words["source_both"]
    return words["source_grid"]


def build_summary_sheet(book, entries, scale, language, source):
    words = INTERFACE[language]

    for other in INTERFACE:
        name = INTERFACE[other]["sheet"]
        if name in book.sheetnames:
            del book[name]

    sheet = book.create_sheet(words["sheet"])
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 8
    sheet.column_dimensions["C"].width = 26
    sheet.column_dimensions["D"].width = 52
    sheet.column_dimensions["E"].width = 70

    sheet["A1"] = words["title"]
    sheet["A1"].font = Font(name="Arial", size=14, bold=True)
    sheet["A2"] = words["file"] + " : " + EXCEL_FILE + "   |   " + words["date"] + " : " + date.today().strftime("%d/%m/%Y")
    sheet["A3"] = words["scale"] + " : " + scale
    sheet["A3"].alignment = Alignment(wrap_text=True)

    sheet["A4"] = words["req_source"] + " : " + source_label(words, source)
    sheet["A4"].font = Font(name="Arial", size=10, bold=True)

    sheet["A6"] = words["disclaimer"]
    sheet["A6"].font = Font(name="Arial", size=10, italic=True)

    counts = {}
    for entry in entries:
        status = entry.get("status", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1

    row = 8
    sheet.cell(row=row, column=1, value=words["summary"]).font = Font(name="Arial", size=11, bold=True)
    row = row + 1
    for status in ["BEFORE_ISSUE", "WORTH_REVIEWING", "OK", "UNKNOWN"]:
        if status in counts:
            sheet.cell(row=row, column=1, value=words["labels"][status])
            sheet.cell(row=row, column=2, value=counts[status])
            sheet.cell(row=row, column=1).fill = PatternFill("solid", fgColor=STATUS_COLORS[status])
            row = row + 1

    row = row + 2
    for i, label in enumerate(words["columns"], start=1):
        cell = sheet.cell(row=row, column=i, value=label)
        cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="44546A")
    header_row = row
    row = row + 1

    for status in ["BEFORE_ISSUE", "WORTH_REVIEWING"]:
        for entry in entries:
            if entry.get("status") != status:
                continue
            sheet.cell(row=row, column=1, value=entry["sheet"])
            sheet.cell(row=row, column=2, value=entry["row"])
            sheet.cell(row=row, column=3, value=entry["section"][:60])
            sheet.cell(row=row, column=4, value=entry["question"][:220])
            sheet.cell(row=row, column=5, value=entry.get("observations", ""))
            for col in range(1, 6):
                sheet.cell(row=row, column=col).alignment = Alignment(wrap_text=True, vertical="top")
            sheet.cell(row=row, column=1).fill = PatternFill("solid", fgColor=STATUS_COLORS[status])
            sheet.row_dimensions[row].height = 46
            row = row + 1

    sheet.freeze_panes = "A" + str(header_row + 1)


# ---------------------------------------------------------------- main

language = ask_language()
words = INTERFACE[language]
print("Review language:", language)

source = ask_requirement_source()

if source == "NONE":
    print()
    print("The requirements are neither stated in the grid nor available as a standard.")
    print("The tool has nothing to review the auditor's entries against, and will not run.")
    exit()

if source in ["STANDARD", "BOTH"] and not REFERENCE_STORE_ID:
    if source == "STANDARD":
        print()
        print("The grid only cites references, and no reference corpus is configured.")
        print("The tool has nothing to review the auditor's entries against, and will not run.")
        print()
        print("Place the applicable standard in the reference_documents folder,")
        print("run setup_reference_store.py, and add REFERENCE_STORE_ID to your .env file.")
        exit()

    print()
    print("No reference corpus is configured. Falling back to the grid text only.")
    source = "GRID"

print()
print("Requirement source:", source)
print()

values_book = load_workbook(EXCEL_FILE, data_only=True)

candidates = []
for sheet in values_book.worksheets:
    if count_requirement_rows(sheet) >= MIN_REQUIREMENT_ROWS:
        candidates.append(sheet.title)

print("Sheets proposed for review:", candidates)
answer = input("Use these sheets? (y/n): ")
if answer.strip().lower() != "y":
    typed = input("Type the sheet names, separated by commas: ")
    candidates = []
    for name in typed.split(","):
        clean = name.strip()
        if clean in values_book.sheetnames:
            candidates.append(clean)
    print("Sheets used:", candidates)
print()

if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, "r", encoding="utf-8") as file:
        saved = json.load(file)
    print("Existing mapping loaded from", MAPPING_FILE)
    print()
else:
    saved = {}

by_signature = {}
result = {}

for sheet_name in candidates:
    sheet = values_book[sheet_name]
    header_row = find_header_row(sheet)
    headers = read_headers(sheet, header_row)
    signature = header_signature(headers)

    if sheet_name in saved:
        mapping = saved[sheet_name]["columns"]
    elif signature in by_signature:
        mapping = by_signature[signature]
        print("Sheet", sheet_name, "reuses the mapping of an identical header.")
    else:
        mapping = ask_model_for_mapping(headers)

    by_signature[signature] = mapping
    result[sheet_name] = {"header_row": header_row, "columns": mapping}
    show_mapping(sheet_name, header_row, headers, mapping)

if not saved:
    answer = input("Are these mappings correct? (y/n): ")
    if answer.strip().lower() != "y":
        print("Not confirmed. You can edit", MAPPING_FILE, "by hand and run again.")
        exit()

with open(MAPPING_FILE, "w", encoding="utf-8") as file:
    json.dump(result, file, indent=2, ensure_ascii=False)

all_entries = []
for sheet_name in candidates:
    sheet = values_book[sheet_name]
    all_entries.extend(extract_entries(
        sheet, result[sheet_name]["header_row"], result[sheet_name]["columns"], source))

print("Requirements extracted:", len(all_entries))
print()

scale = get_rating_scale(all_entries)
print()

try:
    open(OUTPUT_FILE, "a").close()
except PermissionError:
    print("Please close", OUTPUT_FILE, "in Excel before running this script.")
    exit()

if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
    output_book = load_workbook(OUTPUT_FILE)
    print("Resuming from", OUTPUT_FILE)
else:
    output_book = load_workbook(EXCEL_FILE)
    print("Creating", OUTPUT_FILE)
print()

for sheet_name in candidates:
    mapping = result[sheet_name]["columns"]
    header_row = result[sheet_name]["header_row"]
    status_col, obs_col = review_columns(mapping)
    sheet = output_book[sheet_name]

    cell = sheet.cell(row=header_row, column=status_col, value=words["status_header"])
    cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="44546A")

    cell = sheet.cell(row=header_row, column=obs_col, value=words["obs_header"])
    cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="44546A")

    sheet.column_dimensions[get_column_letter(status_col)].width = 26
    sheet.column_dimensions[get_column_letter(obs_col)].width = 70

reviewed = 0

for entry in all_entries:
    mapping = result[entry["sheet"]]["columns"]
    status_col, obs_col = review_columns(mapping)
    sheet = output_book[entry["sheet"]]

    existing = sheet.cell(row=entry["row"], column=status_col).value
    known = None
    if existing is not None and str(existing).strip():
        known = status_from_label(existing)

    if known is not None:
        entry["status"] = known
        entry["observations"] = sheet.cell(row=entry["row"], column=obs_col).value or ""
        continue

    if ENTRY_LIMIT is not None and reviewed >= ENTRY_LIMIT:
        continue

    review = review_entry(entry, mapping, scale, language, source)
    status = read_status(review)
    observations = read_observations(review)

    entry["status"] = status
    entry["observations"] = observations

    cell = sheet.cell(row=entry["row"], column=status_col, value=words["labels"].get(status, status))
    cell.fill = PatternFill("solid", fgColor=STATUS_COLORS.get(status, "FFFFFF"))
    cell.alignment = Alignment(wrap_text=True, vertical="top")

    cell = sheet.cell(row=entry["row"], column=obs_col, value=observations)
    cell.alignment = Alignment(wrap_text=True, vertical="top")

    output_book.save(OUTPUT_FILE)
    reviewed = reviewed + 1
    print("Reviewed", entry["sheet"], "row", entry["row"], "|", status)

build_summary_sheet(output_book, all_entries, scale, language, source)
output_book.save(OUTPUT_FILE)

counts = {}
for entry in all_entries:
    status = entry.get("status", "UNKNOWN")
    counts[status] = counts.get(status, 0) + 1

print()
print("Done.", reviewed, "entries reviewed in this run |", counts)
print("Written to:", OUTPUT_FILE)