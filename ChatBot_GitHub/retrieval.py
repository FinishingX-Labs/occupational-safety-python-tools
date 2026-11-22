# Copyright © 2026 FinishingX media, s.r.o.
# Developed and made available by FinishingX media, s.r.o.
# Website: https://finishingx.de/
# Licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate written license.
# Contact: info@finishingx.de
# License: https://polyformproject.org/licenses/noncommercial/1.0.0



"""Chunking, embedding and similarity search over one document."""

import hashlib
import json
import os

import numpy as np

import config


def build_chunks(paragraphs):
    """Group consecutive paragraphs into chunks large enough to carry meaning.

    A single paragraph is often a heading or one short sentence - too
    little for the search to latch onto. Grouping keeps the paragraph
    numbers, so every quote stays traceable to a place in the document.
    """
    chunks = []
    current, start = [], 1

    for index, text in enumerate(paragraphs, start=1):
        current.append(text)
        length = sum(len(t) for t in current)

        if length >= config.CHUNK_MIN_CHARS or length > config.CHUNK_MAX_CHARS:
            chunks.append({
                "id": "P" + str(start) + "-" + str(index),
                "text": "\n".join(current),
            })
            current, start = [], index + 1

    if current:
        chunks.append({
            "id": "P" + str(start) + "-" + str(len(paragraphs)),
            "text": "\n".join(current),
        })

    return chunks


def fingerprint(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def embed(client, texts):
    """Turn texts into vectors, in one call."""
    response = client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def normalise(vectors):
    matrix = np.array(vectors, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return matrix / norms


def load_or_build_index(client, chunks, document_text):
    """Embed the chunks once, then reuse them.

    Same lesson as the image cache in the first project: never pay twice
    for the same thing.
    """
    key = fingerprint(document_text)
    cache = {}

    if os.path.exists(config.EMBEDDING_CACHE):
        with open(config.EMBEDDING_CACHE, "r", encoding="utf-8") as handle:
            cache = json.load(handle)

    if key in cache:
        return normalise(cache[key])

    print("Indexing the document (" + str(len(chunks)) + " passages)...")
    vectors = embed(client, [chunk["text"] for chunk in chunks])
    cache[key] = vectors

    with open(config.EMBEDDING_CACHE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle)

    return normalise(vectors)


def search(client, question, chunks, index):
    """Return the best passages, each with its similarity score."""
    question_vector = normalise(embed(client, [question]))[0]
    scores = index @ question_vector
    order = np.argsort(-scores)[:config.TOP_K]

    return [
        {"id": chunks[i]["id"], "text": chunks[i]["text"], "score": float(scores[i])}
        for i in order
    ]