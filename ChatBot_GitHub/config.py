# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0



"""Configuration for the document chatbot."""

DOCUMENT_FILE = "document.docx"

# --- Models -----------------------------------------------------------
# Kept as constants so a second generator (GPT-6 Astra) can be measured
# against the first without touching a line of code.
GENERATOR_MODEL = "gpt-5.5"

# The verifier should ideally come from a different provider than the
# generator. With a single provider available, a different model is a
# compromise - and it must be documented as such.
VERIFIER_MODEL = "gpt-5.4-mini"

EMBEDDING_MODEL = "text-embedding-3-small"

# --- Retrieval --------------------------------------------------------
CHUNK_MIN_CHARS = 400
CHUNK_MAX_CHARS = 1200
TOP_K = 4

# Below this similarity, the tool abstains before calling the generator.
# Calibrate it on the benchmark: too high and it refuses everything.
MIN_SIMILARITY = 0.30

EMBEDDING_CACHE = "embeddings_cache.json"

# --- Output -----------------------------------------------------------
DEFAULT_LANGUAGE = "French"

SUPPORTED = "SUPPORTED"
PARTIALLY = "PARTIALLY"
NOT_SUPPORTED = "NOT_SUPPORTED"
VERDICTS = [SUPPORTED, PARTIALLY, NOT_SUPPORTED]
# --- Benchmark --------------------------------------------------------
BENCHMARK_FILE = "benchmark.txt"
BENCHMARK_CSV = "benchmark_results.csv"
BENCHMARK_TRACE = "benchmark_trace.json"

# These models are not deterministic. One run tells you nothing about
# the next one, so the benchmark is run several times.
RUNS = 3

CSV_DELIMITER = ";"

# Question families. The first two expect an answer, the last two expect
# the tool to hold back.
ANSWERABLE = ["ANSWERABLE_SINGLE", "ANSWERABLE_MULTI"]
UNANSWERABLE = ["NOT_ANSWERABLE", "FALSE_PREMISE"]