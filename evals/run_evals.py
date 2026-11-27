"""Evaluate DocuMind's retrieval and answers against a small labelled dataset.

Usage (Postgres must be running and ANTHROPIC_API_KEY set):
    python -m evals.run_evals            # retrieval + answer checks
    python -m evals.run_evals --no-llm   # retrieval only (free, fast)

Metrics
- hit@k:    the expected source document appears in the top-k retrieved chunks
- keyword:  the generated answer contains at least one expected keyword
- abstain:  for unanswerable questions, nothing relevant is retrieved or the answer declines
"""

import argparse
import json
from pathlib import Path

from app import rag, store
from app.config import settings
from app.db import init_db, pool
from app.embeddings import embed_query, embed_texts
from app.ingest.chunking import chunk_pages
from app.ingest.loaders import load_pages

ROOT = Path(__file__).parent


def ingest_corpus() -> None:
    existing = {d["filename"] for d in store.list_documents()}
    for path in sorted((ROOT / "corpus").glob("*")):
        if path.name in existing:
            continue
        pages = load_pages(path.name, path.read_bytes())
        chunks = chunk_pages(pages, settings.chunk_max_chars, settings.chunk_overlap)
        store.add_document(path.name, chunks, embed_texts([c.text for c in chunks]))
        print(f"ingested {path.name} ({len(chunks)} chunks)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="skip answer generation")
    args = parser.parse_args()

    init_db()
    pool.open()
    ingest_corpus()

    rows = [json.loads(line) for line in (ROOT / "dataset.jsonl").read_text().splitlines() if line]
    hits = answerable = keyword_ok = abstain_ok = unanswerable = 0

    for row in rows:
        retrieved = rag.filter_relevant(store.search(embed_query(row["question"]), settings.top_k))
        expected_source = row["expected_source"]

        if expected_source is None:
            unanswerable += 1
            ok = not retrieved
            if not ok and not args.no_llm:
                text = rag.answer(row["question"], retrieved).lower()
                ok = any(k in text for k in row["expected_keywords"])
            abstain_ok += ok
            print(f"{'PASS' if ok else 'FAIL'}  [abstain] {row['question']}")
            continue

        answerable += 1
        hit = any(c.filename == expected_source for c in retrieved)
        hits += hit
        line = f"{'PASS' if hit else 'FAIL'}  [retrieval] {row['question']}"

        if not args.no_llm:
            text = rag.answer(row["question"], retrieved).lower()
            kw = any(k.lower() in text for k in row["expected_keywords"])
            keyword_ok += kw
            line += f"  | answer {'PASS' if kw else 'FAIL'}"
        print(line)

    print("\n--- results ---")
    print(f"hit@{settings.top_k}:        {hits}/{answerable}")
    if not args.no_llm:
        print(f"keyword match:  {keyword_ok}/{answerable}")
    print(f"abstain:        {abstain_ok}/{unanswerable}")
    pool.close()


if __name__ == "__main__":
    main()
