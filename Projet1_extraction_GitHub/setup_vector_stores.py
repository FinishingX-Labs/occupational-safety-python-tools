# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

from openai import OpenAI
from dotenv import load_dotenv
from config import LEGAL_FOLDER, INTERNAL_FOLDER, RISK_FOLDER
import os

load_dotenv(override=True)
client = OpenAI()

ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"]


def collect_files(folder):
    paths = []
    for name in sorted(os.listdir(folder)):
        extension = os.path.splitext(name)[1].lower()
        if extension in ALLOWED_EXTENSIONS:
            paths.append(os.path.join(folder, name))
    return paths


def create_store(name, file_paths):
    if not file_paths:
        print("No file found for", name)
        return None

    store = client.vector_stores.create(name=name)

    for path in file_paths:
        with open(path, "rb") as file:
            client.vector_stores.files.upload_and_poll(
                vector_store_id=store.id,
                file=file
            )
        print("Uploaded:", path)

    print(name, "->", store.id)
    print()
    return store.id


create_store("Legal regulations", collect_files(LEGAL_FOLDER))
create_store("Internal documents", collect_files(INTERNAL_FOLDER))
create_store("Risk assessment", collect_files(RISK_FOLDER))