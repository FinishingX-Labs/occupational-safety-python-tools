# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0
"""
Regulatory comparison tool.

The user supplies two things: a document of their own, and the text of a
regulatory provision. The tool breaks the provision into discrete
requirements, then reports, for each one, what the document says about it.

It never concludes that the document is compliant. That is a judgement for a
qualified person.
"""

import json
import os
import re
import datetime

from dotenv import load_dotenv
from openai import OpenAI
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

import config
import prompts
from readers import read_file, number_paragraphs

# override=True: a stale variable left in the terminal session must never win
# over the .env file. This cost us an afternoon on the first project.
load_dotenv(override=True)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# Model access
# ---------------------------------------------------------------------------

def call_model(prompt):
    """One call to the Responses API, returning plain text."""
    response = client.responses.create(
        model=config.MODEL,
        input=prompt,
    )
    return response.output_text


def parse_json(text):
    """Read the JSON the model returned, tolerating a code fence around it."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to the outermost array or object in the reply.
        for opening, closing in (("[", "]"), ("{", "}")):
            start = cleaned.find(opening)
            end = cleaned.rfind(closing)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    continue
        raise


# ---------------------------------------------------------------------------
# Step 1 - requirements
# ---------------------------------------------------------------------------

def extract_requirements(regulation_text, language):
    """Break the regulatory text into a list of discrete requirements."""
    prompt = prompts.localise(prompts.PROMPT_EXTRACT_REQUIREMENTS, language)
    reply = call_model(prompt + regulation_text)
    requirements = parse_json(reply)

    if not isinstance(requirements, list) or not requirements:
        raise ValueError(
            "The model did not return a usable list of requirements.\n"
            "Check that the regulatory file really contains the text of a "
            "provision, and not just its reference."
        )

    cleaned = []
    for entry in requirements:
        cleaned.append({
            "source": str(entry.get("source", "")).strip(),
            "nature": str(entry.get("nature", "")).strip().upper(),
            "requirement": str(entry.get("requirement", "")).strip(),
        })

    return [entry for entry in cleaned if entry["requirement"]]


def load_or_build_requirements(regulation_text, language):
    """Reuse the cached requirements, or build and cache them."""
    if os.path.exists(config.REQUIREMENTS_FILE):
        with open(config.REQUIREMENTS_FILE, "r", encoding="utf-8") as handle:
            requirements = json.load(handle)
        print("Requirements loaded from " + config.REQUIREMENTS_FILE + ".")
        print("Delete that file to extract them again.\n")
        return requirements

    print("Reading the regulatory text...\n")
    requirements = extract_requirements(regulation_text, language)

    with open(config.REQUIREMENTS_FILE, "w", encoding="utf-8") as handle:
        json.dump(requirements, handle, ensure_ascii=False, indent=2)

    return requirements


def confirm_requirements(requirements):
    """Show the requirements and let the user accept or stop.

    The whole comparison rests on this list. A bad split here produces a clean
    looking spreadsheet full of wrong questions, so it is worth thirty seconds
    of reading.
    """
    print("=" * 70)
    print(str(len(requirements)) + " requirements found in the regulatory text")
    print("=" * 70 + "\n")

    for index, entry in enumerate(requirements, start=1):
        print(str(index) + ". [" + entry["nature"] + "] " + entry["source"])
        print("   " + entry["requirement"] + "\n")

    print("-" * 70)
    answer = input("Use this list? (y = yes / n = stop and edit the file): ").strip().lower()

    if answer != "y":
        print("\nStopped. Edit " + config.REQUIREMENTS_FILE + " by hand, or delete")
        print("it to have the text read again, then run the tool once more.")
        return False

    print()
    return True


# ---------------------------------------------------------------------------
# Step 2 - comparison
# ---------------------------------------------------------------------------

def normalise(text):
    """Lowercase and collapse whitespace, for comparing quoted text."""
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_extract(extract, document_text):
    """Check that the quoted extract really appears in the document.

    A model can produce a plausible quotation that the document never
    contained. This check is deterministic and free, and it is the only part
    of the tool that cannot be fooled.
    """
    if not extract:
        return True

    needle = normalise(extract)
    haystack = normalise(document_text)

    if needle in haystack:
        return True

    # A quotation spanning several paragraphs may carry a separator the
    # document does not have. Accept it if every long fragment is present.
    fragments = [f for f in re.split(r"[\[\]\n…]|\.\.\.", extract) if len(f.strip()) > 25]
    if fragments:
        return all(normalise(f) in haystack for f in fragments)

    return False


def compare_requirement(entry, numbered_document, language):
    """Compare one requirement against the whole document."""
    prompt = prompts.localise(prompts.PROMPT_COMPARE, language)

    prompt += "\n\nREQUIREMENT\n-----------\n"
    prompt += "Source: " + entry["source"] + "\n"
    prompt += "Nature: " + entry["nature"] + "\n"
    prompt += entry["requirement"] + "\n"
    prompt += "\n\nDOCUMENT\n--------\n" + numbered_document + "\n"

    result = parse_json(call_model(prompt))

    verdict = str(result.get("verdict", "")).strip().upper()
    if verdict not in config.VERDICTS:
        verdict = config.UNCLEAR

    location = str(result.get("location", "")).strip()
    extract = str(result.get("extract", "")).strip()
    observation = str(result.get("observation", "")).strip()

    # A verdict of NOT_COVERED must not carry a quotation.
    if verdict == config.NOT_COVERED:
        location = ""
        extract = ""

    return {
        "verdict": verdict,
        "location": location,
        "extract": extract,
        "observation": observation,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def build_workbook(requirements):
    """Create the spreadsheet with one empty row per requirement."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = config.RESULT_SHEET

    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="44546A")

    for column, title in enumerate(config.COLUMNS, start=1):
        cell = sheet.cell(row=1, column=column, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    for column, width in enumerate(config.COLUMN_WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width

    sheet.freeze_panes = "A2"

    for index, entry in enumerate(requirements, start=1):
        row = index + 1
        sheet.cell(row=row, column=1, value=index)
        sheet.cell(row=row, column=2, value=entry["source"])
        sheet.cell(row=row, column=3, value=entry["nature"])
        sheet.cell(row=row, column=4, value=entry["requirement"])
        for column in range(1, len(config.COLUMNS) + 1):
            sheet.cell(row=row, column=column).alignment = Alignment(
                vertical="top", wrap_text=True
            )

    return workbook


def open_workbook(requirements):
    """Reuse an existing result file, or start a new one.

    Reusing it is what makes the run resumable: an interrupted session picks up
    where it stopped instead of paying for every requirement again.
    """
    if os.path.exists(config.OUTPUT_FILE):
        try:
            workbook = load_workbook(config.OUTPUT_FILE)
        except Exception:
            print("The existing " + config.OUTPUT_FILE + " could not be read.")
            print("Starting a new one.\n")
            return build_workbook(requirements)

        if config.RESULT_SHEET in workbook.sheetnames:
            sheet = workbook[config.RESULT_SHEET]
            if sheet.max_row - 1 == len(requirements):
                print("Existing results found. Filled rows will be skipped.\n")
                return workbook

        print("The existing file does not match this list of requirements.")
        print("Starting a new one.\n")

    return build_workbook(requirements)


def write_result(sheet, row, result):
    """Write one comparison into the sheet."""
    verdict_column = config.COLUMNS.index("Verdict") + 1

    sheet.cell(row=row, column=verdict_column, value=result["verdict"])
    sheet.cell(row=row, column=verdict_column + 1, value=result["location"])
    sheet.cell(row=row, column=verdict_column + 2, value=result["extract"])
    sheet.cell(row=row, column=verdict_column + 3, value=result["observation"])

    colour = config.VERDICT_COLOURS.get(result["verdict"])
    if colour:
        cell = sheet.cell(row=row, column=verdict_column)
        cell.fill = PatternFill("solid", fgColor=colour)
        cell.font = Font(name="Arial", bold=True)

    for column in range(verdict_column, verdict_column + 4):
        sheet.cell(row=row, column=column).alignment = Alignment(
            vertical="top", wrap_text=True
        )


def add_header_sheet(workbook, requirements, counts, language):
    """Record what was compared, and what the result does not mean."""
    if config.HEADER_SHEET in workbook.sheetnames:
        del workbook[config.HEADER_SHEET]

    sheet = workbook.create_sheet(config.HEADER_SHEET, 0)
    sheet.column_dimensions["A"].width = 34
    sheet.column_dimensions["B"].width = 78

    rows = [
        ("Document checked", config.DOCUMENT_FILE),
        ("Regulatory text", config.REGULATION_FILE),
        ("Date of the check", datetime.date.today().strftime("%d/%m/%Y")),
        ("Model", config.MODEL),
        ("Output language", language),
        ("Requirements compared", str(len(requirements))),
        ("", ""),
        ("Covered and consistent", str(counts.get(config.COVERED, 0))),
        ("Covered but divergent", str(counts.get(config.DIVERGENT, 0))),
        ("Not covered", str(counts.get(config.NOT_COVERED, 0))),
        ("Unclear", str(counts.get(config.UNCLEAR, 0))),
        ("", ""),
        ("What this file is",
         "A comparison between one document and one regulatory text supplied "
         "by the user. Each line reports what the document says about one "
         "requirement."),
        ("What it is not",
         "It is not a compliance assessment. The tool does not conclude that "
         "the document complies, and a full set of green lines does not mean "
         "the document is lawful: only the requirements contained in the "
         "supplied text were examined."),
        ("Points to keep in mind",
         "A national transposition may be stricter than the text used here. A "
         "collective agreement or an internal standard may add obligations. A "
         "requirement may be worded correctly and still be inapplicable to "
         "the situation. Every line is a starting point for a human check, "
         "not a conclusion."),
        ("Quotation check",
         "Every quoted extract was verified against the document. Any "
         "quotation that could not be found verbatim is flagged in the "
         "observation column."),
    ]

    bold = Font(name="Arial", bold=True)
    for index, (label, value) in enumerate(rows, start=1):
        cell = sheet.cell(row=index, column=1, value=label)
        cell.font = bold
        cell.alignment = Alignment(vertical="top")
        sheet.cell(row=index, column=2, value=value).alignment = Alignment(
            vertical="top", wrap_text=True
        )

    return sheet


def save(workbook):
    """Save, with a readable message if the file is open in Excel."""
    try:
        workbook.save(config.OUTPUT_FILE)
    except PermissionError:
        raise PermissionError(
            config.OUTPUT_FILE + " is open in Excel.\n"
            "Close it and run the tool again. Results already written are kept."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def choose_language():
    print("Language of the output:")
    for key, name in config.LANGUAGES.items():
        print("  " + key + " - " + name)

    answer = input("Your choice [" + config.DEFAULT_LANGUAGE + "]: ").strip()
    language = config.LANGUAGES.get(answer, config.DEFAULT_LANGUAGE)
    print("Output language: " + language + "\n")
    return language


def main():
    print("\n" + "=" * 70)
    print("REGULATORY COMPARISON")
    print("=" * 70 + "\n")

    if not os.environ.get("OPENAI_API_KEY"):
        print("No API key found. Create a .env file containing:")
        print("OPENAI_API_KEY=sk-...")
        return

    language = choose_language()

    document_parts = read_file(config.DOCUMENT_FILE)
    regulation_parts = read_file(config.REGULATION_FILE)

    numbered_document = number_paragraphs(document_parts)
    regulation_text = "\n".join(regulation_parts)

    print("Document: " + str(len(document_parts)) + " paragraphs, "
          + str(len(numbered_document)) + " characters")
    print("Regulatory text: " + str(len(regulation_text)) + " characters\n")

    if len(numbered_document) > config.MAX_DOCUMENT_CHARS:
        print("Warning: the document is long, and it is sent once per")
        print("requirement. Consider checking one section at a time.\n")

    requirements = load_or_build_requirements(regulation_text, language)

    if not confirm_requirements(requirements):
        return

    if config.REQUIREMENT_LIMIT:
        requirements = requirements[:config.REQUIREMENT_LIMIT]
        print("Test run limited to " + str(len(requirements)) + " requirements.\n")

    workbook = open_workbook(requirements)
    sheet = workbook[config.RESULT_SHEET]
    verdict_column = config.COLUMNS.index("Verdict") + 1

    counts = {}

    for index, entry in enumerate(requirements, start=1):
        row = index + 1

        existing = sheet.cell(row=row, column=verdict_column).value
        if existing:
            counts[existing] = counts.get(existing, 0) + 1
            print("[" + str(index) + "/" + str(len(requirements)) + "] already done")
            continue

        print("[" + str(index) + "/" + str(len(requirements)) + "] "
              + entry["source"] + " ... ", end="", flush=True)

        try:
            result = compare_requirement(entry, numbered_document, language)
        except Exception as error:
            print("failed")
            print("   " + str(error))
            print("\nStopping here. Results already written are saved.")
            print("Run the tool again to continue from this requirement.")
            break

        # Deterministic check: the quotation must exist in the document.
        if result["extract"] and not verify_extract(result["extract"], numbered_document):
            result["observation"] = (
                "[QUOTATION NOT FOUND IN THE DOCUMENT - verify this line by hand] "
                + result["observation"]
            )
            result["verdict"] = config.UNCLEAR

        write_result(sheet, row, result)
        counts[result["verdict"]] = counts.get(result["verdict"], 0) + 1
        save(workbook)

        print(result["verdict"])

    add_header_sheet(workbook, requirements, counts, language)
    save(workbook)

    print("\n" + "=" * 70)
    print("Done. Results written to " + config.OUTPUT_FILE)
    for verdict in config.VERDICTS:
        print("  " + verdict + ": " + str(counts.get(verdict, 0)))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()