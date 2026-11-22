# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

# ============================================================
#  Project configuration
#  This is the only file you need to edit to analyse a new
#  presentation. No other file should be modified.
# ============================================================

# --- Input and output files ---------------------------------
PPTX_FILE = "presentation.pptx"
CSV_FILE = "output/slides.csv"
OUTPUT_PPTX_FILE = "output/presentation_reviewed.pptx"
FILTERED_PPTX_FILE = "output/presentation_filtered.pptx"
CSV_DELIMITER = ";"

# --- Reference document folders -----------------------------
LEGAL_FOLDER = "reference_documents/legal"
INTERNAL_FOLDER = "reference_documents/internal"
RISK_FOLDER = "reference_documents/risk_assessment"

# --- Models -------------------------------------------------
VISION_MODEL = "gpt-5.4-mini"
COMPLIANCE_MODEL = "gpt-5.5"

# --- Language -----------------------------------------------
DEFAULT_LANGUAGE = "French"

# --- Processing limits --------------------------------------
EXTRACTION_SLIDE_LIMIT = None
COMPLIANCE_SLIDE_LIMIT = None

MIN_CONTENT_LENGTH = 150
MAX_SELECTION_PREVIEW = 400

FORCE_EXTRACTION = False

# --- CSV structure ------------------------------------------
SLIDE_NUMBER_COLUMN = "Slide Nr."
SLIDE_CONTENT_COLUMN = "Slide content"
SPEAKER_NOTES_COLUMN = "Speaker notes"
IMAGE_TEXT_COLUMN = "Image text"
LEGAL_COLUMN = "Compliance check - Legal"
INTERNAL_COLUMN = "Compliance check - Internal documents"
RISK_COLUMN = "Compliance check - Risk assessment"
TRANSLATION_COLUMN = "Slide content - translated"

COLUMNS = [
    SLIDE_NUMBER_COLUMN,
    SLIDE_CONTENT_COLUMN,
    SPEAKER_NOTES_COLUMN,
    IMAGE_TEXT_COLUMN,
    LEGAL_COLUMN,
    INTERNAL_COLUMN,
    RISK_COLUMN,
    TRANSLATION_COLUMN,
]