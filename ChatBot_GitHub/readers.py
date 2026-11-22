# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0



"""
Reading the input file.

The same function reads a .docx, a .pdf, a .txt or a .md, because the tool
makes no assumption about the format the document arrives in.
"""

import os
import re

# A line that ends with one of these is a finished thought.
TERMINAL = (".", ":", ";", "!", "?", '"', "»", ")")

# Below this length, an unpunctuated line is treated as a heading.
HEADING_LENGTH = 70


def reflow(lines):
    """Join lines that belong to the same paragraph.

    Text and PDF files wrap sentences at a fixed width, so a naive reading
    turns one sentence into three paragraphs. That would make the paragraph
    numbers meaningless and would break every quotation, since no quoted
    sentence would exist as a single unit.
    """
    paragraphs = []
    current = ""

    for raw in lines:
        line = raw.strip()

        if not line:
            if current:
                paragraphs.append(current)
                current = ""
            continue

        if not current:
            current = line
            continue

        starts_new_item = bool(re.match(r"^([(\[]?[0-9a-zA-Z][)\].]|[-•*–])\s", line))
        previous_is_finished = current.endswith(TERMINAL)

        # A short unpunctuated line followed by a capital letter is a heading,
        # not the first half of a wrapped sentence. A genuine wrapped sentence
        # almost always continues in lower case.
        previous_is_heading = (
            len(current) < HEADING_LENGTH
            and not previous_is_finished
            and line[:1].isupper()
        )

        if previous_is_finished or starts_new_item or previous_is_heading:
            paragraphs.append(current)
            current = line
        else:
            current = current + " " + line

    if current:
        paragraphs.append(current)

    return paragraphs


def read_docx(path):
    """Read a Word document, paragraph by paragraph, including tables."""
    from docx import Document

    document = Document(path)
    parts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    return parts


def read_pdf(path):
    """Read a PDF and rebuild its paragraphs."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    lines = []

    for page in reader.pages:
        text = page.extract_text() or ""
        lines.extend(text.split("\n"))
        # A page break is a paragraph break, not a mid-sentence wrap.
        lines.append("")

    return reflow(lines)


def read_text(path):
    """Read a plain text or markdown file and rebuild its paragraphs."""
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()

    return reflow(content.split("\n"))


def read_file(path):
    """Read any supported file and return a list of paragraphs."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            "File not found: " + path + "\n"
            "Check the name in config.py and that the file sits in the same "
            "folder as the script."
        )

    extension = os.path.splitext(path)[1].lower()

    if extension == ".docx":
        parts = read_docx(path)
    elif extension == ".pdf":
        parts = read_pdf(path)
    elif extension in (".txt", ".md"):
        parts = read_text(path)
    else:
        raise ValueError(
            "Unsupported format: " + extension + "\n"
            "Accepted formats are .docx, .pdf, .txt and .md.\n"
            "A .doc file must be saved as .docx first."
        )

    if not parts:
        raise ValueError(
            "No text could be read from " + path + ".\n"
            "If it is a scanned PDF, the pages are images and contain no text "
            "layer. Export it as text, or retype the extract into a .txt file."
        )

    return parts


def number_paragraphs(parts):
    """Prefix every paragraph with its number."""
    lines = []
    for index, text in enumerate(parts, start=1):
        lines.append("[" + str(index) + "] " + text)
    return "\n".join(lines)