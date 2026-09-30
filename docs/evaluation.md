# Retrieval evaluation

This benchmark tests query-to-passage retrieval on two public datasets, SQuAD and CUAD. It does not test claim-to-evidence retrieval, which is what the auditor does with a claim it extracted from a document. The CUAD "queries" are 41 fixed category prompts (for example "Governing Law") repeated across contracts, and are not claims. SQuAD questions were written by annotators who were reading the passage, which favors methods that match words. How far either fact changes the conclusions for the auditor's own claims has not been measured.

Run on 30 September 2026 with Python 3.11.15, numpy 2.4.6 and wordllama 0.4.0.post1 (2 vCPU, 7 GB RAM, Linux). The tables and leak-check numbers below are produced by the commands under Reproduce and stored in `docs/retrieval-results.json`; `python -m evals.retrieval.report --markdown` prints the tables again. The numbers described as one-off checks (LSA dimensions, the CUAD shuffle and the CUAD lowest third) came from short scripts run once on the same day. Those scripts are not in the repository.

## What every row sees

- Each passage is one string and each query is one string. All lexical rows tokenize with the auditor's own `_tokens` (lowercase, ASCII letters and digits with inner hyphens, at least three characters, 22 stop words). The dense row uses WordLlama's tokenizer, so it does not see identical tokens.
- Inverse document frequency (idf) comes from the passages a query searches: all 2,067 paragraphs for SQuAD, the sentences of one contract for CUAD. The auditor computes idf from the chunks of the one document it is auditing, plus the chunks of an evidence pack when one is supplied. The CUAD setup is close to that. The SQuAD setup does not, because its corpus is 2,067 paragraphs from many articles.
- `TF-IDF as shipped` is the auditor's scoring: raw term counts, idf = ln((N+1)/(df+1)) + 1, cosine. A query term absent from the corpus gets idf 1.0 and counts in the query length. `tests/test_retrieval_bench.py` compares it with the auditor's `_build_idf`, `_tfidf_vector` and `_cosine`, and every run repeats that comparison on 200 sampled queries (largest difference 6.4e-08 on SQuAD, 1.1e-07 on CUAD).
- `TF-IDF, sublinear tf` replaces the count with 1 + ln(count). It sits beside BM25 in every table because BM25 also saturates term frequency. Comparing BM25 with the shipped scorer alone would mix that effect with the rest of what BM25 changes.
- `BM25` uses k1 = 1.2, b = 0.75, the Lucene-style idf ln((N - df + 0.5)/(df + 0.5) + 1), and counts each distinct query term once. `BM25, b=0` switches off length normalization.
- `LSA-64` is a truncated SVD of the normalized tf-idf matrix with 64 dimensions (fewer when a corpus is smaller), and the query is projected into it. 64 is small for 2,067 paragraphs. A one-off check on 1,000 sampled SQuAD queries, not part of the bench, gave nDCG@10 0.532 at 256 dimensions, 0.700 at 1,024 and 0.753 at 2,066, which equals shipped TF-IDF on that sample (0.753). Treat the row as a low-rank floor.
- `Dense, static vectors` is WordLlama's 256-dimension static embeddings: a floor, not a verdict on embeddings. The WordLlama package is MIT licensed. The license of the weights inside its wheel was not checked, and nothing from it is vendored here.
- `RRF` sums 1 / (60 + rank) over its two legs. A lexical leg gives nothing to a passage that matched no query term. The dense and LSA legs rank every passage.
- Equal scores are ordered by one fixed random permutation per corpus, so a passage's position in the file never wins a tie. `Random` is a seeded random score matrix.

## Data

- SQuAD dev-v1.1: 10,570 questions over 2,067 paragraphs. The gold passage is the paragraph the question was written from. Cloned from `rajpurkar/SQuAD-explorer`; the data is distributed under CC BY-SA 4.0 according to the SQuAD site.
- CUAD-QA from `TheAtticusProject/cuad` (CC BY 4.0 according to the Atticus Project site). Each contract is one corpus, split into sentences by the auditor's own `normalize_text` and `chunk_text`. A sentence is gold when it overlaps an annotated answer span. A query is dropped when it has no answer or when its answer lies in no sentence (headings are not chunks). Contracts with 10 sentences or fewer are skipped because the top 10 would then be the whole contract and Hit@10 would be 1 for every method. The counts are in the table header below.
- Both are fetched with `git clone --depth 1` into `data/raw/`, which Git ignores. Nothing from them is committed. The commit that was cloned is stored in the results file.
- A 20-query fixture in `evals/fixtures/mini.json` runs offline (see Fixture).

## Metrics

nDCG@10 with binary gain, MRR@10 and Hit@10. Intervals are 95% percentile intervals from 1,000 bootstrap resamples (seed 0) that draw whole clusters: a SQuAD paragraph with all its questions, or a CUAD contract with all its queries. Each "difference" interval uses the same resamples for both methods, so it is a paired interval. Overlap is the share of a query's distinct content words that appear in its gold passage. The lowest third holds queries with overlap at or below the first tercile; ties stay in the lower group, so it can exceed a third of the queries.

## Results

### SQuAD dev-v1.1

SQuAD dev-v1.1: 10,570 queries, 2,067 paragraphs

| Method | nDCG@10 | 95% CI | Difference from shipped TF-IDF [95% CI] | MRR@10 | Hit@10 | nDCG@10, lowest-overlap third |
|---|---|---|---|---|---|---|
| Random | 0.002 | [0.002, 0.003] | -0.748 [-0.758, -0.738] | 0.001 | 0.005 | 0.001 |
| TF-IDF as shipped (raw tf) | 0.750 | [0.740, 0.760] | baseline | 0.701 | 0.901 | 0.612 |
| TF-IDF, sublinear tf (1 + ln tf) | 0.825 | [0.816, 0.834] | +0.075 [+0.071, +0.080] | 0.790 | 0.932 | 0.694 |
| BM25 (k1=1.2, b=0.75) | 0.846 | [0.838, 0.854] | +0.097 [+0.091, +0.102] | 0.817 | 0.938 | 0.703 |
| BM25, b=0 | 0.824 | [0.816, 0.833] | +0.074 [+0.068, +0.081] | 0.791 | 0.926 | 0.659 |
| LSA-64 | 0.338 | [0.328, 0.350] | -0.411 [-0.422, -0.401] | 0.279 | 0.532 | 0.246 |
| Dense, static vectors | 0.678 | [0.668, 0.688] | -0.072 [-0.080, -0.064] | 0.624 | 0.848 | 0.599 |
| RRF(BM25, dense) | 0.796 | [0.787, 0.805] | +0.046 [+0.040, +0.052] | 0.751 | 0.934 | 0.701 |
| RRF(BM25, LSA) | 0.588 | [0.578, 0.599] | -0.161 [-0.171, -0.153] | 0.514 | 0.826 | 0.466 |

Lowest-overlap third: 4,601 queries with overlap <= 0.500.

Paired differences in nDCG@10, 95% cluster-bootstrap interval:
- BM25 (k1=1.2, b=0.75) minus TF-IDF, sublinear tf (1 + ln tf): +0.021 [+0.018, +0.025]
- RRF(BM25, dense) minus BM25 (k1=1.2, b=0.75): -0.051 [-0.056, -0.045]
- RRF(BM25, LSA) minus BM25 (k1=1.2, b=0.75): -0.258 [-0.267, -0.249]

### CUAD-QA, sentence chunks

CUAD-QA, sentence chunks: 6,500 queries (41 distinct texts), 501 contracts, 14,041 queries dropped (13,867 with no annotated answer, 174 with an answer in no chunk); 9 contracts with 10 chunks or fewer skipped (369 queries)

| Method | nDCG@10 | 95% CI | Difference from shipped TF-IDF [95% CI] | MRR@10 | Hit@10 | nDCG@10, lowest-overlap third |
|---|---|---|---|---|---|---|
| Random | 0.037 | [0.033, 0.041] | -0.279 [-0.289, -0.270] | 0.031 | 0.112 | 0.046 |
| TF-IDF as shipped (raw tf) | 0.316 | [0.306, 0.326] | baseline | 0.294 | 0.586 | 0.121 |
| TF-IDF, sublinear tf (1 + ln tf) | 0.318 | [0.307, 0.328] | +0.001 [-0.001, +0.004] | 0.293 | 0.589 | 0.118 |
| BM25 (k1=1.2, b=0.75) | 0.324 | [0.314, 0.334] | +0.008 [+0.003, +0.012] | 0.311 | 0.587 | 0.091 |
| BM25, b=0 | 0.332 | [0.322, 0.341] | +0.015 [+0.009, +0.022] | 0.322 | 0.600 | 0.080 |
| LSA-64 | 0.291 | [0.280, 0.302] | -0.025 [-0.031, -0.020] | 0.264 | 0.541 | 0.111 |
| Dense, static vectors | 0.301 | [0.290, 0.311] | -0.016 [-0.024, -0.008] | 0.294 | 0.514 | 0.168 |
| RRF(BM25, dense) | 0.334 | [0.323, 0.344] | +0.017 [+0.011, +0.024] | 0.326 | 0.572 | 0.137 |
| RRF(BM25, LSA) | 0.322 | [0.311, 0.332] | +0.006 [+0.001, +0.010] | 0.302 | 0.585 | 0.104 |

Lowest-overlap third: 2,377 queries with overlap <= 0.125.

Paired differences in nDCG@10, 95% cluster-bootstrap interval:
- BM25 (k1=1.2, b=0.75) minus TF-IDF, sublinear tf (1 + ln tf): +0.007 [+0.002, +0.011]
- RRF(BM25, dense) minus BM25 (k1=1.2, b=0.75): +0.009 [+0.004, +0.016]
- RRF(BM25, LSA) minus BM25 (k1=1.2, b=0.75): -0.002 [-0.006, +0.002]

### Reading

- SQuAD, lexical: BM25 is 0.097 above the shipped TF-IDF, and sublinear TF-IDF is 0.075 above it. BM25 is still 0.021 above sublinear TF-IDF (interval 0.018 to 0.025). BM25 with b=0 (0.824) and sublinear TF-IDF (0.825) are level, and both recover about three quarters of BM25's gain over the shipped scorer. BM25 with b=0.75 is 0.022 above b=0, so length normalization is the part of the remaining gap that the table can point to. No row isolates BM25's idf.
- CUAD, lexical: the shipped TF-IDF, sublinear TF-IDF and both BM25 rows lie within 0.016 of each other. BM25 is 0.008 above the shipped scorer (interval 0.003 to 0.012) and 0.007 above sublinear TF-IDF (0.002 to 0.011), and b=0 is the highest lexical row. On single sentences the differences are small.
- Static dense vectors are below the shipped TF-IDF on both sets. On CUAD they are highest in the lowest-overlap third (0.168 against 0.121 for shipped TF-IDF and 0.091 for BM25). That is the group where queries share the fewest words with their gold sentence, which fits a method that does not match words. The tables give no interval for a third. A one-off check outside the bench, resampling contracts within those 2,377 queries, gave dense minus RRF(BM25, dense) +0.031 (0.024 to 0.039) and dense minus shipped TF-IDF +0.047 (0.036 to 0.058).
- Fusion: RRF(BM25, dense) is 0.051 below BM25 on SQuAD and 0.009 above it on CUAD (interval 0.004 to 0.016), where it has the highest point estimate, 0.002 above BM25 with b=0. The bench has no interval for that gap. RRF(BM25, LSA) is below BM25 on SQuAD and indistinguishable from it on CUAD.
- These rows show ranking quality against human-marked passages for these two tasks. They do not show claim verification, answer quality, or what a transformer embedding does, and they do not show that the auditor's retrieval would change by switching scorer.

## Leak checks

Printed after every run and stored in the results file.

- BM25's top 10 for the first corpus, computed a second time from the strings alone, equals the run. Both times run the same code, so this checks that the ranking is deterministic and does not depend on state left by other rows. It does not show that no label is used. That rests on the structure: a `Task` holds only passage and query text, and a test checks that `score_all` is called with lists of strings only.
- Each ranking is scored again against gold sets dealt to other queries of the same corpus (mean of 10 shuffles). On SQuAD every row falls to 0.002 to 0.003, level with Random. On CUAD the rows fall from between 0.291 and 0.334 to between 0.072 and 0.090, which is about twice Random (0.036). That floor is not zero because the shuffle can deal a query a gold set that shares a sentence with its own: inside a contract, categories often mark the same sentences (13,687 gold marks fall on 11,177 distinct sentences), and a query can be dealt its own set back. A one-off check outside the bench, using the same 10 shuffles, found this for 13.9% of CUAD queries. For the other queries the shuffled nDCG@10 was 0.040 for shipped TF-IDF and 0.044 for BM25, against 0.032 for Random. The shuffle does not exclude these cases, so on CUAD it overstates the floor. It still shows that the scores on the true labels depend on the labels.
- No query appears verbatim inside its gold passage.
- The paired and interval code is tested on toy data in `tests/test_retrieval_bench.py`.

## Fixture

`evals/fixtures/mini.json` holds 40 passages and 20 queries written by hand for this repository, each query a paraphrase of one passage sharing at most one content word with it (a test enforces this). Results are illustrative: 20 queries, no intervals, no claims. The fixture favors the dense row by construction. It was committed before the final runs, and its sha256 is printed in the report. On it the dense row ranks the gold passage first for 6 of 20 queries and in the top 10 for 20 of 20; shipped TF-IDF does so for 3 and 6.

## Reproduce

Bash:

```bash
pip install -r evals/requirements.txt
python -m evals.retrieval.fetch_data
python -m evals.retrieval.run --dataset fixture
python -m evals.retrieval.run --dataset squad
python -m evals.retrieval.run --dataset cuad
```

PowerShell: the same commands, with `.\.venv\Scripts\Activate.ps1` first.

A full run of a dataset writes `docs/retrieval-results.json` and `docs/retrieval-bench.html`. `--limit N` samples N SQuAD questions or N CUAD contracts and does not touch `docs/` unless `--out` is given. `--dense none` drops the dense rows.

Wall-clock time of the full runs on the machine above: fixture 0.4 s, SQuAD 67 to 157 s and CUAD 139 to 339 s over three runs of nearly the same code, the slower ones while other jobs were running (peak memory about 2.9 GB for SQuAD and 0.7 GB for CUAD).

`--dense openai` reads `EMBED_BASE_URL`, `EMBED_MODEL` and optionally `EMBED_KEY` for any OpenAI-compatible `/embeddings` endpoint and caches vectors in `data/eval/embed_cache.sqlite`. It has only been tested against a local stub server in `tests/test_retrieval_bench.py`.

## Limits

- Query-to-passage retrieval, not claim-to-evidence (see the first paragraph).
- One seed, one tokenizer, one setting of k1, b and LSA dimensions. No parameter was tuned.
- SQuAD uses one corpus for all questions and CUAD uses one corpus per contract, so idf differs between the two setups and neither equals the auditor's per-document idf on a claim.
- CUAD gold is derived from answer spans, so a sentence next to the answer is a miss, and sentences are a small unit for a prompt that describes a whole clause.
- CUAD queries with no annotated answer are dropped (13,867 of 20,910), so every query kept has a relevant sentence. That makes the task easier than one where the answer may be absent, as it can be for an audited claim.
- The dense row is one static model with 256 dimensions. No transformer embedding was run.
- The numpy matrices are dense: fine for 2,067 paragraphs or one contract, too large for hundreds of thousands of passages.
- Intervals cover sampling of queries and clusters only. They do not cover the choice of datasets or parameters, and no correction is made for the number of intervals reported.
- The overlap-third columns have no intervals, so small gaps between rows in one third should not be read as differences. Only the CUAD lowest-third result for dense vectors was checked with an interval, once, outside the bench.
- The thirds are defined from the gold text, so they select queries where word matching is handicapped by construction.
- The leak check that recomputes BM25 from strings runs the same code twice and cannot detect a label used inside it. The shuffled-label check on CUAD overstates its floor, as described under Leak checks.

## Not validated

- The GitHub Actions workflow in `.github/workflows/ci.yml` has not run. It was written here and cannot execute in this environment.
- `--dense openai` against a real endpoint, including Azure OpenAI in Foundry Models.
- Any Azure AI Search index, hybrid query or Foundry evaluator run. The mapping in the README is by description of the documentation only.
- Windows execution of the commands above. The paths use `pathlib` and the tests ran on Linux.
