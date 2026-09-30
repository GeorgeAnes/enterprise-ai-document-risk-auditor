"""Datasets for the retrieval bench.

A Task holds only what a retriever may see: passage texts and query texts.
The gold labels (qrels) come back separately and are read only by the metrics.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import random
import re
import subprocess
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from backend.app.core.chunk import chunk_text
from backend.app.core.ingest import normalize_text

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
FIXTURE = ROOT / "evals" / "fixtures" / "mini.json"
SQUAD = RAW / "squad-explorer" / "dataset" / "dev-v1.1.json"
CUAD = RAW / "cuad-atticus" / "data.zip"  # not data/raw/cuad, where docs/download_datasets.md puts the Zenodo zip
CUAD_QUERY = re.compile(r'related to "(.*?)" that should be reviewed by a lawyer\. Details: (.*)$', re.S)
MIN_CHUNKS = 11  # with 10 chunks or fewer the top 10 is the whole contract, so Hit@10 is 1 for every method


@dataclass(frozen=True)
class Query:
    id: str
    text: str
    corpus: str  # key into Task.corpora: the passages this query searches


@dataclass
class Task:
    name: str
    corpora: dict[str, list[str]]
    queries: list[Query]
    notes: dict = field(default_factory=dict)  # counts and provenance, printed and saved by run.py


Qrels = dict[str, set[int]]  # query id -> indexes of the gold passages inside that query's corpus


def load_fixture(path: Path = FIXTURE, **_) -> tuple[Task, Qrels]:
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    ids = [p["id"] for p in data["passages"]]
    queries = [Query(q["id"], q["text"], "fixture") for q in data["queries"]]
    qrels = {q["id"]: {ids.index(q["gold"])} for q in data["queries"]}
    digest = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()  # same hash with Windows line endings
    return Task("fixture", {"fixture": [p["text"] for p in data["passages"]]}, queries, {"fixture_sha256": digest}), qrels


def load_squad(path: Path = SQUAD, limit: int | None = None, seed: int = 0) -> tuple[Task, Qrels]:
    """SQuAD dev-v1.1: every paragraph is a passage, the gold passage is the one the question was written from."""
    paragraphs = [p for article in _read(path)["data"] for p in article["paragraphs"]]
    items = [(qa["id"], qa["question"], i) for i, p in enumerate(paragraphs) for qa in p["qas"]]
    total = len(items)
    if limit:
        items = random.Random(seed).sample(items, min(limit, total))
    notes = {"queries_in_file": total, "passages": len(paragraphs), "data_commit": _head(path.parents[1])}
    task = Task("squad", {"squad": [p["context"] for p in paragraphs]}, [Query(i, q, "squad") for i, q, _ in items], notes)
    return task, {i: {g} for i, _, g in items}


def load_cuad(path: Path = CUAD, limit: int | None = None, seed: int = 0) -> tuple[Task, Qrels]:
    """CUAD-QA: one corpus per contract, made by the auditor's own ingest and chunker (one sentence per chunk).

    A chunk is gold when it overlaps an annotated answer span. Queries with no span, or whose span
    falls in no chunk (headings are not chunks), are dropped and counted.
    """
    _exists(path)
    with zipfile.ZipFile(path) as z:
        contracts = json.loads(z.read("CUADv1.json"))["data"]
    if limit:
        contracts = random.Random(seed).sample(contracts, min(limit, len(contracts)))
    corpora, queries, qrels, n = {}, [], {}, Counter()
    for c in contracts:
        context = c["paragraphs"][0]["context"]
        chunks = [ch.text for ch in chunk_text(normalize_text(context), source="contract")]
        if len(chunks) < MIN_CHUNKS:
            n["contracts_skipped_too_few_chunks"] += 1
            n["queries_in_skipped_contracts"] += len(c["paragraphs"][0]["qas"])
            continue
        flat, offset = _flat(context), _collapsed_offset(context)
        spans = _chunk_spans(flat, chunks)
        n["chunks_not_located"] += spans.count(None)
        kept = 0
        for qa in c["paragraphs"][0]["qas"]:
            hit = _gold(flat, offset, spans, qa["answers"], n)
            if not qa["answers"]:
                n["queries_dropped_no_answer"] += 1
            elif not hit:
                n["queries_dropped_span_in_no_chunk"] += 1
            else:
                m = CUAD_QUERY.search(qa["question"])
                text = f"{m[1]}. {' '.join(m[2].split())}" if m else qa["question"]
                queries.append(Query(qa["id"], text, c["title"]))
                qrels[qa["id"]] = hit
                kept += 1
        if kept:
            corpora[c["title"]] = chunks
    n["contracts_used"], n["queries_used"] = len(corpora), len(queries)
    n["gold_chunks_per_query"] = round(sum(len(g) for g in qrels.values()) / max(len(qrels), 1), 2)
    n["distinct_query_texts"] = len({q.text for q in queries})  # the 41 category prompts, repeated across contracts
    n["data_commit"] = _head(path.parent)
    return Task("cuad", corpora, queries, dict(n)), qrels


def _flat(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def _chunk_spans(flat: str, chunks: list[str]) -> list[tuple[int, int] | None]:
    """Character span of each chunk in the whitespace-collapsed contract. Chunks come out of the text in order."""
    pos, spans = 0, []
    for ch in chunks:
        i = flat.find(ch, pos)
        spans.append((i, i + len(ch)) if i >= 0 else None)
        pos = i + len(ch) if i >= 0 else pos
    return spans


def _collapsed_offset(context: str):
    """Returns f(i) = len(_flat(context[:i])), the position of raw character i in the collapsed text, without re-collapsing."""
    runs = [m.span() for m in re.finditer(r"\s+", context)]
    starts, removed = [r[0] for r in runs], [0]
    for a, b in runs:
        removed.append(removed[-1] + b - a - 1)  # a run of n whitespace characters collapses to one

    def offset(i: int) -> int:
        j = bisect.bisect_left(starts, i)  # runs 0..j-1 start before i
        if j == 0:
            return i
        a, b = runs[j - 1]
        return i - removed[j - 1] - (min(i, b) - a - 1)

    return offset


def _gold(flat: str, offset, spans, answers, n: Counter) -> set[int]:
    gold = set()
    for a in answers:
        start = offset(a["answer_start"])
        end = start + len(_flat(a["text"]))
        if flat[start:end] != _flat(a["text"]):
            n["answer_spans_misaligned"] += 1  # skipped, not guessed
            continue
        gold |= {i for i, s in enumerate(spans) if s and s[0] < end and s[1] > start}
    return gold


def _exists(path: Path) -> None:
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found. Run: python -m evals.retrieval.fetch_data")


def _read(path: Path) -> dict:
    _exists(path)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _head(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
