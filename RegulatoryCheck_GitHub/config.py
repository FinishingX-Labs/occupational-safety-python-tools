# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

"""
Configuration for the regulatory comparison tool.

Everything that a user may want to change lives here.
No other file needs to be edited to run the tool on new documents.
"""

# ---------------------------------------------------------------------------
# Input files
# ---------------------------------------------------------------------------
# The document to be checked: a procedure, an instruction, a paragraph.
# Accepted formats: .docx, .pdf, .txt, .md
DOCUMENT_FILE = "TEST_procedure.docx"

# The regulatory text supplied by the user: an article, an extract, a section.
# Accepted formats: .docx, .pdf, .txt, .md
REGULATION_FILE = "TEST_regulation.txt"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
OUTPUT_FILE = "comparison.xlsx"

# Requirements extracted from the regulation are cached here, so that a second
# run does not pay for the same extraction twice. Delete it to start over.
REQUIREMENTS_FILE = "requirements.json"

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
MODEL = "gpt-5.5"

# ---------------------------------------------------------------------------
# Output language
# ---------------------------------------------------------------------------
LANGUAGES = {
    "1": "French",
    "2": "English",
    "3": "German",
}
DEFAULT_LANGUAGE = "English"

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
# The whole document is sent with every requirement, so a very long document
# becomes expensive. The tool warns above this size.
MAX_DOCUMENT_CHARS = 40000

# Set to a small number for a first run, then back to None.
REQUIREMENT_LIMIT = None

# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------
COVERED = "COVERED_AND_CONSISTENT"
DIVERGENT = "COVERED_BUT_DIVERGENT"
NOT_COVERED = "NOT_COVERED"
UNCLEAR = "UNCLEAR"

VERDICTS = [COVERED, DIVERGENT, NOT_COVERED, UNCLEAR]

# Fill colours used in the spreadsheet.
VERDICT_COLOURS = {
    COVERED: "C6EFCE",     # green
    DIVERGENT: "FFEB9C",   # amber
    NOT_COVERED: "FFC7CE", # red
    UNCLEAR: "D9D9D9",     # grey
}

# ---------------------------------------------------------------------------
# Spreadsheet layout
# ---------------------------------------------------------------------------
COLUMNS = [
    "No.",
    "Source in the regulation",
    "Nature",
    "Requirement",
    "Verdict",
    "Where in the document",
    "Quoted extract",
    "Observation",
]

COLUMN_WIDTHS = [6, 22, 14, 55, 26, 20, 55, 70]

RESULT_SHEET = "Comparison"
HEADER_SHEET = "About this check"