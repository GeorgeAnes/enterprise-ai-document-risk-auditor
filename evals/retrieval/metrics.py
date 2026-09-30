"""Ranking metrics, a cluster bootstrap, and the query/gold overlap measure. Gold labels are used here and nowhere else."""
from __future__ import annotations

import math
import random
from collections import defaultdict

import numpy as np

from backend.app.core.retrieval import _tokens

K = 10


def ndcg(ranked, gold, k: int = K) -> float:
    """Binary-gain nDCG@k: DCG of the ranking divided by DCG of a ranking that puts every gold passage first."""
    dcg = sum(1 / math.log2(r + 2) for r, d in enumerate(ranked[:k]) if d in gold)
    ideal = sum(1 / math.log2(r + 2) for r in range(min(len(gold), k)))
    return dcg / ideal if ideal else 0.0


def mrr(ranked, gold, k: int = K) -> float:
    return next((1 / (r + 1) for r, d in enumerate(ranked[:k]) if d in gold), 0.0)


def hit(ranked, gold, k: int = K) -> float:
    return float(any(d in gold for d in ranked[:k]))


def first_rank(ranked, gold) -> int:
    """1-based position of the best-placed gold passage in the full ranking."""
    return int(np.flatnonzero(np.isin(ranked, list(gold)))[0]) + 1


def evaluate(order, golds) -> np.ndarray:
    """One row per query: nDCG@10, MRR@10, Hit@10, rank of the first gold passage."""
    return np.array([[ndcg(o, g), mrr(o, g), hit(o, g), first_rank(o, g)] for o, g in zip(order, golds)])


def bootstrap_means(values, clusters, resamples: int = 1000, seed: int = 0) -> np.ndarray:
    """Means of `values` over resamples that draw whole clusters (a paragraph, a contract), not single queries."""
    _, inverse = np.unique(np.asarray(clusters), return_inverse=True)
    sums, counts = np.bincount(inverse, weights=values), np.bincount(inverse)
    draw = np.random.default_rng(seed).integers(0, len(sums), (resamples, len(sums)))
    return sums[draw].sum(1) / counts[draw].sum(1)


def interval(values, clusters, **kw) -> tuple[float, float]:
    lo, hi = np.percentile(bootstrap_means(values, clusters, **kw), [2.5, 97.5])
    return float(lo), float(hi)


def shared_tokens(query: str, texts) -> set[str]:
    """Content words (the auditor's tokens) that a query shares with the gold passages."""
    return set(_tokens(query)) & {t for x in texts for t in _tokens(x)}


def overlap(query: str, texts) -> float:
    """Fraction of the query's distinct content words that appear in the gold passages."""
    words = set(_tokens(query))
    return len(shared_tokens(query, texts)) / len(words) if words else 0.0


def terciles(values) -> np.ndarray:
    """0, 1 or 2 per value. Ties at a boundary stay in the lower group, so the lowest group can hold more than a third."""
    lo, hi = np.quantile(values, [1 / 3, 2 / 3])
    return np.where(values <= lo, 0, np.where(values <= hi, 1, 2))


def shuffle_qrels(qrels, corpus_of, seed: int = 0):
    """Give each query another query's gold set from the same corpus. Used to show the metrics collapse."""
    rng, groups, out = random.Random(seed), defaultdict(list), {}
    for q in qrels:
        groups[corpus_of[q]].append(q)
    for ids in groups.values():
        golds = [qrels[q] for q in ids]
        rng.shuffle(golds)
        out.update(zip(ids, golds))
    return out
