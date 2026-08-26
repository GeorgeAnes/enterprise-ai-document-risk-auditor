# Implementation Plan: Azure Deployment (Terraform)

## Overview

`SPEC-azure-deployment.md` (approved) defines the target architecture for deploying the Document Risk Auditor (FastAPI + React) to Azure at $0/month idle cost: Container Apps (backend, scale-to-zero) + Static Web Apps (frontend, free) + Blob Storage (samples) + remote Terraform state, all least-privilege via managed identity/RBAC, no keys or secrets anywhere. (Key Vault was in the approved spec but is **deferred** — see Deferred Scope below — because `LLM_MODE=off` leaves no secret to store.)

This plan turns that spec into an ordered, vertically-sliced task breakdown (full task cards in `tasks/todo.md`). Research (one Explore pass over the actual codebase, one Plan pass cross-referencing it against the spec) surfaced three gaps the spec didn't cover, because they only become visible once you trace the real code paths:

1. **CORS is hardcoded** to `http://localhost:5173`/`127.0.0.1:5173` only (`backend/app/main.py:47-53`) — deployed as-is, the production frontend cannot call the production backend at all (verified by reading the file).
2. **No SPA routing fallback** — the frontend uses `BrowserRouter` with real paths (`/scan`, `/overview`, `/findings/:claimId`, verified in `App.tsx`); without a Static Web Apps `navigationFallback` config, a direct nav or refresh on any route but `/` 404s.
3. **Build-time env var ordering** — `frontend/src/api.ts:3` reads `VITE_API_BASE_URL` at *build* time (`import.meta.env`), so the frontend's production build must happen **after** the Container App exists and has a stable FQDN, not before.

All three are included in the task list as real tasks, not scope creep — without them the deployed app doesn't actually work.

Two questions the spec left implicit were resolved with the human before finalizing this plan:
- **Blob Storage**: provisioned and RBAC-proven (backend identity can read it), but the running app keeps serving `/samples` from its local baked-in copy — no new Python dependency, matches the spec's literal success criteria.
- **Frontend deploy tool**: `npx @azure/static-web-apps-cli deploy` for the one-time manual deploy (CI/CD is separately deferred) — nothing persisted to `package.json`.

One more decided directly (low-stakes, no real tradeoff): Docker images are tagged with the git short SHA, not `latest` — Container Apps only rolls a new revision when the Terraform-managed image string textually changes, so a floating `latest` tag would silently stop deploying new builds after the first one.

## Architecture Decisions

- **Static Web App is provisioned before the Container App** (reorders the spec's illustrative file list into the real apply order) — the backend's CORS config needs the SWA's Azure-generated hostname, which doesn't exist until the SWA resource does.
- **Storage RBAC lands in its own phase, after the Container App**, not bundled with the resource group — the role assignment needs the backend's managed identity's principal ID, which doesn't exist until the Container App is created. (Originally "Storage + Key Vault"; Key Vault is now deferred.)
- **`shared_access_key_enabled = false`** on the storage account — turns "we don't use storage keys" from convention into a platform-enforced guarantee.
- **Sample blob uploads via `for_each` over `fileset()`**, not three hardcoded resource blocks.
- **The Static Web App is the one resource that cannot use `var.location`** (discovered in Task 7) — SWA is offered in only five regions, none of them `northeurope`, and the sole EU entry (`westeurope`) refuses new customers on this subscription. It takes a separate `static_web_app_location` variable defaulting to `eastus2` while still living in the `northeurope` resource group.
- Standing instruction for every `.tf` file written during implementation: invoke `full-output-enforcement` — no truncated resource blocks, no placeholder comments.

## Dependency Graph

```
Phase 1 — Foundation (two independent tracks, fully parallel)
  T1 bootstrap-tfstate.sh ──▶ T2 versions.tf+backend.tf+backend.hcl (terraform init) ──▶ T3 main.tf/RG (terraform apply #1)
  T4 CORS env-var support ─┐
  T5 backend/Dockerfile    ┴──▶ T6 build & push image to GHCR (public)

Phase 2 — Independent Infra Shells (both depend only on T3)
  T7 static_web_app.tf        T8 budget.tf

Phase 3 — Backend Compute (pinch point)
  T9 container_app.tf  ◀── T3 (RG) + T6 (image) + T7 (SWA hostname, for CORS)

Phase 4 — Least-Privilege Data Plane (depends on T9's managed identity)
  T10 storage.tf              [T11 key_vault.tf -- DEFERRED, not built]

Phase 5 — Frontend Build & Deploy
  T12 staticwebapp.config.json (no deps)
  T13 build + swa deploy  ◀── T9 (FQDN) + T7 (deploy token) + T12 (routing config)

Phase 6 — Verification, Resilience, Docs
  T14 full verification  ◀── T9, T10, T13
  T15 destroy/recreate proof  ◀── T14
  T16 architecture diagram + README link  ◀── T7, T9, T10, T13
```

## Task List (index — full cards in `tasks/todo.md`)

### Phase 1: Foundation
- [x] Task 1: Bootstrap remote Terraform state (script) — done; region switched westeurope → northeurope mid-task, RBAC grant fixed after diagnosing a Git Bash path-mangling bug (not subscription flakiness as first thought), see `tasks/todo.md` note
- [x] Task 2: Provider pin + remote backend wiring — done; `terraform init/fmt/validate` all clean, azurerm v4.81.0
- [x] Task 3: Resource group + shared scaffolding — done; `rg-docaudit-prod-ne` live in northeurope, tagged
- [x] Task 4: Backend CORS becomes configurable — done; TDD, 15 tests passing (was 12)
- [x] Task 5: Backend Dockerfile — done; multi-stage build, non-root user verified, /health + /samples verified in a running container. .dockerignore moved to repo root (Docker resolves it against build context, not the Dockerfile's directory)
- [x] Task 6: Build and publish image to GHCR — done; `ae2696f` published public, unauthenticated pull verified end-to-end. GHCR write needs a **classic** PAT (fine-grained PATs fail); package pushed private by default and had to be flipped to public

### Checkpoint: End of Phase 1
- [x] `pytest` passes (incl. new CORS tests) — 15 passed
- [x] `terraform fmt/validate` clean, resource group exists
- [x] Image builds/runs locally, `/health` + `/samples` both 200
- [x] Image pullable from GHCR with zero credentials
- [x] Review with human before Phase 2

### Phase 2: Independent Infra Shells
- [x] Task 7: Static Web App resource — done; `swa-docaudit-prod-eus2` live, hostname resolves 200 over HTTPS. SWA exists in only 5 regions and `northeurope` is not one, so it needed its own location variable; `westeurope` refused new customers (same 403 as Task 1), so it landed in `eastus2` — serving is CDN-global, so no latency or residency impact
- [x] Task 8: Cost Management budget alert — done; `budget-docaudit-prod-ne`, $5/month RG-scoped, alerts at 25% actual and 100% forecasted. `start_date` derived from `timestamp()` + `ignore_changes` rather than hardcoded — a fixed date would fail on any destroy/recreate in a later month, which Task 15 requires

### Checkpoint: End of Phase 2
- [x] SWA hostname resolves over HTTPS
- [x] Budget visible in Cost Management
- [x] `terraform validate` clean
- [x] Review with human before Phase 3 — approved

### Phase 3: Backend Compute
- [x] Task 9: Container Apps environment + backend app + managed identity — done; live at `ca-docaudit-backend-prod-ne.calmmoss-5d3b8134.northeurope.azurecontainerapps.io`, `/health` 200 over HTTPS, zero registry credentials. `Microsoft.App` needed registering first. Log Analytics ingestion capped via `daily_quota_gb = 0.1` per the human's correction. Scale-to-zero proven as a round trip after a first attempt produced a false positive; cold start measured at ~21s

### Checkpoint: End of Phase 3
- [x] Backend reachable over HTTPS, `/health` 200
- [x] No credentials in `az containerapp show`
- [x] Scale-to-zero behaviourally proven (0 → 1 → 0), not inferred from config
- [x] Review with human before Phase 4 — approved (with the Log Analytics ingestion correction applied, and Task 11 deferred)

### Phase 4: Least-Privilege Data Plane
- [ ] Task 10: Blob Storage — account, private container, sample docs, RBAC
- [~] Task 11: Key Vault — **DEFERRED**, not built. With `LLM_MODE=off` there are zero application secrets, so this would provision an empty vault plus a grant to read nothing. It would also break Task 15: Azure forces soft-delete on every vault, so `terraform destroy` leaves the name reserved and the recreate fails without `purge_soft_delete_on_destroy` and disabled purge protection — real machinery, weakening a safety default, for a resource holding nothing. Reinstate with the first real secret (the same change that enables Gemini). Full reasoning in `tasks/todo.md`

### Checkpoint: End of Phase 4
- [ ] Backend identity has exactly **one** RBAC grant (`Storage Blob Data Reader`, container-scoped) — revised from two, Task 11 deferred
- [ ] No keys/SAS/access-policies anywhere
- [ ] Review with human before Phase 5

### Phase 5: Frontend Build & Deploy
- [ ] Task 12: Static Web Apps routing fallback config
- [ ] Task 13: Production frontend build and deploy — now also includes a self-documenting cold-start loading state (Task 9 measured ~21s cold vs 0.26s warm). The first-call loading state explains the scale-to-zero tradeoff in plain language rather than hiding it behind a spinner, so a reviewer reads a deliberate choice instead of assuming the app is broken. Approved copy in `tasks/todo.md`

### Checkpoint: End of Phase 5
- [ ] Full audit flow works end-to-end between live frontend and backend
- [ ] Zero CORS errors
- [ ] Review with human before Phase 6

### Phase 6: Verification, Resilience, Docs
- [ ] Task 14: Full manual verification checklist
- [ ] Task 15: `terraform destroy` / recreate resilience proof
- [ ] Task 16: Architecture diagram and README link — must document the cold-start tradeoff in the same terms as Task 13, and must **not** draw a Key Vault box (Task 11 deferred, no vault exists)

### Checkpoint: Final
- [ ] Every Success Criteria box in `SPEC-azure-deployment.md` verified true
- [ ] Full test suite passes (`pytest`, `npm run test`, optionally `npm run test:e2e`)
- [ ] Live deployment stands post-Task-15
- [ ] Cost view checked a few days later against the ~$0.01–0.06/month estimate (follow-up, not a same-day blocker)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `stdocauditprodne` name is globally unique across all of Azure — may already be taken | Blocks T10's apply | Append a short suffix; only T10 needs the rename |
| GHCR package can default to private on first push even for a public repo | Container App pull fails 401/403, by design (zero configured credentials) | T6's verification requires an *unauthenticated* `docker pull`, not just a successful push |
| Destroy + recreate changes both the Container App FQDN and SWA hostname every time | Site silently broken post-recreate if frontend isn't rebuilt | T15's acceptance criteria require rebuild + redeploy + reverify, not just `terraform apply` |
| `image_tag` set to a mutable tag like `latest` | Terraform never detects a change, never rolls a new revision | Git short-SHA tag (decided above) |
| `azurerm ~> 4.0` floating constraint drifts between plan and implementation | Minor attribute drift | `.terraform.lock.hcl` committed after first `init`, pins the exact resolved version |
| Careless `FRONTEND_ORIGIN` implementation breaks local dev/docker-compose/tests | Violates "no commit without passing test suite" | T4's acceptance criteria require the existing dev origins keep working with the env var unset, TDD'd |
| SWA deployment token leaks via logs/shell history/a committed file | Full write access to site content | **Revised in Task 7** — `sensitive = true` alone is NOT sufficient: it only redacts the bulk `terraform output` form, while `terraform output <name>` prints the secret in the clear (this leaked the token once; rotated via `az staticwebapp secrets reset-api-key`). Real mitigation: only ever `terraform output -raw <name>` piped straight into the consuming command, plus `tfplan*` gitignored (a saved plan embeds the token) |

## Deferred Scope

- **Task 11 (Key Vault)** — deferred 2026-08-26 until a real secret exists. Deferring also avoids adding Key Vault soft-delete handling to Task 15's destroy/recreate proof. The spec still describes Key Vault as the intended secret-handling design; it is simply not provisioned yet, and the Task 16 diagram must reflect what was built.

## Verification (end-to-end, after all tasks)

1. `pytest` (root) — full backend + dataset-smoke suite passes.
2. `cd frontend && npm run test && npm run build` — unit tests and production build both succeed.
3. `terraform fmt -check && terraform validate` clean across `infra/`.
4. Live site: open the SWA URL, run a sample audit, confirm claims/evidence/export all render, confirm no console CORS errors.
5. `az resource list -g rg-docaudit-prod-ne` and `az role assignment list --assignee <backend-principal-id>` reviewed by hand against the spec's Security & IAM Design table.
6. `terraform destroy` + recreate proof (Task 15) completed at least once.

## Open Questions

None outstanding — the two architecturally significant ones (Blob Storage runtime role, SWA deploy tool) were resolved with the human before this plan was finalized; see Overview.
