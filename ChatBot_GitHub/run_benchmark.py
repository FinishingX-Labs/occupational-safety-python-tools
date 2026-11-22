# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0



"""Run the benchmark and produce the numbers for the results chapter.

Reads benchmark.txt, runs every question several times, writes a CSV for
the report and a full JSON trace for auditing, then prints a summary.
"""

import csv
import json
import statistics

import config
from chatbot import answer_question, load_document


def load_benchmark(path):
    """Read questions grouped by family.

    Format: a line starting with # opens a family, every other non-empty
    line is a question.
    """
    questions = []
    family = "UNSPECIFIED"

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                family = line.lstrip("#").strip().upper()
                continue
            questions.append({"family": family, "question": line})

    if not questions:
        raise ValueError("No question found in " + path)

    return questions


def write_csv(rows):
    columns = [
        "run", "family", "question", "top_score", "abstained",
        "claims_generated", "dropped_quote", "dropped_verifier",
        "claims_kept", "faithfulness",
    ]

    with open(config.BENCHMARK_CSV, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, delimiter=config.CSV_DELIMITER,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarise(rows):
    """Per family: abstention rate, faithfulness, retrieval score."""
    families = sorted({row["family"] for row in rows})
    print("\n" + "=" * 72)
    print("RÉSULTATS")
    print("=" * 72)

    for family in families:
        subset = [r for r in rows if r["family"] == family]
        abstained = [r for r in subset if r["abstained"]]
        faith = [r["faithfulness"] for r in subset if r["faithfulness"] is not None]
        scores = [r["top_score"] for r in subset]

        print("\n" + family + "  (" + str(len(subset)) + " exécutions)")
        print("  abstention        : "
              + str(round(100 * len(abstained) / len(subset), 1)) + " %")

        if family in config.UNANSWERABLE:
            print("  -> abstention correcte, à maximiser")
        elif family in config.ANSWERABLE:
            print("  -> abstention excessive, à minimiser")

        if faith:
            line = "  faithfulness      : " + str(round(statistics.mean(faith), 3))
            if len(faith) > 1:
                line += "  (écart-type " + str(round(statistics.stdev(faith), 3)) + ")"
            print(line)

        print("  similarité max    : " + str(round(statistics.mean(scores), 3)))
        print("  citations écartées: " + str(sum(r["dropped_quote"] for r in subset)))
        print("  non soutenues     : " + str(sum(r["dropped_verifier"] for r in subset)))

    total_generated = sum(r["claims_generated"] for r in rows)
    total_kept = sum(r["claims_kept"] for r in rows)

    print("\n" + "-" * 72)
    print("Ensemble : " + str(total_kept) + " affirmations retenues sur "
          + str(total_generated) + " produites")
    if total_generated:
        print("Faithfulness globale : " + str(round(total_kept / total_generated, 3)))
    print("-" * 72 + "\n")


def main():
    questions = load_benchmark(config.BENCHMARK_FILE)
    paragraphs, chunks, index = load_document()

    print("\nDocument : " + config.DOCUMENT_FILE
          + "  (" + str(len(chunks)) + " passages)")
    print("Générateur : " + config.GENERATOR_MODEL)
    print("Vérificateur : " + config.VERIFIER_MODEL)
    print(str(len(questions)) + " questions x " + str(config.RUNS) + " exécutions\n")

    rows, trace = [], []

    for run in range(1, config.RUNS + 1):
        print("--- exécution " + str(run) + " ---")

        for number, item in enumerate(questions, start=1):
            print("[" + str(number) + "/" + str(len(questions)) + "] "
                  + item["question"][:60] + " ... ", end="", flush=True)

            record = answer_question(
                item["question"], chunks, index, config.DEFAULT_LANGUAGE
            )
            record["run"] = run
            record["family"] = item["family"]

            rows.append(record)
            trace.append(record)

            print("abstention" if record["abstained"]
                  else str(record["claims_kept"]) + " affirmation(s)")

        print()

    write_csv(rows)

    with open(config.BENCHMARK_TRACE, "w", encoding="utf-8") as handle:
        json.dump(trace, handle, ensure_ascii=False, indent=2)

    summarise(rows)

    print("Détail par question : " + config.BENCHMARK_CSV)
    print("Trace complète      : " + config.BENCHMARK_TRACE + "\n")


if __name__ == "__main__":
    main()