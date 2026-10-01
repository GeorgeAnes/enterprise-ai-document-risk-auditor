"""Fixture-only tests for the retrieval bench: no downloads, no network. Skipped when numpy is not installed."""
import dataclasses
import json
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

np = pytest.importorskip("numpy")

from backend.app.core.retrieval import _build_idf, _cosine, _tfidf_vector  # noqa: E402
from evals.retrieval import datasets as D  # noqa: E402
from evals.retrieval import metrics as M  # noqa: E402
from evals.retrieval import report, run  # noqa: E402
from evals.retrieval import retrievers as R  # noqa: E402


def test_tfidf_matches_the_auditors_own_functions():
    task, _ = D.load_fixture()
    texts, queries = task.corpora["fixture"], [q.text for q in task.queries]  # many query words are unseen in the corpus
    mine = R.Corpus(texts, queries).tfidf()
    idf = _build_idf(texts)
    vectors = [_tfidf_vector(t, idf) for t in texts]
    for row, q in zip(mine, queries):
        assert np.allclose(row, [_cosine(_tfidf_vector(q, idf), v) for v in vectors], atol=1e-6)


def test_bm25_matches_worked_example_on_three_documents():
    # avgdl = 3, idf(apple) = ln(2.5/1.5 + 1) = 0.9808, idf(banana) = ln(1.5/2.5 + 1) = 0.4700
    # doc 1: apple tf 2 -> 2*2.2/(2 + 1.2*1.0) = 1.375; banana tf 1 -> 2.2/2.2 = 1.0; 1.375*0.9808 + 0.4700 = 1.8186
    # doc 2: banana tf 1, length 2 -> 2.2/(1 + 1.2*0.75) = 1.1579; 1.1579*0.4700 = 0.5442.  Doc 3: no query term.
    docs = ["apple banana apple", "banana cherry", "cherry cherry cherry date"]
    scores = R.Corpus(docs, ["apple banana"]).bm25()[0]
    assert scores == pytest.approx([1.8186, 0.5442, 0.0], abs=1e-3)


def test_rrf_exact_scores_and_order():
    lexical = np.array([[3.0, 2.0, 1.0, 0.0]])  # passage 3 matched no term, so this leg gives it nothing
    dense = np.array([[0.1, 0.9, 0.5, 0.2]])  # dense ranks: 1, 0, 2 (best first: passages 1, 2, 3, 0)
    fused = R.rrf([(lexical, True), (dense, False)], np.arange(4))[0]
    assert fused == pytest.approx([1 / 61 + 1 / 64, 1 / 62 + 1 / 61, 1 / 63 + 1 / 62, 1 / 63])
    assert list(R.order(fused[None, :], np.arange(4))[0]) == [1, 0, 2, 3]


def test_metrics_on_a_toy_ranking():
    ranked, gold = [5, 2, 9, 1], {2, 1}
    ideal = 1 + 1 / np.log2(3)
    assert M.ndcg(ranked, gold) == pytest.approx((1 / np.log2(3) + 1 / np.log2(5)) / ideal)
    assert (M.mrr(ranked, gold), M.hit(ranked, gold), M.first_rank(ranked, gold)) == (0.5, 1.0, 2)
    assert M.ndcg([7, 8], gold) == 0.0


def test_bootstrap_is_seeded_and_resamples_whole_clusters():
    values, clusters = np.array([1, 1, 1, 1, 0, 0]), ["a"] * 4 + ["b"] * 2
    first = M.bootstrap_means(values, clusters, 300, seed=3)
    assert np.array_equal(first, M.bootstrap_means(values, clusters, 300, seed=3))
    assert not np.array_equal(first, M.bootstrap_means(values, clusters, 300, seed=4))
    assert set(np.round(first, 6)) <= {0.0, round(4 / 6, 6), 1.0}  # two clusters can only be drawn as aa, ab, bb


def test_cuad_answer_spans_become_gold_chunks(tmp_path):
    sentences = [f"Item {i} says the supplier shall deliver to the customer before date {i}." for i in range(14)]
    context = "Master Services Agreement\n\n" + "  ".join(sentences[:7]) + "\n\n" + " ".join(sentences[7:])

    def qa(name, text=None, at=None):
        answers = [{"text": text, "answer_start": context.index(text) if at is None else at}] if text else []
        return {"id": name, "question": f'Highlight the parts (if any) of this contract related to "{name}" that should be reviewed by a lawyer. Details: about {name}', "answers": answers}

    across = sentences[4][-20:] + "  " + sentences[5][:15]  # crosses the double space between chunks 4 and 5
    qas = [qa("inside", "Item 2 says the"), qa("across", across), qa("empty"), qa("heading", "Master Services")]
    path = tmp_path / "data.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("CUADv1.json", json.dumps({"data": [{"title": "T", "paragraphs": [{"context": context, "qas": qas}]}]}))

    task, qrels = D.load_cuad(path)
    assert task.corpora["T"] == sentences  # the heading is not a chunk
    assert qrels == {"inside": {2}, "across": {4, 5}}
    assert (task.notes["queries_dropped_no_answer"], task.notes["queries_dropped_span_in_no_chunk"]) == (1, 1)
    assert task.queries[0].text == "inside. about inside"


def test_qrels_never_reach_a_retriever(monkeypatch):
    assert not {"qrels", "gold"} & {f.name for f in dataclasses.fields(D.Task)}
    seen = []
    real = R.score_all

    def spy(texts, queries, *rest):
        seen.append((texts, queries))
        return real(texts, queries, *rest)

    monkeypatch.setattr(run.R, "score_all", spy)
    run.run_dataset("fixture", dense="none")
    assert seen and all(isinstance(x, list) and all(isinstance(s, str) for s in x) for pair in seen for x in pair)


def test_shuffled_labels_collapse_to_chance():
    n = 50
    qrels, corpus_of = {i: {i} for i in range(n)}, {i: "c" for i in range(n)}
    perfect = [[i] + [j for j in range(n) if j != i] for i in range(n)]  # every query ranks its own gold first
    assert np.mean([M.ndcg(r, qrels[i]) for i, r in enumerate(perfect)]) == 1.0
    wrong = [M.shuffle_qrels(qrels, corpus_of, seed=s) for s in range(100)]
    assert sorted(map(sorted, wrong[0].values())) == sorted(map(sorted, qrels.values()))  # same gold sets, dealt differently
    assert np.mean([np.mean([M.ndcg(r, w[i]) for i, r in enumerate(perfect)]) for w in wrong]) < 0.15


def test_dense_row_falls_to_chance_with_shuffled_labels():
    pytest.importorskip("wordllama")
    checks = run.run_dataset("fixture")["leak_checks"]["ndcg_with_shuffled_labels"]
    real = {r["key"]: r["ndcg"] for r in run.run_dataset("fixture")["rows"]}
    assert real["dense"] > 0.5 and checks["dense"] < real["dense"] / 2


def test_every_fixture_paraphrase_shares_at_most_one_content_word_with_its_gold():
    task, qrels = D.load_fixture()
    assert (len(task.queries), len(task.corpora["fixture"])) == (20, 40)
    for q in task.queries:
        assert len(M.shared_tokens(q.text, [task.corpora["fixture"][j] for j in qrels[q.id]])) <= 1, q.id
    assert len(M.shared_tokens("supplier security report", ["The supplier must deliver a security report"])) == 3  # the check can fail


def test_fixture_run_and_static_report(tmp_path):
    result = run.run_dataset("fixture", dense="none")
    assert [r["key"] for r in result["rows"]] == [k for k in R.LABELS if k != "dense" and k != "rrf_bm25_dense"]
    assert len(result["inspector"]) == 20 and result["leak_checks"]["tfidf_parity"]["max_abs_difference"] < 1e-6
    assert result["leak_checks"]["gold_overlap"] == {"marks": 20, "distinct": 20, "passages": 40}  # one gold passage per query, none shared
    entry = result["inspector"][0]["maths"]  # the "show the math" cosine is the score the LSA row ranked by
    task, qrels = D.load_fixture()
    scores, _ = R.score_all(task.corpora["fixture"], [q.text for q in task.queries])
    assert entry["cosine"] == pytest.approx(scores["lsa"][0, min(qrels[task.queries[0].id])], abs=1e-3)
    page = tmp_path / "r.html"
    report.write_html({"fixture": json.loads(json.dumps(result))}, page)
    html = page.read_text(encoding="utf-8")
    assert "Show the math" in html and "http://" not in html and "https://" not in html
    assert not any(tag in html for tag in ("<link", " src=", "@import", "url("))


def test_paired_difference_is_first_minus_second_with_an_interval_per_cluster():
    task, qrels = D.load_fixture()
    golds, n = [qrels[q.id] for q in task.queries], len(task.queries)
    rec = {k: np.zeros((n, 4)) for k in ("tfidf", "tfidf_sub", "bm25")}
    rec["bm25"][:, 0], rec["bm25"][:10, 0] = 1.0, 0.5  # bm25 scores 1.0 on ten queries and 0.5 on the rest
    _, _, paired = run._rows(task, golds, rec, list(rec), list(range(n)), seed=0)
    assert [(p["a"], p["b"]) for p in paired] == [("bm25", "tfidf_sub")]  # the pairs that need the hybrid rows are skipped
    mean, low, high = paired[0]["diff"]
    assert (mean, low <= mean <= high) == (0.75, True)
    line = report._paired({"paired": paired})[0]
    assert line.startswith(R.LABELS["bm25"] + " minus " + R.LABELS["tfidf_sub"]) and "+0.750" in line


def test_openai_compatible_embedder_against_a_stub_server(tmp_path, monkeypatch):
    calls = []

    class Stub(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(body["input"])
            data = [{"index": i, "embedding": [float(len(t)), 1.0]} for i, t in enumerate(body["input"])]
            payload = json.dumps({"data": data[::-1]}).encode()  # out of order on purpose
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(R, "CACHE", tmp_path / "cache.sqlite")
    monkeypatch.setenv("EMBED_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("EMBED_MODEL", "stub")
    for var in ("NO_PROXY", "no_proxy"):  # a proxy in the environment must not take the loopback request
        monkeypatch.setenv(var, "127.0.0.1")
    try:
        assert R._openai_embed(["aa", "bbbb"]).tolist() == [[2.0, 1.0], [4.0, 1.0]]
        assert R._openai_embed(["aa", "bbbb"]).tolist() == [[2.0, 1.0], [4.0, 1.0]]
        assert calls == [["aa", "bbbb"]]  # the second call came from the cache
    finally:
        server.shutdown()
    monkeypatch.setenv("EMBED_BASE_URL", "file:///etc/passwd")
    with pytest.raises(ValueError):
        R._openai_embed(["x"])


def test_dense_row_is_labeled_after_its_embedder(monkeypatch):
    monkeypatch.setenv("EMBED_MODEL", "stub")
    monkeypatch.setitem(R.LABELS, "dense", R.LABELS["dense"])  # put back what the run changes
    monkeypatch.setattr(R, "get_embedder", lambda kind: lambda texts: np.ones((len(texts), 2), np.float32))
    labels = {r["key"]: r["label"] for r in run.run_dataset("fixture", dense="openai")["rows"]}
    assert labels["dense"] == "Dense, stub"
