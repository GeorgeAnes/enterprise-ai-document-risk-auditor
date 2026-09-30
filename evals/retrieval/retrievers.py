"""The rows of the bench. Every function takes plain strings and returns score matrices (queries x passages).

No function here receives a label. All lexical rows use the auditor's own tokenizer on the same text.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import urllib.request
from pathlib import Path

import numpy as np

from backend.app.core.retrieval import _tokens

K1, B, RRF_K, LSA_DIMS, BLOCK = 1.2, 0.75, 60, 64, 256
CACHE = Path(__file__).resolve().parents[2] / "data" / "eval" / "embed_cache.sqlite"

# key -> label shown in tables. Order is the order of the rows.
LABELS = {
    "random": "Random",
    "tfidf": "TF-IDF as shipped (raw tf)",
    "tfidf_sub": "TF-IDF, sublinear tf (1 + ln tf)",
    "bm25": "BM25 (k1=1.2, b=0.75)",
    "bm25_b0": "BM25, b=0",
    "lsa": "LSA-64",
    "dense": "Dense, static vectors",
    "rrf_bm25_dense": "RRF(BM25, dense)",
    "rrf_bm25_lsa": "RRF(BM25, LSA)",
}


def _unit(m):
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)


def _tf(counts, sublinear: bool):
    return np.where(counts > 0, 1 + np.log(np.maximum(counts, 1)), 0) if sublinear else counts


class Corpus:
    """Term statistics for one corpus and the queries that search it.

    # ponytail: dense term-document matrix, fine for one contract or 2,000 paragraphs;
    # use scipy.sparse if the corpus grows to hundreds of thousands of passages.
    """

    def __init__(self, texts: list[str], queries: list[str]):
        self.n = len(texts)
        docs = [_tokens(t) for t in texts]
        self.qtoks = [_tokens(q) for q in queries]
        terms = sorted({t for d in docs for t in d})
        self.v = len(terms)
        self.vocab = {t: i for i, t in enumerate(terms)}
        for q in self.qtoks:  # query-only terms get columns after the corpus terms
            for t in q:
                self.vocab.setdefault(t, len(self.vocab))
        self.C = self._count(docs, self.v)
        self.df = (self.C > 0).sum(0)
        # The auditor's idf. A query term the corpus never saw gets 1.0, as in _tfidf_vector.
        self.idf = np.ones(len(self.vocab), np.float32)
        self.idf[: self.v] = np.log((self.n + 1) / (self.df + 1)) + 1

    def _count(self, token_lists, width):
        m = np.zeros((len(token_lists), width), np.float32)
        for i, toks in enumerate(token_lists):
            for t in toks:
                m[i, self.vocab[t]] += 1
        return m

    def _blocks(self):
        for lo in range(0, len(self.qtoks), BLOCK):
            yield self._count(self.qtoks[lo : lo + BLOCK], len(self.vocab))

    def _dot(self, q, w):
        """q (queries x all terms) times w.T (passages x corpus terms), touching only the terms these queries use."""
        cols = np.flatnonzero(q[:, : self.v].any(0))
        return q[:, cols] @ w[:, cols].T

    def tfidf(self, sublinear: bool = False):
        """Cosine of tf-idf vectors. With sublinear=False this is the auditor's retrieval (see the parity test)."""
        docs = _unit(_tf(self.C, sublinear) * self.idf[: self.v])
        out = []
        for qc in self._blocks():
            q = _tf(qc, sublinear) * self.idf  # the norm includes query-only terms, as in the auditor
            norm = np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-12)
            out.append(self._dot(q, docs) / norm)
        return np.vstack(out)

    def bm25(self, b: float = B):
        """Robertson BM25 with the Lucene-style idf. Each distinct query term counts once."""
        dl = self.C.sum(1, keepdims=True)
        tf = self.C * (K1 + 1) / (self.C + K1 * (1 - b + b * dl / max(float(dl.mean()), 1e-9)))
        idf = np.log((self.n - self.df + 0.5) / (self.df + 0.5) + 1)
        w = tf * idf
        return np.vstack([self._dot((qc > 0).astype(np.float32), w) for qc in self._blocks()])

    def lsa(self, dims: int = LSA_DIMS):
        """Truncated SVD of the tf-idf matrix. Returns cosine scores and the (query, passage) vectors in the latent space."""
        x = _unit(self.C * self.idf[: self.v])
        _, s, vt = np.linalg.svd(x, full_matrices=False)
        k = max(1, min(dims, len(s) - 1))
        v = vt[:k]  # k latent dimensions x corpus terms
        passages = x @ v.T
        queries = np.vstack([self._dot(qc * self.idf, v) for qc in self._blocks()])
        return _unit(queries) @ _unit(passages).T, (queries, passages)


def dense(embed, texts: list[str], queries: list[str]):
    return _unit(np.asarray(embed(queries))) @ _unit(np.asarray(embed(texts))).T


def tiebreak(n: int, seed: int = 0):
    return np.random.default_rng(seed).permutation(n)


def order(scores, perm, block: int = BLOCK):
    """Passage indexes best-first. Equal scores fall in the order of `perm`, a fixed shuffle, so position never wins a tie."""
    parts = [perm[np.argsort(-scores[i : i + block][:, perm], axis=1, kind="stable")] for i in range(0, len(scores), block)]
    return np.vstack(parts).astype(np.int32)


def rrf(legs, perm, k: int = RRF_K):
    """Reciprocal rank fusion: sum over legs of 1 / (k + rank), rank starting at 1.

    legs is a list of (scores, lexical). A lexical leg gives nothing to a passage it scored 0 (no term matched).
    """
    total = 0
    for scores, lexical in legs:
        o = order(scores, perm)
        rank = np.empty_like(o)
        np.put_along_axis(rank, o, np.arange(1, o.shape[1] + 1, dtype=o.dtype)[None, :], axis=1)
        total = total + np.where((scores > 0) | (not lexical), 1 / (k + rank.astype(np.float32)), 0)
    return np.asarray(total, np.float32)


def score_all(texts: list[str], queries: list[str], embed=None, seed: int = 0):
    """Every row for one corpus. Returns ({row: scores}, lsa_vectors)."""
    c, perm = Corpus(texts, queries), tiebreak(len(texts), seed)
    s = {"random": np.random.default_rng(seed).random((len(queries), len(texts)), dtype=np.float32)}
    s["tfidf"], s["tfidf_sub"] = c.tfidf(), c.tfidf(sublinear=True)
    s["bm25"], s["bm25_b0"] = c.bm25(), c.bm25(b=0.0)
    s["lsa"], vectors = c.lsa()
    if embed is not None:
        s["dense"] = dense(embed, texts, queries)
        s["rrf_bm25_dense"] = rrf([(s["bm25"], True), (s["dense"], False)], perm)
    s["rrf_bm25_lsa"] = rrf([(s["bm25"], True), (s["lsa"], False)], perm)
    return {k: s[k] for k in LABELS if k in s}, vectors


def get_embedder(kind: str):
    if kind == "wordllama":
        from wordllama import WordLlama  # static 256-d vectors that ship inside the PyPI wheel

        return WordLlama.load().embed
    if kind == "openai":
        return _openai_embed
    raise ValueError(f"unknown dense kind: {kind}")


def _openai_embed(texts: list[str], batch: int = 64):
    """Any OpenAI-compatible /embeddings endpoint: EMBED_BASE_URL, EMBED_MODEL, optional EMBED_KEY. Vectors are cached in sqlite.

    # ponytail: one request per batch, no retry or rate limiting; add them if a hosted endpoint throttles.
    """
    base, model, key = os.environ["EMBED_BASE_URL"].rstrip("/"), os.environ["EMBED_MODEL"], os.environ.get("EMBED_KEY", "")
    if not base.startswith(("http://", "https://")):
        raise ValueError("EMBED_BASE_URL must start with http:// or https://")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(CACHE)
    db.execute("create table if not exists vec (k text primary key, e blob)")
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})}
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        keys = [hashlib.sha256(f"{model}\0{t}".encode()).hexdigest() for t in chunk]
        got = {}
        for k in keys:
            row = db.execute("select e from vec where k = ?", (k,)).fetchone()
            if row:
                got[k] = row[0]
        missing = [(k, t) for k, t in zip(keys, chunk) if k not in got]
        if missing:
            body = json.dumps({"model": model, "input": [t for _, t in missing]}).encode()
            with urllib.request.urlopen(urllib.request.Request(base + "/embeddings", body, headers), timeout=120) as r:
                data = sorted(json.load(r)["data"], key=lambda d: d["index"])
            for (k, _), d in zip(missing, data):
                got[k] = np.asarray(d["embedding"], np.float32).tobytes()
                db.execute("insert or replace into vec values (?, ?)", (k, got[k]))
            db.commit()
        out += [np.frombuffer(got[k], np.float32) for k in keys]
    db.close()
    return np.stack(out)
