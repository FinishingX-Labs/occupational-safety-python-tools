# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from pptx import Presentation
from openai import OpenAI
from dotenv import load_dotenv
from config import (
    PPTX_FILE, CSV_FILE, CSV_DELIMITER, VISION_MODEL,
    EXTRACTION_SLIDE_LIMIT, COLUMNS,
    SLIDE_NUMBER_COLUMN, SLIDE_CONTENT_COLUMN, SPEAKER_NOTES_COLUMN,
    IMAGE_TEXT_COLUMN, LEGAL_COLUMN, INTERNAL_COLUMN, RISK_COLUMN,
    TRANSLATION_COLUMN,
)
import csv
import base64
import hashlib

load_dotenv(override=True)
client = OpenAI()

PROMPT = (
    "Extract all text visible in this image, exactly as written. "
    "Ignore logos, letterheads, watermarks, brand names and organisation names that are "
    "part of the document design rather than its content. "
    "Ignore incidental text visible inside photographs, such as shop signs or street names. "
    "If the image is a safety pictogram or sign without text, describe it in one short sentence. "
    "If there is nothing relevant, answer NONE."
)

image_cache = {}


def read_image_text(image_bytes, extension):
    fingerprint = hashlib.md5(image_bytes).hexdigest()
    if fingerprint in image_cache:
        return image_cache[fingerprint]

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    response = client.responses.create(
        model=VISION_MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {"type": "input_image",
                 "image_url": f"data:image/{extension};base64,{encoded_image}"}
            ]
        }]
    )

    result = response.output_text.strip()
    if result.upper() == "NONE":
        result = ""

    image_cache[fingerprint] = result
    return result


def run_extraction():
    try:
        open(CSV_FILE, "a").close()
    except PermissionError:
        print("Please close", CSV_FILE, "in Excel before running this script.")
        return False

    presentation = Presentation(PPTX_FILE)
    rows = []

    for number, slide in enumerate(presentation.slides, start=1):
        if EXTRACTION_SLIDE_LIMIT is not None and number > EXTRACTION_SLIDE_LIMIT:
            break

        texts = []
        image_texts = []

        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    texts.append(text)

            if shape.shape_type is not None and "PICTURE" in str(shape.shape_type):
                image = shape.image
                found = read_image_text(image.blob, image.ext)
                if found:
                    image_texts.append(found)

        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        rows.append({
            SLIDE_NUMBER_COLUMN: number,
            SLIDE_CONTENT_COLUMN: "\n".join(texts),
            SPEAKER_NOTES_COLUMN: notes,
            IMAGE_TEXT_COLUMN: "\n".join(image_texts),
            LEGAL_COLUMN: "",
            INTERNAL_COLUMN: "",
            RISK_COLUMN: "",
            TRANSLATION_COLUMN: "",
        })

        print("Slide", number, "extracted")

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS, delimiter=CSV_DELIMITER)
        writer.writeheader()
        writer.writerows(rows)

    print("Extraction done:", len(rows), "slides,", len(image_cache), "unique images analysed")
    return True


if __name__ == "__main__":
    run_extraction()