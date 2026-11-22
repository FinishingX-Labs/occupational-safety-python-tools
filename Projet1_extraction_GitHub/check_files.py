# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

import os

FOLDER = "reference_documents"

if os.path.isdir(FOLDER):
    print("Files in", FOLDER, ":")
    for name in os.listdir(FOLDER):
        print(" -", name)
else:
    print("Folder", FOLDER, "not found.")
    print("Current folder contains:")
    for name in os.listdir():
        print(" -", name)