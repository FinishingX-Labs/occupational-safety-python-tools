# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0

import os

for path in ["slides.csv", "output/slides.csv"]:
    print("---", path)
    if not os.path.exists(path):
        print("   does not exist")
        continue

    with open(path, "r", encoding="utf-8-sig") as file:
        lines = file.readlines()

    print("   lines:", len(lines))
    if lines:
        print("   header:", repr(lines[0][:120]))