# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0


"""Document chatbot: retrieve, answer with separate claims, check, verify.

Every question produces a record: what was retrieved, what was claimed,
what was discarded and why. That record is what the benchmark measures.
"""

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

import config
import prompts
import retrieval
from readers import read_file

load_dotenv(override=True)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def call_model(model, prompt):
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned.strip())
    return json.loads(cleaned)


def quote_is_real(quote, passage_text):
    """Check the quote exists in the passage, word for word.

    No model call. This is the only part of the tool that cannot be
    fooled, and it costs nothing.
    """
    if not quote:
        return False
    needle = re.sub(r"\s+", " ", quote).strip().lower()
    haystack = re.sub(r"\s+", " ", passage_text).strip().lower()
    return needle in haystack


def generate(question, passages, language):
    """Ask the generator for separate, sourced claims."""
    prompt = prompts.localise(prompts.PROMPT_GENERATE, language)

    prompt += "\n\nPASSAGES\n--------\n"
    for passage in passages:
        prompt += "[" + passage["id"] + "] " + passage["text"] + "\n\n"

    prompt += "QUESTION\n--------\n" + question + "\n"

    return parse_json(call_model(config.GENERATOR_MODEL, prompt))


def verify(claim, passage_text, language):
    """Second model, closed question, no context beyond passage and claim."""
    prompt = prompts.localise(prompts.PROMPT_VERIFY, language)
    prompt += "\n\nPASSAGE\n-------\n" + passage_text
    prompt += "\n\nCLAIM\n-----\n" + claim + "\n"

    result = parse_json(call_model(config.VERIFIER_MODEL, prompt))
    verdict = str(result.get("verdict", "")).strip().upper()

    if verdict not in config.VERDICTS:
        verdict = config.NOT_SUPPORTED

    return verdict, str(result.get("reason", "")).strip()


def empty_record(question, top_score, reason):
    return {
        "question": question,
        "top_score": top_score,
        "abstained": True,
        "abstention_reason": reason,
        "claims_generated": 0,
        "dropped_quote": 0,
        "dropped_verifier": 0,
        "claims_kept": 0,
        "faithfulness": None,
        "claims": [],
        "missing": "",
        "passages": [],
    }


def answer_question(question, chunks, index, language):
    """Run the full pipeline and return everything that happened."""
    passages = retrieval.search(client, question, chunks, index)
    top_score = passages[0]["score"] if passages else 0.0

    # Abstain before spending anything on generation.
    if top_score < config.MIN_SIMILARITY:
        return empty_record(question, top_score, "similarity below threshold")

    try:
        result = generate(question, passages, language)
    except Exception as error:
        record = empty_record(question, top_score, "generation failed")
        record["error"] = str(error)
        return record

    claims = result.get("claims", [])
    by_id = {p["id"]: p["text"] for p in passages}

    kept, dropped_quote, dropped_verifier = [], 0, 0

    for claim in claims:
        passage_text = by_id.get(claim.get("passage_id", ""), "")

        if not quote_is_real(claim.get("quote", ""), passage_text):
            dropped_quote += 1
            continue

        verdict, reason = verify(claim.get("text", ""), passage_text, language)

        if verdict == config.NOT_SUPPORTED:
            dropped_verifier += 1
            continue

        claim["verdict"] = verdict
        claim["reason"] = reason
        kept.append(claim)

    generated = len(claims)

    return {
        "question": question,
        "top_score": top_score,
        "abstained": len(kept) == 0,
        "abstention_reason": "no supported claim" if not kept else "",
        "claims_generated": generated,
        "dropped_quote": dropped_quote,
        "dropped_verifier": dropped_verifier,
        "claims_kept": len(kept),
        # Faithfulness as defined by Ragas: supported statements over
        # total statements produced.
        "faithfulness": (len(kept) / generated) if generated else None,
        "claims": kept,
        "missing": str(result.get("missing", "")).strip(),
        "passages": [{"id": p["id"], "score": p["score"]} for p in passages],
    }


def print_record(record):
    print()

    if record["abstained"]:
        if record["abstention_reason"] == "similarity below threshold":
            print("Ce document ne traite pas de ce sujet.")
        else:
            print("Aucune affirmation vérifiable n'a pu être établie.")
        print("(similarité maximale " + str(round(record["top_score"], 3)) + ")")
    else:
        for claim in record["claims"]:
            mark = "  " if claim["verdict"] == config.SUPPORTED else "~ "
            print(mark + claim["text"])
            print("     source : " + claim["passage_id"])
            if claim["verdict"] == config.PARTIALLY:
                print("     nuance : " + claim["reason"])

    if record["missing"]:
        print("\n  Non traité par le document : " + record["missing"])

    discarded = record["dropped_quote"] + record["dropped_verifier"]
    if discarded:
        print("\n[" + str(discarded) + " affirmation(s) écartée(s) : "
              + str(record["dropped_quote"]) + " citation introuvable, "
              + str(record["dropped_verifier"]) + " non soutenue]")
    print()


def load_document():
    """Read, chunk and index the document. Shared with the benchmark."""
    paragraphs = read_file(config.DOCUMENT_FILE)
    document_text = "\n".join(paragraphs)
    chunks = retrieval.build_chunks(paragraphs)
    index = retrieval.load_or_build_index(client, chunks, document_text)
    return paragraphs, chunks, index


def main():
    paragraphs, chunks, index = load_document()

    print("\nDocument : " + config.DOCUMENT_FILE)
    print(str(len(paragraphs)) + " paragraphes, " + str(len(chunks)) + " passages")
    print("Générateur : " + config.GENERATOR_MODEL)
    print("Vérificateur : " + config.VERIFIER_MODEL)
    print("\nPosez vos questions. Entrée vide pour quitter.\n")

    while True:
        question = input("> ").strip()
        if not question:
            break
        print_record(answer_question(question, chunks, index, config.DEFAULT_LANGUAGE))


if __name__ == "__main__":
    main()