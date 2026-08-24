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

### Task 7: Static Web App resource

**Description:** Provision the SWA resource itself (Free tier), no content deployed yet — sequenced before the Container App specifically so its `default_host_name` exists and can be referenced as the Container App's CORS origin.

**Acceptance criteria:**
- [ ] `azurerm_static_web_app` created, Free SKU, tagged
- [ ] `outputs.tf` exposes `default_host_name` (for Task 9's CORS reference) and the deployment token (`api_key` attribute, marked `sensitive = true`, needed by Task 13)

**Verification:**
- [ ] `terraform plan -var-file=terraform.tfvars` reviewed, then `terraform apply -var-file=terraform.tfvars`
- [ ] `az staticwebapp show -n <name> -g rg-docaudit-prod-ne` returns the resource; its default hostname resolves over HTTPS

**Dependencies:** Task 3

**Files likely touched:**
- `infra/static_web_app.tf`
- `infra/outputs.tf`

**Estimated scope:** Small (2 files)

---

### Task 8: Cost Management budget alert

**Description:** `azurerm_consumption_budget_resource_group` scoped to `rg-docaudit-prod-ne`, $5/month threshold. Needs a notification contact email variable — no committed default; the real value goes in the operator's own gitignored `terraform.tfvars`.

**Acceptance criteria:**
- [ ] Budget scoped to the resource group only (not subscription-wide)
- [ ] Notification threshold at $5/month, contact email sourced from a new `variables.tf` entry with no default, never committed with a real value

**Verification:**
- [ ] `terraform apply -var-file=terraform.tfvars`
- [ ] `az consumption budget list -g rg-docaudit-prod-ne` shows the budget with the configured threshold

**Dependencies:** Task 3

**Files likely touched:**
- `infra/budget.tf`
- `infra/variables.tf`

**Estimated scope:** Small (2 files)

---

## Checkpoint: End of Phase 2
- [ ] SWA resource live, default hostname resolves
- [ ] Budget alert visible in Cost Management
- [ ] `terraform validate` clean with RG + SWA + budget all defined
- [ ] Review with human before proceeding to Phase 3

---

## Phase 3: Backend Compute

### Task 9: Container Apps environment + backend Container App + managed identity

**Description:** The graph's pinch point — depends on Task 3 (RG), Task 6 (pushed image), and Task 7 (SWA hostname for CORS). `container_app.tf` holds three tightly-coupled resources: `azurerm_log_analytics_workspace` (`retention_in_days = 30` — keeps ingestion inside the free 5GB/month grant), `azurerm_container_app_environment` (referencing the workspace), and `azurerm_container_app` with `identity { type = "SystemAssigned" }`, `min_replicas = 0`, `max_replicas = 2`, image from GHCR at the Task 6 tag, and an `ingress` block (`external_enabled = true`, `target_port = 8000`, `transport = "auto"` — without this there's no public FQDN at all). Env vars: `LLM_MODE=off`, `FRONTEND_ORIGIN=https://${azurerm_static_web_app.this.default_host_name}` (wires Task 4's code to Task 7's resource).

Reasonable to land as two commits internally (workspace+environment, then the app) while remaining one task/one verification pass, per the ~100-line-per-commit guidance.

**Acceptance criteria:**
- [ ] System-assigned managed identity present, no registry credentials configured anywhere (image pulled anonymously)
- [ ] `min_replicas = 0`, `max_replicas = 2`
- [ ] Ingress external, HTTPS
- [ ] `FRONTEND_ORIGIN` env var resolves to the real SWA hostname, not a placeholder

**Verification:**
- [ ] `terraform plan -var-file=terraform.tfvars` reviewed, then `apply`
- [ ] `curl https://<backend-fqdn>/health` → `{"status":"ok"}` over HTTPS
- [ ] `az containerapp show` confirms the identity block and zero registry credentials in the config
- [ ] Immediately post-apply (no traffic yet), replica count is 0

**Dependencies:** Task 3, Task 6, Task 7

**Files likely touched:**
- `infra/container_app.tf`
- `infra/variables.tf` (add `image_tag`)
- `infra/outputs.tf` (add backend FQDN)

**Estimated scope:** Medium (3 files)

---

## Checkpoint: End of Phase 3
- [ ] Backend reachable at its FQDN over HTTPS, `/health` returns 200
- [ ] No API key, connection string, or registry credential anywhere in `az containerapp show` output
- [ ] Review with human before proceeding to Phase 4

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

### Task 11: Key Vault — RBAC mode, RBAC grant, conditional Gemini secret

**Description:** `azurerm_key_vault` (Standard tier, `enable_rbac_authorization = true` — not access policies). RBAC role assignment `Key Vault Secrets User` → backend identity, scoped to the vault, created now regardless of Gemini status. The Gemini secret resource itself is written now but conditional: `count = var.gemini_api_key != null ? 1 : 0`, so it evaluates to zero instances for this deployment (`LLM_MODE=off`) without any future re-architecture needed to turn it on. New `variables.tf` entry: `gemini_api_key`, `type = string`, `sensitive = true`, `default = null`.

**Acceptance criteria:**
- [ ] Key Vault uses RBAC authorization mode (`enable_rbac_authorization = true`)
- [ ] Role assignment (`Key Vault Secrets User`) exists and is scoped to this vault only
- [ ] Zero secrets exist in the vault for this deployment

**Verification:**
- [ ] `terraform plan -var-file=terraform.tfvars` reviewed, then `apply`
- [ ] `az keyvault show --name <vault>` confirms `--enable-rbac-authorization true`
- [ ] `az keyvault secret list --vault-name <vault>` returns empty
- [ ] `az role assignment list --assignee <backend-principal-id>` now shows two grants total (Storage + Key Vault), nothing broader

**Dependencies:** Task 9

**Files likely touched:**
- `infra/key_vault.tf`
- `infra/variables.tf`

**Estimated scope:** Small (2 files)

---

## Checkpoint: End of Phase 4
- [ ] Backend identity has exactly two RBAC role assignments (`Storage Blob Data Reader` on the container, `Key Vault Secrets User` on the vault) — confirm via `az role assignment list --assignee <principal-id>` that nothing subscription- or RG-scoped exists
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

**Dependencies:** Task 9, Task 7, Task 12

**Files likely touched:**
- None required; optionally `frontend/package.json` gets a convenience `"deploy"` script wrapping the two commands (no new dependency, just a script alias)

**Estimated scope:** Small (0-1 files)

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

**Verification:**
- [ ] Mermaid renders correctly on GitHub
- [ ] Link from README resolves

**Dependencies:** Task 7, Task 9, Task 10, Task 11, Task 13

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
