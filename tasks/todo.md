# Task List: Azure Deployment (Terraform)

Full detail per task. See `tasks/plan.md` for the narrative, dependency graph, and risks. See `SPEC-azure-deployment.md` for the approved architecture.

Standing instruction for every task that writes a `.tf` file: invoke `full-output-enforcement` — no truncated resource blocks, no placeholder comments.

## Phase 1: Foundation

### Task 1: Bootstrap remote Terraform state ✅ DONE

**Description:** One-time idempotent `az` CLI script (not Terraform — avoids the chicken-and-egg problem of a backend storing state for the run that would create it) creating the state resource group, storage account, and blob container.

**Note:** region changed from `westeurope` to `northeurope` mid-implementation — Azure rejected new resources in `westeurope` for this subscription (`RequestDisallowedByAzure`, capacity restriction on new/trial subscriptions). Confirmed with the user; all resource naming updated repo-wide (`-ne` suffix). See `SPEC-azure-deployment.md` Assumptions §0.

**Correction (found during Task 2):** an earlier version of this note claimed the script's `Storage Blob Data Contributor` role grant was redundant (subscription Owner already covers blob data-plane access) and removed it. That conclusion was wrong. The grant calls were failing for an unrelated reason: Git Bash on Windows mangles any argument starting with `/` (treats it as a POSIX path and rewrites it), which corrupted every `--scope /subscriptions/...` value and produced a misleading `MissingSubscription` error with no hint of the real cause. Confirmed via `MSYS_NO_PATHCONV=1`, which fixed it immediately. The grant genuinely is required — Terraform's backend needs to LIST blobs to check for existing state, which Owner's implicit access does not cover even though it does cover container *creation*. The role assignment is back in the script, scoped to the resource group (this RG is single-purpose — only ever holds this one storage account — so RG-scope carries the same real blast radius as account-scope here), with `MSYS_NO_PATHCONV=1` on both the idempotency check and the create call. Verified idempotent across two consecutive runs.

**Acceptance criteria:**
- [x] Checks for existence before creating each resource — safe to re-run
- [x] Storage account name distinct from the app's own `stdocauditprodne` (different lifecycle, outlives `terraform destroy` of the main stack)
- [x] Script prints the resource group/storage account/container names `backend.hcl` will need

**Verification:**
- [x] Run twice in a row — second run makes zero changes (confirmed: both runs after initial creation showed only "already exists, skipping" + idempotent container create)
- [x] `az storage account show -n <name> -g <state-rg>` succeeds after running (confirmed, plus resource group and container also verified)

**Dependencies:** None

**Files likely touched:**
- `scripts/bootstrap-tfstate.sh`

**Estimated scope:** Small (1 file)

---

### Task 2: Provider pin + remote backend wiring ✅ DONE

**Description:** `versions.tf` pins `terraform` and `azurerm` (`~> 4.0`) and declares `provider "azurerm" { features {} }`. `backend.tf` declares an empty `backend "azurerm" {}` block. `backend.hcl` supplies the real resource group/storage account/container/key names from Task 1 — safe to commit (names, not credentials; backend blocks can't read Terraform variables, which is why this file exists as a separate `-backend-config` input). `backend.hcl` also sets `use_azuread_auth = true` so Terraform itself never touches a storage account key.

**Note:** initial `terraform init` failed with `AuthorizationPermissionMismatch` — this is what surfaced the missing RBAC grant now fixed in Task 1 (see its corrected note). Once that grant was in place, `init` succeeded cleanly.

**Acceptance criteria:**
- [x] `terraform init -backend-config=backend.hcl` succeeds from a clean checkout
- [x] `.terraform.lock.hcl` generated and committed (pins the exact resolved provider version — azurerm v4.81.0)
- [x] `infra/.gitignore` covers `*.tfstate*`, `*.tfvars` (except `*.tfvars.example`), `.terraform/`

**Verification:**
- [x] `terraform init -backend-config=backend.hcl` — succeeded, backend "azurerm" configured
- [x] `terraform fmt -check` — clean
- [x] `terraform validate` — "Success! The configuration is valid."
- [x] Confirmed no `.tfstate` file appears anywhere in the working tree after `init`

**Dependencies:** Task 1

**Files likely touched:**
- `infra/versions.tf`
- `infra/backend.tf`
- `infra/backend.hcl`
- `infra/.gitignore`

**Estimated scope:** Small (4 files)

---

### Task 3: Resource group + shared variable/output scaffolding ✅ DONE

**Description:** `main.tf` creates the resource group (`rg-docaudit-prod-ne`) and a `locals.common_tags` map (`project`, `environment`, `managed_by`) every later resource references. `variables.tf` gets its first entries (`location`, `environment`). `outputs.tf` gets its first output (resource group name). `terraform.tfvars.example` is the committed placeholder template.

**Acceptance criteria:**
- [x] `azurerm_resource_group` created in `northeurope`, tagged per the spec's Code Style convention
- [x] `locals.common_tags` defined once, referenced (not retyped) by every resource in later tasks
- [x] `terraform.tfvars.example` has placeholder values only, no real subscription ID or secrets (location/environment aren't sensitive, so the example shows real values)

**Verification:**
- [x] `terraform fmt -check && terraform validate` — both clean
- [x] `terraform plan -var-file=terraform.tfvars` reviewed before apply — 1 to add, 0 to change, 0 to destroy, matched design exactly
- [x] `terraform apply -var-file=terraform.tfvars` — applied, resource created after 26s
- [x] `az group show -n rg-docaudit-prod-ne` — confirmed, correct location and tags, `provisioningState: Succeeded`

**Dependencies:** Task 2

**Files likely touched:**
- `infra/main.tf`
- `infra/variables.tf`
- `infra/outputs.tf`
- `infra/terraform.tfvars.example`

**Estimated scope:** Medium (4 files)

---

### Task 4: Backend CORS becomes configurable ✅ DONE

**Description:** Today CORS is hardcoded to `http://localhost:5173`/`127.0.0.1:5173` only (`backend/app/main.py:47-53`) — deployed as-is, the production frontend cannot call the production backend at all. Add an optional `FRONTEND_ORIGIN` env var, additive to the existing dev-origin list. Single value, not a comma-separated list — this is a single-`prod`-only deployment, there's only ever one extra origin to add. Extract a small pure function (e.g. `_cors_allowed_origins() -> list[str]`) that reads the env and returns the list; `add_middleware` calls it once at import time, and tests call the function directly with `monkeypatch.setenv`/`delenv` rather than fighting the module-level `app` object.

**Acceptance criteria:**
- [x] `FRONTEND_ORIGIN` unset → behavior identical to today (only the two localhost dev origins allowed), no regression on existing tests
- [x] `FRONTEND_ORIGIN` set → that origin is additionally allowed
- [x] No wildcard (`*`) ever in `allow_origins`

**Verification:**
- [x] New tests in `backend/tests/test_api.py` written first (TDD) — confirmed failing (ImportError) before the change, all 3 passing after
- [x] Full `pytest` suite passes — 15 passed (was 12, +3 new)

**Dependencies:** None (parallel to Tasks 1-3)

**Files likely touched:**
- `backend/app/main.py`
- `backend/tests/test_api.py`

**Estimated scope:** Small (2 files)

---

### Task 5: Backend Dockerfile ✅ DONE

**Description:** No `backend/Dockerfile` exists yet. Multi-stage build on `python:3.12-slim` (matches `docker-compose.yml`): deps-install stage, then a slim runtime stage with a non-root user, `backend/` + `requirements.txt` copied in, `EXPOSE 8000`, `CMD` running `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`. The app reads sample documents from `REPO_ROOT/data/samples` at runtime (`backend/app/main.py:17-18`), so the image **must** `COPY data/samples/` in — scoped to just that subdirectory (not all of `data/`), so `data/raw/`, `data/private/`, `data/external/`, `data/eval/` (gitignored, some potentially private) can never end up in the public image even if present in a local checkout.

**Note:** deps installed into an isolated venv in the builder stage (not `pip install --user`) — avoids relying on HOME-directory resolution for the non-root runtime user, which is a real edge case that pattern can trip on. `.dockerignore` had to move from the originally-planned `backend/.dockerignore` to repo-root `.dockerignore` — Docker resolves it against the build context root, not the Dockerfile's own directory, and this build's context is repo root (`docker build -f backend/Dockerfile .`). Not load-bearing for correctness (the Dockerfile uses scoped `COPY` paths, not `COPY . .`), but it is what actually makes the ignore rules take effect.

**Acceptance criteria:**
- [x] Multi-stage build; final image contains no build tooling, just the app + deps
- [x] Runs as a non-root user — confirmed via `docker exec ... whoami` → `appuser` (uid=1000)
- [x] `data/samples/*.md` present in the image; `data/raw/`, `data/private/`, `data/external/`, `data/eval/`, `.git/`, `.venv/`, `node_modules/`, `frontend/`, test files are not — confirmed via `docker exec ... find`
- [x] Existing single `backend/requirements.txt` used as-is (no prod/dev split)

**Verification:**
- [x] `docker build -t docaudit-backend:local -f backend/Dockerfile .` — succeeded
- [x] `docker run -p 8010:8000 -e LLM_MODE=off docaudit-backend:local` then `curl http://127.0.0.1:8010/health` → `{"status":"ok"}`
- [x] `curl http://127.0.0.1:8010/samples` returns all 3 samples; spot-checked `/samples/consulting_report` content is readable

**Dependencies:** None (parallel to Tasks 1-3)

**Files likely touched:**
- `backend/Dockerfile`
- `backend/.dockerignore`

**Estimated scope:** Small (2 files)

---

### Task 6: Build and publish backend image to GHCR ✅ DONE

**Description:** Build with a git-short-SHA tag (`git rev-parse --short HEAD`) — not `latest`, since Container Apps only rolls a new revision when the Terraform-managed image string textually changes. Push to `ghcr.io/georgeanes/document-risk-auditor-backend`, confirm the package is public.

**Published image:** `ghcr.io/georgeanes/document-risk-auditor-backend:ae2696f`
**Digest:** `sha256:766810b4c4b5980ff03d4ee6076906583d1e0a9ce3331b3b00fac9fc627b7b80`
→ This is the exact tag Task 9 must reference in `var.image_tag`.

**Note — auth:** fine-grained PATs (`github_pat_...`) failed to push with `permission_denied: The token provided does not match expected scopes`, even freshly issued. GHCR write reliably needs a **classic** PAT with `write:packages` (a known fine-grained PAT limitation). Operator used a temporary classic PAT, then revoked it and logged Docker out — so the verification below ran genuinely unauthenticated.

**Note — visibility:** the package pushed **private** by default despite the repo being public (exactly the risk the plan flagged). Anonymous access returned 403 until visibility was flipped to Public in the package settings UI. Worth remembering if the package is ever recreated — the Container App configures **zero** registry credentials, so a private package would fail the pull with 401/403 at Task 9.

**Acceptance criteria:**
- [x] Image pushed with a git-SHA-based tag (`ae2696f`)
- [x] Package visibility explicitly confirmed/set to public in GHCR

**Verification:**
- [x] `docker build -t ghcr.io/georgeanes/document-risk-auditor-backend:ae2696f -f backend/Dockerfile .` — succeeded
- [x] `docker push ghcr.io/georgeanes/document-risk-auditor-backend:ae2696f` — succeeded, digest `sha256:766810b4...`
- [x] Anonymous registry token obtained + manifest fetch returned **200** (was 403 while private)
- [x] With Docker logged out of ghcr.io and the local copy deleted: `docker pull ghcr.io/georgeanes/document-risk-auditor-backend:ae2696f` **succeeded**, digest matched
- [x] Pulled artifact smoke-tested: `/health` → `{"status":"ok"}`, `/samples` → 3 samples, running as `appuser`

**Dependencies:** Task 4, Task 5

**Files likely touched:** None (Docker CLI + GHCR only)

**Estimated scope:** Small (0 files)

---

## Checkpoint: End of Phase 1
- [ ] `pytest` (full suite, including new CORS tests) passes
- [ ] `terraform fmt -check && terraform validate` clean; `rg-docaudit-prod-ne` exists in Azure
- [ ] Docker image builds, runs locally, `/health` and `/samples` both 200
- [ ] Image is live on GHCR and pullable with zero credentials
- [ ] Review with human before proceeding to Phase 2

---

## Phase 2: Independent Infra Shells

### Task 7: Static Web App resource — DONE

**Description:** Provision the SWA resource itself (Free tier), no content deployed yet — sequenced before the Container App specifically so its `default_host_name` exists and can be referenced as the Container App's CORS origin.

**Acceptance criteria:**
- [x] `azurerm_static_web_app` created, Free SKU, tagged
- [x] `outputs.tf` exposes `default_host_name` (for Task 9's CORS reference) and the deployment token (`api_key` attribute, marked `sensitive = true`, needed by Task 13)

**Verification:**
- [x] `terraform plan` reviewed (1 to add, 0 change, 0 destroy), then applied
- [x] `az staticwebapp show -n swa-docaudit-prod-eus2 -g rg-docaudit-prod-ne` returns the resource, Free SKU, all three common tags present
- [x] Hostname resolves over HTTPS: `https://ambitious-glacier-0ef327a0f.7.azurestaticapps.net` → 200, TLS verify 0

**Dependencies:** Task 3

**Files touched:**
- `infra/static_web_app.tf` (new)
- `infra/outputs.tf`
- `infra/variables.tf` (added `static_web_app_location`)
- `infra/.gitignore` (ignore saved plan files)

**Estimated scope:** Small (2 files) — actual: 4 files

**Outcome:** `swa-docaudit-prod-eus2`, hostname `ambitious-glacier-0ef327a0f.7.azurestaticapps.net`, commit `2c2c34f`. Free SKU, $0/month.

**Finding — SWA cannot live in `northeurope`.** Static Web Apps is offered in exactly five regions (`centralus`, `eastus2`, `westus2`, `westeurope`, `eastasia`), confirmed via `az provider show --namespace Microsoft.Web --query "resourceTypes[?resourceType=='staticSites'].locations"`. So this is the one resource in the stack that cannot inherit `var.location`; it needed its own `static_web_app_location` variable (with a `validation` block restricting it to those five). It still lives in the `rg-docaudit-prod-ne` resource group — only the resource's own region differs. `westeurope`, the only EU entry on that list, failed with the same `RequestDisallowedByAzure: The selected region is currently not accepting new customers` 403 that moved the stack off westeurope back in Task 1, leaving no EU option at all. Settled on `eastus2`. Serving is unaffected — SWA distributes content from a global CDN edge regardless of the resource's home region, and the latency-sensitive path (API calls) still terminates at the northeurope Container App. The bundle is static assets with no user data, so there is no data-residency consequence.

**Finding — `terraform output <name>` does NOT redact sensitive values.** Only the bulk `terraform output` form redacts (it prints `static_web_app_deployment_token = <sensitive>`). Naming a specific output is treated by Terraform as explicit intent to read it, so `terraform output static_web_app_deployment_token` prints the secret in the clear — which is what happened during this task's verification, leaking the live token into the session log. Rotated immediately with `az staticwebapp secrets reset-api-key`, then `terraform refresh` to pull the new value into state. **For Task 13, always use `terraform output -raw ...` piped directly into the deploy command — never as a bare command whose output lands in a log.** Also added `tfplan*` to `infra/.gitignore`: a saved plan file embeds the deployment token in full.

**Correction to the risk table:** the plan's mitigation for the token-leak risk was "output marked `sensitive = true`". That is necessary but *not* sufficient, as this task demonstrated — the marking does not protect a targeted `terraform output <name>`. The real mitigation is never materializing the token as standalone command output.

---

### Task 8: Cost Management budget alert — DONE

**Description:** `azurerm_consumption_budget_resource_group` scoped to `rg-docaudit-prod-ne`, $5/month threshold. Needs a notification contact email variable — no committed default; the real value goes in the operator's own gitignored `terraform.tfvars`.

**Acceptance criteria:**
- [x] Budget scoped to the resource group only (not subscription-wide) — verified: the only budget on the subscription is `.../resourceGroups/rg-docaudit-prod-ne/providers/Microsoft.Consumption/budgets/budget-docaudit-prod-ne`
- [x] $5/month cap, contact email from a new `variables.tf` entry with no default; only the `you@example.com` placeholder is committed, real address lives in gitignored `terraform.tfvars` (confirmed via `git check-ignore`)

**Verification:**
- [x] `terraform plan` reviewed (1 to add, 0 change, 0 destroy), then applied
- [x] `az consumption budget list -g rg-docaudit-prod-ne` → `budget-docaudit-prod-ne`, amount 5.0, Monthly, category Cost, start `2026-08-01T00:00:00Z`
- [x] Both notifications live: `actual_GreaterThan_25.000000_Percent` and `forecasted_GreaterThan_100.000000_Percent`
- [x] No perpetual diff — follow-up `terraform plan -detailed-exitcode` returned "No changes", exit 0

**Dependencies:** Task 3

**Files touched:**
- `infra/budget.tf` (new)
- `infra/variables.tf` (added `budget_amount`, `budget_contact_email`)
- `infra/terraform.tfvars.example` (placeholder email)

**Estimated scope:** Small (2 files) — actual: 3 files

**Outcome:** `budget-docaudit-prod-ne`, commit `43b677e`. Budgets are free.

**Decision — thresholds at 25% actual and 100% forecasted, not just 100%.** The spec estimates ~$0.01–0.06/month, so the $5 cap is ~80x expected spend: it is a runaway-detector, not a real budget. Alerting only at 100% would mean finding out after $5 is already gone. 25% actual ($1.25) is still ~20x the estimate, so it should never fire on ordinary usage, and it fires while the absolute loss is about a dollar. The forecasted alert catches a bad trend before it reaches the cap at all.

**Finding — a hardcoded `start_date` would have broken Task 15.** Azure requires a Monthly budget's start date to be the first of a month, and a *past* start date must fall within the current time grain — effectively the first of the current month. A literal `"2026-08-01T00:00:00Z"` therefore applies cleanly today and then fails on create the first time the stack is destroyed and recreated in any later month, which is exactly what Task 15's destroy/recreate proof does. `start_date` is instead derived as `formatdate("YYYY-MM-01'T'00:00:00'Z'", timestamp())`, so every fresh create computes a valid date. `timestamp()` is normally a perpetual-diff trap; `lifecycle { ignore_changes = [time_period[0].start_date] }` neutralises it, and this was verified rather than assumed — the post-apply plan is empty.

**Note — budgets alert, they never cap.** An Azure budget never throttles, stops, or deletes anything; it only emails. The one hard spend stop in this entire stack is `daily_quota_gb` on the Task 9 Log Analytics workspace, which actually halts ingestion when hit. Scale-to-zero keeps compute near zero, but that is a consequence of no traffic rather than an enforced ceiling. Worth remembering at Task 15 and when reading the cost estimate.

---

## Checkpoint: End of Phase 2
- [x] SWA resource live, default hostname resolves — `ambitious-glacier-0ef327a0f.7.azurestaticapps.net`, HTTPS 200
- [x] Budget alert visible in Cost Management — `budget-docaudit-prod-ne`, $5/month, RG-scoped
- [x] `terraform validate` clean with RG + SWA + budget all defined; `terraform fmt -check` clean; post-apply plan empty
- [ ] Review with human before proceeding to Phase 3 — **AWAITING**

---

## Phase 3: Backend Compute

### Task 9: Container Apps environment + backend Container App + managed identity

**Description:** The graph's pinch point — depends on Task 3 (RG), Task 6 (pushed image), and Task 7 (SWA hostname for CORS). `container_app.tf` holds three tightly-coupled resources: `azurerm_log_analytics_workspace` (`daily_quota_gb = 0.1` to cap ingestion, plus `retention_in_days = 30`), `azurerm_container_app_environment` (referencing the workspace), and `azurerm_container_app` with `identity { type = "SystemAssigned" }`, `min_replicas = 0`, `max_replicas = 2`, image from GHCR at the Task 6 tag, and an `ingress` block (`external_enabled = true`, `target_port = 8000`, `transport = "auto"` — without this there's no public FQDN at all). Env vars: `LLM_MODE=off`, `FRONTEND_ORIGIN=https://${azurerm_static_web_app.this.default_host_name}` (wires Task 4's code to Task 7's resource).

Reasonable to land as two commits internally (workspace+environment, then the app) while remaining one task/one verification pass, per the ~100-line-per-commit guidance.

**Correction (human, before implementation) — retention does not bound ingestion.** The original card claimed `retention_in_days = 30` "keeps ingestion inside the free 5GB/month grant". That is wrong: retention and ingestion are **separate meters**. `retention_in_days` controls how long data is *kept* once ingested; the free 5GB/month grant is on *ingestion*, and retention settings do not constrain it at all. As originally written, nothing in this stack bounded log volume — a chatty container could have ingested well past the grant and billed for it.

The actual control is `daily_quota_gb` on the workspace. Set to `0.1` — ample for one demo app, and when the cap is hit ingestion **stops** for the remainder of the UTC day rather than continuing to bill. `retention_in_days = 30` is kept as well, on its own merits: the first 31 days of retention are free, so 30 costs nothing and is worth having.

**This is the only hard spend stop anywhere in the stack.** The Task 8 budget *alerts* — it never caps, throttles, or deletes. `daily_quota_gb` is the single control in this architecture that actually halts a cost rather than emailing about it. Scale-to-zero keeps compute near zero by design, but it is a consequence of no traffic, not an enforced ceiling.

**Acceptance criteria:**
- [x] `daily_quota_gb` set on the Log Analytics workspace (ingestion hard-capped, not merely retained for 30 days) — `0.1`, alongside `retention_in_days = 30`
- [x] System-assigned managed identity present, no registry credentials configured anywhere (image pulled anonymously) — `identity.type = SystemAssigned`, principal `25309fc7-ff24-425f-9740-b688087fd3b5`; `properties.configuration.registries` and `.secrets` both `null`
- [x] `min_replicas = 0`, `max_replicas = 2`
- [x] Ingress external, HTTPS — plain HTTP returns 301 to the HTTPS URL (`allow_insecure_connections = false`)
- [x] `FRONTEND_ORIGIN` env var resolves to the real SWA hostname, not a placeholder — `https://ambitious-glacier-0ef327a0f.7.azurestaticapps.net`

**Verification:**
- [x] `terraform plan` reviewed (3 to add, 0 change, 0 destroy), then applied; follow-up plan empty (exit 0, no drift)
- [x] `curl https://<backend-fqdn>/health` → `{"status":"ok"}`, 200, TLS verify 0
- [x] `/samples` returns all 3 samples from the image's baked-in copy
- [x] `az containerapp show` confirms the identity block and zero registry credentials
- [x] Scale-to-zero proven as a full round trip (see finding below)
- [x] CORS preflight from the real SWA origin returns `access-control-allow-origin: https://ambitious-glacier-0ef327a0f.7.azurestaticapps.net` — Task 4 → Task 7 → Task 9 wiring confirmed live, ahead of Task 13

**Dependencies:** Task 3, Task 6, Task 7

**Files touched:**
- `infra/container_app.tf` (new)
- `infra/variables.tf` (added `image_tag`, `ghcr_owner`, `ghcr_image_name`)
- `infra/outputs.tf` (added `backend_fqdn`, `backend_principal_id`)

**Estimated scope:** Medium (3 files) — actual: 3 files

**Outcome:** commit `f5d6012`. FQDN `ca-docaudit-backend-prod-ne.calmmoss-5d3b8134.northeurope.azurecontainerapps.io`, backend principal ID `25309fc7-ff24-425f-9740-b688087fd3b5` (Tasks 10 and 11 scope their RBAC grants to it).

**Blocker hit — `Microsoft.App` was `NotRegistered`.** Registered with `az provider register --namespace Microsoft.App` and polled to `Registered` (~30s) before planning. Same class of failure as Task 1's `Microsoft.Storage`, where it surfaced as a misleading `SubscriptionNotFound`. Worth pre-checking provider registration on this subscription before any new resource type.

**Finding — the original "replica count is 0 immediately post-apply" check was wrong, and my first attempt at it produced a false positive.** Two separate problems:
1. A freshly created Container App always starts one provisioning replica to reach `Healthy`, so it is *not* 0 immediately post-apply. The criterion as written could never pass honestly.
2. My first scale-to-zero poll piped `az` errors to `/dev/null` and counted lines, so a *failed* command was indistinguishable from a genuine zero. It reported "scaled to zero" on the first poll, seconds after I had driven traffic — a result that should not have been believable, and was not.

Re-verified properly as a full round trip, with `--query "length(@)"` so a command failure aborts loudly instead of reading as zero: **0 replicas → request cold-starts in 21.0s returning 200 → replicas reads 1 → ~90s idle → replicas reads 0.** The check demonstrably reports both states, so zero means zero. Scale-to-zero is confirmed working.

**Finding — cold start is ~21 seconds.** This is the direct cost of `min_replicas = 0`, which is a non-negotiable constraint, so it stays. But it is a real UX consequence for a portfolio demo: the first visitor after any idle period waits ~21s for the first response, while a warm request is 0.26s. Worth surfacing on the project page or handling in the frontend with a loading state that sets expectations, rather than letting a reviewer think the app is broken. Flagged for Task 13/16 — not a defect to fix here.

**Finding — the ARM API reports `minReplicas: null`, not `0`.** `az containerapp show --query properties.template.scale` shows `minReplicas: null` even though Terraform state correctly holds `min_replicas = 0`. Azure omits the field when it is zero. Do not read that `null` as "unset/defaulted to something else" during Task 14 or Task 15 — the behavioural round-trip above is the authoritative check, not the field.

---

## Checkpoint: End of Phase 3
- [x] Backend reachable at its FQDN over HTTPS, `/health` returns 200 — plain HTTP 301s to HTTPS
- [x] No API key, connection string, or registry credential anywhere in `az containerapp show` output — `registries: null`, `secrets: null`
- [x] Scale-to-zero proven by round trip (0 → 1 on request → 0 after idle), not inferred from a config field
- [ ] Review with human before proceeding to Phase 4 — **AWAITING**

---

## Phase 4: Least-Privilege Data Plane

### Task 10: Blob Storage — account, private container, sample docs, RBAC

**Description:** `azurerm_storage_account` (`stdocauditprodne`) with `shared_access_key_enabled = false`. Private container (no public/anonymous access). Sample docs (`data/samples/*.md`, 3 tiny files) uploaded via `for_each` over `fileset("${path.module}/../data/samples", "*.md")`. RBAC: `azurerm_role_assignment` granting `Storage Blob Data Reader` to the Container App's `identity[0].principal_id`, scoped to the **container** specifically (not the storage account — account-level scoping would over-grant to any future container). **Confirmed scope: provision + prove the RBAC path only. The running app keeps serving `/samples` from its local baked-in copy (Task 5) — no runtime fetch from Blob Storage, no new Python dependency.**

**Acceptance criteria:**
- [ ] `shared_access_key_enabled = false` on the storage account
- [ ] Container has no anonymous/public access
- [ ] All 3 sample docs present as blobs, content matches `data/samples/`
- [ ] Role assignment scope is the container's resource ID, not the storage account's, and the role is `Storage Blob Data Reader` (read-only)

**Verification:**
- [ ] `terraform plan -var-file=terraform.tfvars` reviewed, then `apply`
- [ ] `az storage blob list --account-name stdocauditprodne --container-name <name> --auth-mode login` (operator's own login, not a key) lists 3 blobs
- [ ] `az role assignment list --assignee <backend-principal-id>` shows exactly this one grant, scoped to the container

**Dependencies:** Task 9

**Files likely touched:**
- `infra/storage.tf`

**Estimated scope:** Small (1 file)

---

### Task 11: Key Vault — DEFERRED (not built)

**Status: deferred by decision, 2026-08-26.** Not descoped permanently — deferred until an actual secret exists. Reinstate this card verbatim at that point.

**Original description:** `azurerm_key_vault` (Standard tier, `enable_rbac_authorization = true` — not access policies). RBAC role assignment `Key Vault Secrets User` → backend identity, scoped to the vault. Gemini secret written now but conditional: `count = var.gemini_api_key != null ? 1 : 0`. New `variables.tf` entry: `gemini_api_key`, sensitive, default `null`.

**Why deferred:**

1. **There is nothing to put in it.** With `LLM_MODE=off` there are zero application secrets. `GEMINI_API_KEY` is deferred by that same decision; storage keys are deliberately disabled in favour of RBAC (Task 10, `shared_access_key_enabled = false`); the SWA deployment token is a Terraform output that the application never reads. The planned secret resource was already `count = ... ? 1 : 0` — zero instances by construction. The task would provision an empty vault plus a `Key Vault Secrets User` grant to read nothing, and its acceptance criterion would literally be "confirm the vault is empty."

2. **It would actively damage Task 15.** Azure enforces soft-delete on every Key Vault — it cannot be disabled, and retention is 7–90 days. `terraform destroy` therefore does *not* cleanly remove a vault: the name stays reserved in a soft-deleted state, and the recreate half of the resilience proof fails unless the config also sets `purge_protection_enabled = false` and the provider gains `features { key_vault { purge_soft_delete_on_destroy = true } }`. That is real machinery, and it means weakening a safety default, in order to support a resource holding nothing. It conflicts directly with the spec's hard constraint that `terraform destroy` cleanly removes every resource it created.

3. **The security story does not depend on it.** Task 10 already demonstrates managed identity + resource-scoped RBAC + zero keys, with an acceptance criterion that can actually be proven. A Key Vault would be a second instance of the same pattern, empty.

**Reinstate when:** the first real secret appears — in practice the same change that sets `LLM_MODE=gemini` and introduces `GEMINI_API_KEY`. At that point the vault, the `Key Vault Secrets User` grant, and the Container App `secret` block referencing it all land together and can be verified end to end, and the Task 15 soft-delete handling gets added deliberately rather than pre-emptively.

**Consequence for the spec:** `SPEC-azure-deployment.md` lists Key Vault in its architecture and IAM table. It stays in the spec as the intended design for secret handling, annotated as not-yet-provisioned. The Task 16 architecture diagram must show the *built* system, so it must not draw a Key Vault box as though one exists.

---

## Checkpoint: End of Phase 4
- [ ] Backend identity has exactly **one** RBAC role assignment (`Storage Blob Data Reader`, scoped to the samples container) — revised from "two" now that Task 11 is deferred. Confirm via `az role assignment list --assignee <principal-id>` that nothing subscription- or RG-scoped exists
- [ ] No storage keys, SAS tokens, or Key Vault access policies exist anywhere
- [ ] Review with human before proceeding to Phase 5

---

## Phase 5: Frontend Build & Deploy

### Task 12: Static Web Apps routing fallback config

**Description:** No dependency on any Azure resource. New `frontend/public/` directory (doesn't exist yet) with `staticwebapp.config.json` containing a `navigationFallback` rewrite to `/index.html`, so direct navigation/refresh on `/scan`, `/overview`, `/findings/:claimId` doesn't 404. Vite copies `public/` contents verbatim into `dist/` root.

**Acceptance criteria:**
- [ ] `staticwebapp.config.json` present at `frontend/public/staticwebapp.config.json`
- [ ] `navigationFallback.rewrite` set to `/index.html`
- [ ] After `npm run build`, the file appears at `frontend/dist/staticwebapp.config.json` unmodified

**Verification:**
- [ ] `cd frontend && npm run build` then confirm `dist/staticwebapp.config.json` exists

**Dependencies:** None

**Files likely touched:**
- `frontend/public/staticwebapp.config.json`

**Estimated scope:** Small (1 file)

---

### Task 13: Production frontend build and deploy

**Description:** `VITE_API_BASE_URL` must be the real Container App FQDN from Task 9 — it's baked in at build time (`frontend/src/api.ts:3`), so this must happen after Task 9. Build with `VITE_API_BASE_URL=https://<backend-fqdn> npm run build`, then push `dist/` to the Task 7 SWA resource with `npx @azure/static-web-apps-cli deploy ./frontend/dist --deployment-token <token> --env production` (token from `terraform output -raw swa_deployment_token`, never written to a tracked file). `npx` avoids adding a persisted `devDependency` — confirmed with the human.

**Acceptance criteria:**
- [ ] Built with the real backend FQDN, not a placeholder or localhost fallback
- [ ] Deployed content includes `staticwebapp.config.json` at the root (proves Task 12 landed before this build)
- [ ] Deployment token never appears in a committed file or persistent shell history capture

**Verification:**
- [ ] SWA URL loads the app in a browser
- [ ] Run the sample audit end-to-end (select a sample, run scan) — network tab shows successful calls to the backend FQDN with no CORS errors
- [ ] Direct navigation to `/overview` (not just client-side routing to it) loads correctly, proving Task 12's fallback works in production

**Added scope — self-documenting cold start (decided 2026-08-26).** Task 9 measured a ~21s cold start (warm: 0.26s), the direct cost of `min_replicas = 0`. This is **not** to be hidden behind a generic spinner. The frontend must show a loading state on the first API call that explains the tradeoff, so a reviewer learns it was a deliberate engineering choice rather than concluding the app is broken. Approved copy, to use near-verbatim:

> Waking the backend — this deployment scales to zero when idle, so the first request after a quiet period takes ~20s. Subsequent requests are under 300ms. That tradeoff is why this runs at €0/month.

Implementation notes: applies to the first API call of a session (a cheap approach is to show it when a request exceeds ~1.5s rather than trying to track cold vs. warm state); it should not appear on every subsequent fast request. Keep the numbers honest — if the measured cold start drifts materially from ~20s, update the copy rather than leaving a stale claim.

**Additional acceptance criteria:**
- [ ] First-call loading state renders the cold-start explanation, not a bare spinner
- [ ] The message does not appear on fast/warm requests
- [ ] Quoted timings match what Task 14 actually measures

**Dependencies:** Task 9, Task 7, Task 12

**Files likely touched:**
- `frontend/src/` — loading state on the first API call (component + wherever `api.ts` calls are awaited)
- None required otherwise; optionally `frontend/package.json` gets a convenience `"deploy"` script wrapping the two commands (no new dependency, just a script alias)

**Estimated scope:** Small (0-1 files) — revised: Small–Medium, now includes a frontend loading state

---

## Checkpoint: End of Phase 5
- [ ] Frontend live on its SWA URL, backend live on its Container App FQDN, full audit flow works end-to-end between them
- [ ] No CORS errors in the browser console
- [ ] Review with human before proceeding to Phase 6

---

## Phase 6: Verification, Resilience Proof, Documentation

### Task 14: Full manual verification checklist

**Description:** Run every item in the spec's Testing Strategy checklist against the standing, live deployment — including driving some real traffic first so scale-to-zero can actually be observed afterward.

**Acceptance criteria:**
- [ ] Backend FQDN `/health` returns 200
- [ ] Frontend loads and completes a sample audit end-to-end against the live backend
- [ ] After driving a few requests, replica count returns to 0 within the Container Apps idle cooldown window
- [ ] No API key, connection string, or storage key appears in `az containerapp show` output, Terraform state, or container logs

**Verification:**
- [ ] Each checklist item confirmed via the `az` CLI command or browser action named above, not assumed

**Dependencies:** Task 9, Task 10, Task 11, Task 13

**Files likely touched:** None (verification only)

**Estimated scope:** Small (0 files)

---

### Task 15: `terraform destroy` / recreate resilience proof

**Description:** The spec requires `destroy` be tested at least once before calling this done. Destroying and recreating the Container Apps Environment and/or the Static Web App produces **new**, Azure-random hostnames (not derived from the resource name) — this invalidates the frontend's baked-in `VITE_API_BASE_URL` and the Container App's `FRONTEND_ORIGIN` CORS value. So this task is not just "destroy, then apply again" — it must end by redoing Task 13 (rebuild + redeploy the frontend) and re-verifying.

**Acceptance criteria:**
- [ ] `terraform destroy -var-file=terraform.tfvars` removes every resource the main config created
- [ ] `az resource list -g rg-docaudit-prod-ne` returns empty afterward
- [ ] State-backend resource group (from Task 1's bootstrap) is confirmed still present and untouched
- [ ] `terraform apply -var-file=terraform.tfvars` recreates the full stack
- [ ] Frontend rebuilt with the **new** backend FQDN and redeployed (not skipped)
- [ ] Post-recreate: `/health` 200, sample audit works end-to-end again

**Verification:**
- [ ] `az resource list -g rg-docaudit-prod-ne` (empty, then populated again post-reapply)
- [ ] Same browser end-to-end check as Task 14, re-run against the new URLs

**Dependencies:** Task 14

**Files likely touched:** None (operational)

**Estimated scope:** Small (0 files)

---

### Task 16: Architecture diagram and README link

**Description:** Mermaid diagram of the deployed Azure architecture at `docs/architecture-azure.md` (separate file — `docs/architecture.md` already exists and covers the general app architecture, not a merge target). Link it from `README.md`, after the existing "## Architecture" section. Written after Phase 5, not before, so it reflects reality if anything shifted during implementation.

**Acceptance criteria:**
- [ ] `docs/architecture-azure.md` diagram shows: browser → Static Web App → Container App (managed identity) → GHCR (image pull), Container App → Blob Storage (RBAC) → Key Vault (RBAC, provisioned/empty), remote state storage as a separate/dashed box (different lifecycle, not part of the destroyable stack)
- [ ] README links to it and is accurate against what was actually built

**Added scope — document the cold-start tradeoff on the project page (decided 2026-08-26).** The same explanation the frontend shows at runtime (Task 13) belongs in the written architecture notes, framed as a deliberate decision with a known cost:

> The backend scales to zero when idle, so the first request after a quiet period takes ~20s while a container cold-starts; subsequent requests are under 300ms. That tradeoff is why this runs at €0/month.

State it as a chosen tradeoff with its downside named, not as an apology or a caveat buried at the bottom. A reviewer who reads this learns the choice was made knowingly; a reviewer who just waits 21 seconds assumes the app is broken.

**Additional acceptance criteria:**
- [ ] Architecture doc explains scale-to-zero, the ~20s cold start, and why the tradeoff was taken
- [ ] Quoted timings match Task 14's measurements
- [ ] Diagram reflects what was actually built — **no Key Vault box**, since Task 11 is deferred and no vault exists

**Verification:**
- [ ] Mermaid renders correctly on GitHub
- [ ] Link from README resolves

**Dependencies:** Task 7, Task 9, Task 10, Task 13 (Task 11 deferred — not a dependency)

**Files likely touched:**
- `docs/architecture-azure.md`
- `README.md`

**Estimated scope:** Small (2 files)

---

## Checkpoint: Final
- [ ] All Success Criteria checkboxes in `SPEC-azure-deployment.md` verified true
- [ ] Full test suite passes (`pytest`, `npm run test`, optionally `npm run test:e2e`)
- [ ] Live deployment stands (post-Task-15 re-apply + re-deploy), reachable at its public URL
- [ ] Cost view checked a few days later against the spec's ~$0.01-0.06/month estimate (follow-up, not a same-day blocker)
