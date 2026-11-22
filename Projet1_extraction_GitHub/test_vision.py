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
import base64

load_dotenv()
client = OpenAI()

VISION_MODEL = "gpt-5.4-mini"

PROMPT = (
    "Extract all text visible in this image, exactly as written. "
    "If the image is a safety pictogram or sign without text, describe it in one short sentence. "
    "If there is nothing relevant, answer NONE."
)

presentation = Presentation("presentation.pptx")
slide = presentation.slides[24]

for shape in slide.shapes:
    if shape.shape_type is not None and "PICTURE" in str(shape.shape_type):
        image = shape.image
        print("Image found:", image.ext, len(image.blob), "bytes")

        encoded_image = base64.b64encode(image.blob).decode("utf-8")

        response = client.responses.create(
            model=VISION_MODEL,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {"type": "input_image",
                     "image_url": f"data:image/{image.ext};base64,{encoded_image}"}
                ]
            }]
        )

        print("Result:", response.output_text)
        print("---")