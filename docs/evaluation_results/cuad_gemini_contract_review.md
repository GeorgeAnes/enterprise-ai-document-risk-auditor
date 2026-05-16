# CUAD Gemini Contract Review Stress Test

Small CUAD contract subset run through the deterministic auditor with optional Gemini reviewer notes.

- Contracts audited: 1
- Note: CUAD is used here as a contract-review stress test, not a hallucination benchmark.

## 2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement.txt

- Total extracted claims: 30
- Overall risk score: 33/100
- LLM review status: `completed`
- Gemini reviewer notes:
  - Here are a few reviewer notes:
  - Claims C029, C028, and C030 all point to potential issues with audit procedures and payment verification. The evidence provided seems to relate to the *consequences* of an audit (cost allocation, payment timelines) rather than the specific *terms* of the audit rights themselves, creating a "mixed signal" as noted. Human review is crucial to ensure clarity and enforceability of these audit clauses.
  - Claims C001, C003, C006, C008, and C010 are flagged as "weakly supported." The evidence provided for these claims often describes related concepts or uses different terminology (e.g., "CONTENT" vs. "MARKS," "ESCROW SERVICES" vs. a description of how they function). This suggests a potential mismatch or lack of direct textual support for the extracted claims.
  - The deterministic reason "mixed signals" for C029, C028, and C030 indicates that the automated system found conflicting or ambiguous information when trying to verify these claims against the provided evidence. This necessitates a human to interpret the context and ensure the claims accurately reflect the agreement's intent.

| Label | Risk | Clause / claim | Top evidence |
|---|---:|---|---|
| Needs human review | 80 | 5.3 AUDIT RIGHTS. i-Escrow shall keep for one (1) year proper records and books of account relating to the computation of advertising payments owed to 2TheMart (including, as appropriate, the computation of the size o... | Such inspection shall be at 2TheMart's expense; however, if the audit reveals overdue payments in excess of ten percent (10%) of the payments owed to date, i-Escrow shall immediately pay all cost of such audit. |
| Needs human review | 88 | Once every twelve (12) months, 2TheMart through a CPA may inspect and audit such records to verify reports. | Such inspection shall be at 2TheMart's expense; however, if the audit reveals overdue payments in excess of ten percent (10%) of the payments owed to date, i-Escrow shall immediately pay all cost of such audit. |
| Needs human review | 80 | Any such inspection will be conducted in a manner that does not unreasonably interfere with i-Escrow's business activities and with no less than fifteen (15) days notice. i-Escrow shall within two (2) weeks make any o... | Such inspection shall be at 2TheMart's expense; however, if the audit reveals overdue payments in excess of ten percent (10%) of the payments owed to date, i-Escrow shall immediately pay all cost of such audit. |

## Notes

- CUAD is used as a contract-review stress test, not as a hallucination benchmark.
- Rendered snippets are truncated for GitHub readability.
- Raw CUAD files remain ignored under `data/raw/`.
