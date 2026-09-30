"""Turn results JSON into a Markdown table, a leak-check block, and one static HTML page (no external assets)."""
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

from . import retrievers as R

TITLE = {"fixture": "Fixture (hand-written)", "squad": "SQuAD dev-v1.1", "cuad": "CUAD-QA, sentence chunks"}


def _f(x, sign=False):
    return "n/a" if x is None else f"{x:+.3f}" if sign else f"{x:.3f}"


def _ci(x, lo, hi, sign=False):
    return f"{_f(x, sign)} [{_f(lo, sign)}, {_f(hi, sign)}]"


def describe(r: dict) -> str:
    m, n = r["meta"], r["meta"]["notes"]
    text = f"{TITLE[r['dataset']]}: {m['queries']:,} queries, {m['passages']:,} passages"
    if r["dataset"] == "squad":
        text = f"{TITLE['squad']}: {m['queries']:,} queries, {m['passages']:,} paragraphs"
    if r["dataset"] == "cuad":
        dropped = n.get("queries_dropped_no_answer", 0) + n.get("queries_dropped_span_in_no_chunk", 0)
        text = (
            f"{TITLE['cuad']}: {m['queries']:,} queries ({n.get('distinct_query_texts', 0)} distinct texts), {m['corpora']:,} contracts, {dropped:,} queries dropped "
            f"({n.get('queries_dropped_no_answer', 0):,} with no annotated answer, {n.get('queries_dropped_span_in_no_chunk', 0):,} "
            f"with an answer in no chunk); {n.get('contracts_skipped_too_few_chunks', 0)} contracts with 10 chunks or fewer skipped "
            f"({n.get('queries_in_skipped_contracts', 0)} queries)"
        )
    if m["limit"]:
        text += f". LIMIT {m['limit']}: a subset"
    return text


def _cells(r: dict, row: dict) -> list[str]:
    if r["dataset"] == "fixture":  # counts only: 20 queries are too few for intervals
        n = r["meta"]["queries"]
        return [row["label"], f"{row['gold_first']} of {n}", f"{row['gold_in_top10']} of {n}", _f(row["ndcg"]), _f(row["mrr"])]
    cells = [row["label"], _f(row["ndcg"])]
    if "ndcg_ci" in row:
        diff = "baseline" if row["key"] == "tfidf" else _ci(*row["diff_vs_tfidf"], sign=True)
        cells += [f"[{_f(row['ndcg_ci'][0])}, {_f(row['ndcg_ci'][1])}]", diff]
    return cells + [_f(row["mrr"]), _f(row["hit"]), _f(row["ndcg_by_overlap_third"][0])]


def _head(r: dict) -> list[str]:
    if r["dataset"] == "fixture":
        return ["Method", "Gold ranked first", "Gold in top 10", "nDCG@10", "MRR@10"]
    ci = ["95% CI", "Difference from shipped TF-IDF [95% CI]"] if "ndcg_ci" in r["rows"][0] else []
    return ["Method", "nDCG@10", *ci, "MRR@10", "Hit@10", "nDCG@10, lowest-overlap third"]


def markdown_table(r: dict) -> str:
    head = _head(r)
    lines = [describe(r), "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(_cells(r, row)) + " |" for row in r["rows"]]
    if r["dataset"] != "fixture":
        o = r["overlap"]
        lines += ["", f"Lowest-overlap third: {o['queries_per_third'][0]:,} queries with overlap <= {o['cutoffs'][0]:.3f}."]
        lines += ["", "Paired differences in nDCG@10, 95% cluster-bootstrap interval:"] + [f"- {x}" for x in _paired(r)]
    return "\n".join(lines)


def _paired(r: dict) -> list[str]:
    return [f"{R.LABELS[p['a']]} minus {R.LABELS[p['b']]}: {_ci(*p['diff'], sign=True)}" for p in r["paired"]]


def leak_lines(r: dict) -> list[str]:
    lk = r["leak_checks"]
    sh = lk["ndcg_with_shuffled_labels"]
    rows = {x["key"]: x for x in r["rows"]}
    lines = [
        f"BM25 top 10 recomputed from strings alone matches the run: {lk['bm25_rankings_identical_without_labels']}",
        f"nDCG@10 against gold sets dealt to other queries of the same corpus, which can share passages with the query's own (mean of {lk['shuffles']}): "
        + ", ".join(f"{R.LABELS[k]} {sh[k]:.3f}" for k in R.LABELS if k in sh)
        + f"; random row on the true labels {rows['random']['ndcg']:.3f}",
        f"TF-IDF parity with the auditor's own functions: max |difference| {lk['tfidf_parity']['max_abs_difference']:.1e} over {lk['tfidf_parity']['queries']} queries",
        f"queries appearing verbatim inside a gold passage: {lk['queries_found_verbatim_in_gold']}",
        f"gold marks {lk['gold_overlap']['marks']:,} on {lk['gold_overlap']['distinct']:,} distinct passages, out of {lk['gold_overlap']['passages']:,} searched",
    ]
    if "max_content_words_shared_with_gold" in lk:
        lines.append(f"most content words any query shares with its gold passage: {lk['max_content_words_shared_with_gold']}")
    return lines


def leak_block(r: dict) -> str:
    return "\nLeak checks\n" + "\n".join("  " + x for x in leak_lines(r))


def _bars(r: dict) -> str:
    rows, ci = [x for x in r["rows"]], "ndcg_ci" in r["rows"][0]
    x0, width, h = 250, 440, 26
    out = [f'<svg viewBox="0 0 740 {len(rows) * h + 34}" role="img" aria-label="nDCG@10 by method, {escape(TITLE[r["dataset"]])}">']
    for t in (0, 0.25, 0.5, 0.75, 1):
        out.append(f'<line class="grid" x1="{x0 + t * width}" x2="{x0 + t * width}" y1="4" y2="{len(rows) * h + 4}"/>')
        out.append(f'<text class="axis" x="{x0 + t * width}" y="{len(rows) * h + 22}" text-anchor="middle">{t:g}</text>')
    for i, row in enumerate(rows):
        y = 4 + i * h
        cls = "bar base" if row["key"] == "tfidf" else "bar"
        out.append(f'<text class="lab" x="{x0 - 10}" y="{y + 17}" text-anchor="end">{escape(row["label"])}</text>')
        out.append(f'<rect class="{cls}" x="{x0}" y="{y + 4}" width="{max(row["ndcg"], 0) * width:.1f}" height="16"/>')
        end = x0 + row["ndcg"] * width
        if ci:
            lo, hi = row["ndcg_ci"]
            out.append(f'<path class="whisker" d="M{x0 + lo * width:.1f} {y + 12}H{x0 + hi * width:.1f}M{x0 + lo * width:.1f} {y + 7}v10M{x0 + hi * width:.1f} {y + 7}v10"/>')
            end = x0 + hi * width
        out.append(f'<text class="val" x="{end + 6:.1f}" y="{y + 17}">{row["ndcg"]:.3f}</text>')
    return "".join(out) + "</svg>"


def _table_html(r: dict) -> str:
    fixture = r["dataset"] == "fixture"
    head = _head(r) if fixture else _head(r)[:-1] + ["nDCG@10 by overlap third (low / mid / high)"]
    out = ["<table><thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in head) + "</tr></thead><tbody>"]
    for row in r["rows"]:
        cells = _cells(r, row) if fixture else _cells(r, row)[:-1] + [" / ".join(_f(v) for v in row["ndcg_by_overlap_third"])]
        cells[0] = escape(cells[0])
        out.append(f'<tr class="{"base" if row["key"] == "tfidf" else ""}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table>")
    if not fixture:
        n, c = r["overlap"]["queries_per_third"], r["overlap"]["cutoffs"]
        out.append("<p class=note>Paired differences in nDCG@10, 95% cluster-bootstrap interval:</p><ul>" + "".join(f"<li>{escape(x)}</li>" for x in _paired(r)) + "</ul>")
        out.append(f"<p class=note>Overlap = share of a query's content words found in its gold passage. The thirds hold {n[0]:,} / {n[1]:,} / {n[2]:,} queries (cutoffs {c[0]:.3f} and {c[1]:.3f}; ties stay in the lower third).</p>")
    return "".join(out)


def _worst_html(r: dict) -> str:
    out = ["<details><summary>Ten worst-ranked queries per method (rank of the best gold passage)</summary>"]
    for row in r["rows"]:
        items = "".join(f"<li><b>{w['rank']:,}</b> {escape(w['query'])}</li>" for w in r["worst"][row["key"]])
        out.append(f"<h4>{escape(row['label'])}</h4><ol>{items}</ol>")
    return "".join(out) + "</details>"


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auditor retrieval bench</title>
<style>
:root{--bg:#fff;--fg:#1c2330;--mute:#5b6577;--line:#d9dee7;--bar:#7b8aa3;--base:#c2410c;--gold:#e8f3e8;--panel:#f5f7fa}
@media(prefers-color-scheme:dark){:root{--bg:#12161d;--fg:#e3e8f0;--mute:#9aa5b8;--line:#2b3442;--bar:#6c7f9e;--base:#f97316;--gold:#1f3a26;--panel:#1a2029}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:0}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 8px;border-top:1px solid var(--line);padding-top:20px}h4{margin:12px 0 2px;font-size:13px}
p,li{max-width:80ch}.note,.meta{color:var(--mute);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}
th{white-space:normal;vertical-align:bottom}th:first-child,td:first-child{text-align:left}tr.base td{font-weight:600}
.scroll{overflow-x:auto}svg{width:100%;height:auto;max-width:760px;display:block;margin:8px 0}
.grid{stroke:var(--line)}.axis,.val{fill:var(--mute);font-size:11px}.lab{fill:var(--fg);font-size:12px}.bar{fill:var(--bar)}.bar.base{fill:var(--base)}.whisker{stroke:var(--fg);fill:none;stroke-width:1.2}
details{margin:10px 0}summary{cursor:pointer}pre{background:var(--panel);padding:10px;overflow-x:auto;font-size:12px;border-radius:6px}
select{font:inherit;max-width:100%;padding:4px;background:var(--panel);color:var(--fg);border:1px solid var(--line)}
.q{background:var(--panel);padding:10px 12px;border-radius:6px;margin:10px 0}.gold{background:var(--gold)}
#insp td{white-space:normal;text-align:left;vertical-align:top}#insp td:first-child{white-space:nowrap}.rank{font-weight:700;white-space:nowrap}
.snip{display:block;padding:2px 4px;margin:1px 0;border-radius:3px}.snip.g{background:var(--gold)}
code{font-size:12px;word-break:break-all}
</style></head><body><main>
<h1>Auditor retrieval bench</h1>
<p class="meta">Run on __DATE__ with __VERSIONS__. One static file with inline styles and script; nothing is fetched from anywhere.</p>
<p>What this measures: query-to-passage retrieval on two public datasets, not the auditor's claim-to-evidence task. CUAD "queries" are 41 fixed category prompts repeated across contracts. SQuAD questions were written by people looking at the passage, which favors lexical methods. How these results carry over to the auditor's own claims is not measured.</p>
__SECTIONS__
<h2 id="inspector">Query inspector</h2>
<p class="note">Precomputed at run time. Pick a query to see where its gold passage ranks under each method and what each method put first. Fixture queries are all shown; the SQuAD queries are a seeded sample of __NSQ__. A method that scored the gold passage 0 puts it among the other zero-score passages in a fixed random order.</p>
<select id="pick" aria-label="Query"></select>
<div id="insp"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const rows = JSON.parse(document.getElementById("data").textContent);
const pick = document.getElementById("pick"), box = document.getElementById("insp");
const el = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
rows.items.forEach((it, i) => { const o = el("option", it.set + ": " + it.query.slice(0, 90)); o.value = i; pick.appendChild(o); });
function show(i) {
  const it = rows.items[i]; box.replaceChildren();
  const q = el("div", undefined, "q"); q.append(el("b", "Query: "), it.query); box.append(q);
  const g = el("div", undefined, "q gold"); g.append(el("b", "Gold passage: "), it.gold_text); box.append(g);
  const t = el("table"); const h = el("tr"); ["Method", "Gold rank", "Top 3 returned (gold shaded)"].forEach(x => h.append(el("th", x))); t.append(h);
  rows.labels.forEach(([k, label]) => {
    const m = it.methods[k]; if (!m) return;
    const tr = el("tr"); tr.append(el("td", label), el("td", m.rank.toLocaleString(), "rank"));
    const td = el("td"); m.top.forEach(s => td.append(el("span", s.text, "snip" + (s.gold ? " g" : "")))); tr.append(td); t.append(tr);
  });
  const wrap = el("div", undefined, "scroll"); wrap.append(t); box.append(wrap);
  const d = el("details"); d.append(el("summary", "Show the maths (LSA, the gold passage vs the query)"));
  const x = it.maths, f = a => a.map(v => v.toFixed(4)).join(", ");
  d.append(el("pre", [
    "LSA keeps the top " + x.dims + " singular directions of the tf-idf matrix. A text becomes a vector of length " + x.dims + ".",
    "query vector, first 8 of " + x.dims + ":  " + f(x.query_first8),
    "gold vector,  first 8 of " + x.dims + ":  " + f(x.gold_first8),
    "norms over all " + x.dims + " values:     |q| = " + x.query_norm + "   |g| = " + x.gold_norm,
    "dot product q . g (all " + x.dims + " values): " + x.dot,
    "cosine = q . g / (|q| |g|) = " + x.dot + " / (" + x.query_norm + " x " + x.gold_norm + ") = " + x.cosine,
    "Retrieval ranks every passage by this cosine. The dense row does the same with vectors that a trained model produced."].join("\\n")));
  box.append(d);
}
pick.addEventListener("change", () => show(pick.value)); if (rows.items.length) show(0);
</script></main></body></html>"""


def write_html(data: dict, path) -> None:
    sections, items, versions = [], [], ""
    for name in ("squad", "cuad", "fixture"):
        r = data.get(name)
        if not r:
            continue
        v = r["meta"]["versions"]
        versions = versions or f"Python {v['python']}, numpy {v['numpy']}, wordllama {v['wordllama']}"
        note = f"<p class=note>Dense row: {escape(r['meta']['dense'])}. LSA dimensions: {r['meta']['lsa_dims'][0]} to {r['meta']['lsa_dims'][1]}. Ties are broken by a fixed shuffle.</p>"
        if name == "fixture":
            note += f"<p class=note>Illustrative only: 20 hand-written queries, no intervals, no claims. Every query shares at most one content word with its gold passage by construction, which is why the lexical rows are low. Fixture sha256 (line endings normalized to LF): <code>{r['meta']['notes']['fixture_sha256']}</code></p>"
        lk = "".join(f"<li>{escape(x)}</li>" for x in leak_lines(r))
        sections.append(
            f"<h2>{escape(TITLE[name])}</h2><p>{escape(describe(r))}</p><div class=scroll>{_table_html(r)}</div>{_bars(r)}{note}"
            f"<details><summary>Leak checks</summary><ul>{lk}</ul></details>{_worst_html(r)}"
        )
        for e in r["inspector"]:
            items.append({**e, "set": name})
    items.sort(key=lambda i: i["set"] != "fixture")  # fixture queries first: they are the offline demo
    payload = {"labels": [[k, v] for k, v in R.LABELS.items()], "items": items}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")  # sorted keys: the same bytes from a run and from the saved JSON
    n_sq = sum(1 for i in items if i["set"] == "squad")
    page = PAGE.replace("__SECTIONS__", "".join(sections)).replace("__DATA__", blob).replace("__NSQ__", str(n_sq))
    page = page.replace("__DATE__", next(iter(data.values()))["meta"]["date"]).replace("__VERSIONS__", versions)
    Path(path).write_text(page, encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Rebuild the HTML page, or print the Markdown tables, from docs/retrieval-results.json.")
    ap.add_argument("--markdown", action="store_true", help="print one Markdown table per dataset instead of writing HTML")
    args = ap.parse_args()
    from .run import HTML, RESULTS

    saved = json.loads(RESULTS.read_text(encoding="utf-8"))
    if args.markdown:
        print("\n\n".join(markdown_table(saved[k]) for k in ("squad", "cuad", "fixture") if k in saved))
    else:
        write_html(saved, HTML)
        print(f"wrote {HTML}")
