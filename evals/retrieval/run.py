"""Run the retrieval bench.

    python -m evals.retrieval.run --dataset fixture
    python -m evals.retrieval.run --dataset squad
    python -m evals.retrieval.run --dataset cuad
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import sys
import time
from datetime import date
from importlib import metadata
from pathlib import Path

import numpy as np

from backend.app.core.retrieval import _build_idf, _cosine, _tfidf_vector

from . import datasets as D
from . import metrics as M
from . import report
from . import retrievers as R

RESULTS = D.ROOT / "docs" / "retrieval-results.json"
HTML = D.ROOT / "docs" / "retrieval-bench.html"
LOADERS = {"fixture": D.load_fixture, "squad": D.load_squad, "cuad": D.load_cuad}
DENSE_NOTE = {"wordllama": "static 256-d vectors, no transformer model"}
INSPECT_SQUAD, PARITY_QUERIES, SHUFFLES, SNIPPET = 30, 200, 10, 160
PAIRS = [("bm25", "tfidf_sub"), ("rrf_bm25_dense", "bm25"), ("rrf_bm25_lsa", "bm25")]  # a minus b, beyond the comparison with shipped TF-IDF


def run_dataset(name: str, limit: int | None = None, dense: str = "wordllama", seed: int = 0) -> dict:
    task, qrels = LOADERS[name](limit=limit, seed=seed)
    embed = None if dense == "none" else R.get_embedder(dense)
    queries, ids = task.queries, [q.id for q in task.queries]
    golds = [qrels[i] for i in ids]
    rows = [k for k in R.LABELS if embed is not None or "dense" not in k]
    rec = {k: np.zeros((len(queries), 4)) for k in rows}
    top = {k: np.zeros((len(queries), M.K), np.int32) for k in rows}
    by_corpus: dict[str, list[int]] = {}
    for i, q in enumerate(queries):
        by_corpus.setdefault(q.corpus, []).append(i)
    if name == "fixture":
        picked = set(ids)
    elif name == "squad":
        picked = set(random.Random(seed).sample(ids, min(INSPECT_SQUAD, len(ids))))
    else:
        picked = set()
    inspector, dims = {}, []

    for cid, idx in by_corpus.items():
        texts = task.corpora[cid]
        scores, (qv, pv) = R.score_all(texts, [queries[i].text for i in idx], embed, seed)
        perm = R.tiebreak(len(texts), seed)
        dims.append(qv.shape[1])
        for k in rows:
            o = R.order(scores[k], perm)
            rec[k][idx] = M.evaluate(o, [golds[i] for i in idx])
            top[k][idx] = o[:, : M.K]
            for local, i in enumerate(idx):
                if ids[i] in picked:
                    entry = inspector.setdefault(ids[i], _entry(queries[i].text, texts, golds[i], qv[local], pv))
                    entry["methods"][k] = {
                        "rank": int(rec[k][i, 3]),
                        "top": [{"text": _cut(texts[j], SNIPPET), "gold": int(j) in golds[i]} for j in o[local, :3]],
                    }

    corpus_of = {q.id: q.corpus for q in queries}
    cluster = None
    if name == "squad":
        cluster = [min(g) for g in golds]  # queries about the same paragraph move together
    elif name == "cuad":
        cluster = [q.corpus for q in queries]  # queries about the same contract move together
    rows_out, overlap_out, paired_out = _rows(task, golds, rec, rows, cluster, seed)
    result = {
        "dataset": name,
        "meta": _meta(task, limit, dense, seed, dims, len(by_corpus)),
        "rows": rows_out,
        "overlap": overlap_out,
        "paired": paired_out,
        "worst": {k: _worst(queries, rec[k]) for k in rows},
        "leak_checks": _leak_checks(task, qrels, golds, corpus_of, by_corpus, top, rows, seed),
        "inspector": [inspector[i] for i in ids if i in inspector],
    }
    return result


def _cut(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _entry(query, texts, gold, q_vec, p_vecs) -> dict:
    g = min(gold)
    dot = float(q_vec @ p_vecs[g])
    qn, gn = float(np.linalg.norm(q_vec)), float(np.linalg.norm(p_vecs[g]))
    return {
        "query": query,
        "gold_text": _cut(texts[g], 400),
        "methods": {},
        "maths": {
            "dims": len(q_vec),
            "query_first8": [round(float(x), 4) for x in q_vec[:8]],
            "gold_first8": [round(float(x), 4) for x in p_vecs[g][:8]],
            "query_norm": round(qn, 4),
            "gold_norm": round(gn, 4),
            "dot": round(dot, 4),
            "cosine": round(dot / max(qn * gn, 1e-12), 4),
        },
    }


def _meta(task, limit, dense, seed, dims, n_corpora) -> dict:
    def version(pkg):
        try:
            return metadata.version(pkg)
        except metadata.PackageNotFoundError:
            return None

    return {
        "date": date.today().isoformat(),
        "queries": len(task.queries),
        "corpora": n_corpora,
        "passages": sum(len(t) for t in task.corpora.values()),
        "limit": limit,
        "seed": seed,
        "dense": dense if dense != "wordllama" else f"wordllama ({DENSE_NOTE['wordllama']})",
        "lsa_dims": [min(dims), max(dims)],
        "notes": task.notes,
        "versions": {"python": platform.python_version(), "numpy": version("numpy"), "wordllama": version("wordllama")},
    }


def _rows(task, golds, rec, rows, cluster, seed):
    texts_of = task.corpora
    ov = np.array([M.overlap(q.text, [texts_of[q.corpus][j] for j in g]) for q, g in zip(task.queries, golds)])
    group = M.terciles(ov)
    base = rec["tfidf"][:, 0]
    out = []
    for k in rows:
        nd = rec[k][:, 0]
        row = {
            "key": k,
            "label": R.LABELS[k],
            "ndcg": nd.mean(),
            "mrr": rec[k][:, 1].mean(),
            "hit": rec[k][:, 2].mean(),
            "gold_first": int((rec[k][:, 3] == 1).sum()),
            "gold_in_top10": int((rec[k][:, 3] <= M.K).sum()),
            "ndcg_by_overlap_third": [nd[group == g].mean() if (group == g).any() else None for g in range(3)],
        }
        if cluster is not None:
            row["ndcg_ci"] = M.interval(nd, cluster, seed=seed)
            row["diff_vs_tfidf"] = [(nd - base).mean(), *M.interval(nd - base, cluster, seed=seed)]
        out.append(row)
    info = {"queries_per_third": [int((group == g).sum()) for g in range(3)], "cutoffs": list(np.quantile(ov, [1 / 3, 2 / 3]))}
    paired = []
    for a, b in PAIRS if cluster is not None else []:
        if a in rec and b in rec:
            d = rec[a][:, 0] - rec[b][:, 0]
            paired.append({"a": a, "b": b, "diff": [d.mean(), *M.interval(d, cluster, seed=seed)]})
    return _round(out), _round(info), _round(paired)


def _worst(queries, rec_k) -> list[dict]:
    order = np.argsort(-rec_k[:, 3], kind="stable")[:10]
    return [{"id": queries[i].id, "query": _cut(queries[i].text, 120), "rank": int(rec_k[i, 3])} for i in order]


def _leak_checks(task, qrels, golds, corpus_of, by_corpus, top, rows, seed) -> dict:
    # 1. Recompute BM25 for one corpus from strings alone: same top 10 as the run. The same code runs twice, so this checks
    #    determinism only; that no label reaches a retriever comes from Task holding strings and from the test on score_all.
    cid, idx = next(iter(by_corpus.items()))
    texts = task.corpora[cid]
    again = R.order(R.Corpus(texts, [task.queries[i].text for i in idx]).bm25(), R.tiebreak(len(texts), seed))[:, : M.K]
    # 2. Score the same rankings against gold sets dealt to other queries: the metrics should fall toward the random row.
    #    A dealt set can share passages with the query's own (a contract's categories often mark the same sentences).
    shuffled = {k: 0.0 for k in rows}
    for s in range(SHUFFLES):
        wrong = M.shuffle_qrels(qrels, corpus_of, seed + s)
        wrong_golds = [wrong[q.id] for q in task.queries]
        for k in rows:
            shuffled[k] += np.mean([M.ndcg(t, g) for t, g in zip(top[k], wrong_golds)]) / SHUFFLES
    out = {
        "bm25_rankings_identical_without_labels": bool((again == top["bm25"][idx]).all()),
        "ndcg_with_shuffled_labels": {k: round(v, 4) for k, v in shuffled.items()},
        "shuffles": SHUFFLES,
        "queries_found_verbatim_in_gold": sum(
            q.text.lower() in " ".join(task.corpora[q.corpus][j] for j in g).lower() for q, g in zip(task.queries, golds)
        ),
        "tfidf_parity": _parity(task, golds, seed),
        # Shuffled gold sets can still land on passages that are gold for another query; this counts how often passages are shared.
        "gold_overlap": {
            "marks": sum(len(g) for g in golds),
            "distinct": sum(len(set().union(*(golds[i] for i in idx))) for idx in by_corpus.values()),
            "passages": sum(len(task.corpora[c]) for c in by_corpus),
        },
    }
    if task.name == "fixture":
        out["max_content_words_shared_with_gold"] = max(
            len(M.shared_tokens(q.text, [task.corpora[q.corpus][j] for j in g])) for q, g in zip(task.queries, golds)
        )
    return out


def _parity(task, golds, seed) -> dict:
    """The bench's numpy TF-IDF against the auditor's own _build_idf, _tfidf_vector and _cosine, on sampled queries."""
    sample = random.Random(seed).sample(range(len(task.queries)), min(PARITY_QUERIES, len(task.queries)))
    by_corpus: dict[str, list[int]] = {}
    for i in sample:
        by_corpus.setdefault(task.queries[i].corpus, []).append(i)
    worst = 0.0
    for cid, idx in by_corpus.items():
        texts = task.corpora[cid]
        mine = R.Corpus(texts, [task.queries[i].text for i in idx]).tfidf()
        idf = _build_idf(texts)
        vectors = [_tfidf_vector(t, idf) for t in texts]
        for row, i in zip(mine, idx):
            q = _tfidf_vector(task.queries[i].text, idf)
            worst = max(worst, float(np.abs(np.array([_cosine(q, v) for v in vectors]) - row).max()))
    return {"queries": len(sample), "max_abs_difference": worst}


def _round(x, digits: int = 4):
    if isinstance(x, dict):
        return {k: _round(v, digits) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, digits) for v in x]
    return round(float(x), digits) if isinstance(x, (float, np.floating)) else x


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", choices=LOADERS, required=True)
    ap.add_argument("--limit", type=int, help="squad: sample this many queries; cuad: sample this many contracts")
    ap.add_argument("--dense", choices=["wordllama", "openai", "none"], default="wordllama")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", help="results JSON. Without it, docs/retrieval-results.json is written only for a full default run.")
    args = ap.parse_args()

    start = time.time()
    result = run_dataset(args.dataset, args.limit, args.dense, args.seed)
    print(report.markdown_table(result))
    print(report.leak_block(result))
    default_run = args.limit is None and args.dense == "wordllama" and args.seed == 0
    path = args.out or (str(RESULTS) if default_run else None)
    if path:
        _save(result, path, html=None if args.out else HTML)
        print(f"\nwrote {path}")
    else:
        print("\n--limit, --dense or --seed changed the run, so docs/ was not touched. Pass --out to save it.")
    print(f"wall-clock {time.time() - start:.1f} s, python {platform.python_version()}, numpy {np.__version__}")


def _save(result: dict, path: str, html) -> None:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    data[result["dataset"]] = result
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if html:
        report.write_html(data, html)
        print(f"wrote {html}")


if __name__ == "__main__":
    sys.exit(main())
