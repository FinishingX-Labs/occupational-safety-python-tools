# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv(override=True)
client = OpenAI()

REFERENCE_FOLDER = "reference_documents"
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"]


def collect_files(folder):
    paths = []
    for name in sorted(os.listdir(folder)):
        extension = os.path.splitext(name)[1].lower()
        if extension in ALLOWED_EXTENSIONS:
            paths.append(os.path.join(folder, name))
    return paths


if not os.path.isdir(REFERENCE_FOLDER):
    print("Folder not found:", REFERENCE_FOLDER)
    print("Create it and place the applicable standard inside.")
    exit()

files = collect_files(REFERENCE_FOLDER)

if not files:
    print("No usable document found in", REFERENCE_FOLDER)
    print("Accepted formats:", ", ".join(ALLOWED_EXTENSIONS))
    exit()

store = client.vector_stores.create(name="Audit reference corpus")

for path in files:
    with open(path, "rb") as file:
        client.vector_stores.files.upload_and_poll(vector_store_id=store.id, file=file)
    print("Uploaded:", path)

print()
print("Reference store created:", store.id)
print("Add this line to your .env file:")
print("REFERENCE_STORE_ID=" + store.id)