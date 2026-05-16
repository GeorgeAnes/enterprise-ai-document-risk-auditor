# UI Overhaul Plan

## Summary

Replace the current single light dashboard with a dark, premium enterprise risk-intelligence interface while preserving the existing FastAPI contracts and deterministic audit behavior.

The frontend remains React + Vite + TypeScript. Add `react-router-dom` for clean multi-screen navigation and Playwright for E2E smoke coverage. Backend APIs remain unchanged: `GET /samples`, `GET /samples/{sample_id}`, `POST /audit`, and client-side Markdown/JSON exports.

## Current Frontend Architecture Summary

- Current app is a single-screen React dashboard in `frontend/src/App.tsx`.
- `App.tsx` owns samples, selected sample, document text, evidence text, uploaded file, audit result, selected claim, filter, loading, and error state.
- `frontend/src/api.ts` calls the backend at `VITE_API_BASE_URL ?? http://127.0.0.1:8010`.
- Current components cover sample/upload controls, summary cards, claim table, evidence panel, optional LLM review, and export actions.
- Existing Vitest coverage is a component smoke test for summary metrics.
- Backend response data already supports the new screens: summary, label counts, claims, evidence snippets, markdown report, and optional LLM review.

## Proposed Screen / Route Structure

- `/scan`: ingestion screen with sample selection, document upload/paste, optional evidence pack, radar-style scan animation, and scan CTA.
- `/overview`: threat overview with risk score, status rings, category counts, top risks, executive summary, review checklist, LLM review, and export actions.
- `/findings/:claimId`: deep-dive document view with selected claim, risk explanation, evidence snippets, factors, confidence, document context, and navigation back to overview.

State persists across routes through a top-level `AuditProvider`. Refresh without an in-memory audit falls back gracefully to `/scan`.

## Component Breakdown

- Shell/navigation: `RiskCommandShell`, `TopNav`, `RouteBreadcrumbs`, `AuditProvider`.
- Scan screen: `ScanScreen`, `SampleSelector`, `DocumentDropzone`, `EvidencePackPanel`, `ScanRadar`, `ScanReadinessChecklist`.
- Overview screen: `ThreatOverviewScreen`, `RiskScoreRing`, `ClaimCategoryMatrix`, `TopRiskStack`, `ExecutiveBriefingPanel`, `ReviewChecklistPanel`, `ExportDock`, restyled `LLMReviewPanel`.
- Deep dive: `FindingDeepDiveScreen`, `ClaimRiskHeader`, `EvidenceSnippetStack`, `RiskFactorChips`, `DocumentContextPanel`, `FindingNavigator`.

## Styling / Theme Strategy

- Use a near-black/navy operational dashboard background.
- Use translucent dark panels with subtle borders and layered depth.
- Use controlled cyan and electric-purple accents, with amber/red for risk states.
- Use system sans typography for readability and monospace for excerpts, IDs, scores, and metadata.
- Keep cards at `8px` radius or less.
- Avoid noisy cyberpunk effects, decorative blobs, game-like styling, and neon overload.
- Maintain risk colors with accessible labels and scores.

## Animation Strategy

- CSS-only scan/radar animation while audit is running.
- Subtle pulse/glow for active scan state.
- Animated risk ring using CSS conic gradients.
- Controlled card entrance transitions.
- Respect `prefers-reduced-motion`.
- No heavy animation libraries in v1.

## State Management / Data Flow Plan

- Add `AuditProvider` for samples, active sample, document title/text, evidence text, selected file, audit result, selected claim, loading, error, and actions.
- Keep `auditDocument`, `fetchSamples`, and `fetchSample` API calls unchanged.
- Derive highest-risk claims, label counts, selected claim, risk severity band, and category distribution in the provider or screen layer.
- Deterministic audit remains the source of truth. Optional LLM review is explanatory only.

## Accessibility And Readability Constraints

- Use real buttons and links for navigation/actions.
- Provide visible focus states.
- Do not rely on color alone for risk state.
- Use readable text widths for evidence and document excerpts.
- Use `aria-live` for loading and error state.
- Support keyboard navigation through scan, overview, export, and findings workflows.
- Ensure dark-mode text contrast remains readable.

## Playwright E2E Test Plan

Add scripts:

- `test:e2e`
- `test:e2e:headed`

E2E scope:

- Open `/scan`.
- Confirm sample selector and scan CTA render.
- Run audit using the included sample.
- Verify navigation to `/overview`.
- Confirm risk score, category counts, top risks, and export actions render.
- Open the first top-risk finding.
- Verify `/findings/:claimId` shows claim text, explanation, and evidence snippets.

Keep Vitest for component smoke tests and update tests for the new component names.

## Step-By-Step Implementation Chunks

1. Routing and state foundation: add router, provider, and three routes.
2. Scan screen: build ingestion UI, scan animation, and sample/file/text audit flow.
3. Threat overview screen: build risk summary, risk ring, counts, top risks, LLM review, checklist, and export dock.
4. Deep dive screen: build claim detail, evidence stack, factors, confidence, and document context.
5. Theme and animation pass: replace light CSS with dark enterprise risk-intelligence theme and reduced-motion support.
6. Testing and documentation: add Playwright E2E, update Vitest smoke tests, and update README if run workflow changes.

## Definition Of Done

- Backend API contracts are unchanged.
- Deterministic audit still runs without an LLM.
- `/scan`, `/overview`, and `/findings/:claimId` are functional.
- `python -m pytest`, `npm.cmd test`, `npm.cmd run build`, and `npm.cmd run test:e2e` pass locally.
- UI is dark, serious, readable, and recruiter-ready.

## Risks And Things Not To Over-Engineer

- Do not add Redux/Zustand for this app size.
- Do not add shadcn CLI, CopilotKit, or a charting library in v1.
- Do not make paid LLM access required.
- Do not hide review substance behind animation.
- Do not change backend schemas unless absolutely necessary.
- Do not commit raw datasets, `.env`, generated test artifacts, `node_modules`, or build output.
