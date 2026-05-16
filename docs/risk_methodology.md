# Risk Methodology

This project does not claim to determine truth. It estimates document-grounding risk so a human reviewer can prioritize which claims need evidence, rewriting, or escalation.

## Labels

- `Supported`: the claim has a close supporting passage and no major risk language.
- `Weakly supported`: related evidence exists, but the match is not strong enough for high confidence.
- `Unsupported`: the claim is specific or assertive, but no close supporting passage was retrieved.
- `Vague / non-verifiable`: the claim uses broad language that is difficult to verify.
- `Needs human review`: mixed signals, exception language, or high-certainty wording make the claim unsuitable for automatic acceptance.

## Signals

The deterministic scorer considers:

- top evidence similarity from local TF-IDF retrieval
- numeric specificity such as percentages, dates, counts, and quarters
- citation markers such as `[1]`, `(source: ...)`, `Clause 4.2`, and `Section 2`
- high-certainty words such as `guaranteed`, `always`, `proven`, and `no risk`
- vague business language such as `best-in-class`, `robust`, and `industry-leading`
- caution or exception language in retrieved evidence, including `however`, `unless`, `pending`, and `not yet`

## Limitations

The method is intentionally transparent and lightweight. It can miss implicit support, deeper contradictions, table-only evidence, and domain-specific legal or technical nuance. It should be used as a reviewer triage tool, not an automated approval system.
