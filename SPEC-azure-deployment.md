# Spec: Azure Deployment (Terraform)

> **Status (September 2026).** Two differences from the text below. Key
> Vault was deferred and is not provisioned (`tasks/todo.md`, Task 11;
> `docs/architecture-azure.md`). The app serves its samples from the container
> image, not from Blob Storage, although the Blob read grant exists. The public
> deployment has since been retired. Text below that describes a Key Vault as
> provisioned has been marked as deferred.

## Objective

Deploy the existing Document Risk Auditor (FastAPI backend + React/Vite frontend) to Azure so it is reachable at a public HTTPS URL for the portfolio page, using infrastructure entirely defined in Terraform. The deployment must cost $0/month at idle and stay inside Azure's *permanent* free tiers/grants (not just the 30-day trial credit), since this is a solo portfolio project expected to sit mostly idle between recruiter/reviewer visits.

Success looks like: `terraform apply` stands the whole stack up from nothing, the frontend loads and successfully audits the sample document end-to-end against the live backend, and `terraform destroy` tears it all back down to nothing, with a documented cost estimate confirmed before any resource is created.

## Assumptions

0. **Region is `northeurope`, not `westeurope`.** Discovered during Task 1 implementation: Azure currently rejects new resource creation in `westeurope` for this subscription (`RequestDisallowedByAzure` — Microsoft restricts some regions for new/trial subscriptions for capacity reasons). Confirmed with you; `northeurope` (Ireland) was chosen as the replacement — still EU-resident, one of Azure's most broadly-available regions. All resource names below use the `-ne`/`ne` suffix accordingly.
1. **Single environment.** One resource group (e.g. `rg-docaudit-prod-ne`), no dev/prod split — this is a single-operator portfolio demo, not a team project. *(finalized by default below — say so if wrong.)*
2. **Terraform state is remote**, in an Azure Storage Account — **confirmed.** Local state was rejected specifically because Phase 2 (GitHub Actions CI/CD) needs a state file reachable from CI, not just from one laptop.
3. **GitHub Container Registry package stays public** (matches the public GitHub repo). This means Azure Container Apps can pull the image with **no registry credentials at all** — one less secret to manage.
4. **CI/CD is out of scope for this spec** — confirmed by your own framing ("Phase 2 is a CI/CD pipeline"). This spec covers Terraform infra + manual `docker build/push` + `terraform apply`; GitHub Actions is the next spec once this one is proven and remote state exists for it to use.
5. **`LLM_MODE=off` for this deployment — confirmed.** Deterministic pipeline only. LM Studio was already ruled out (localhost-only, unreachable from Azure); Gemini is deliberately deferred too, not just LM Studio. Key Vault was to be provisioned now (per your standing "design it in, don't retrofit" instruction) with the RBAC wiring proven end-to-end, holding zero secrets until Gemini is turned on later. **Deferred, not provisioned:** it goes in with the first real secret — see Tech Stack.

### Remote state backend — bootstrap mechanics

Terraform's `backend "azurerm" {}` block can't reference input variables (a Terraform constraint, not a choice) and can't be created by the same Terraform run that will store its state in it (self-referential chicken-and-egg). So:

- A one-time **bootstrap script** (`az` CLI, not Terraform — see the `ponytail:` note in Project Structure) creates just the state resource group + storage account + blob container, once.
- `infra/backend.tf` declares an empty `backend "azurerm" {}` block; the actual values (storage account name, container, resource group, key) are supplied at `terraform init -backend-config=backend.hcl`.
- `backend.hcl` is **safe to commit** — it names resources, it doesn't contain credentials. Access to the state storage account is via the operator's own `az login` identity (RBAC), same least-privilege pattern as everything else in this spec, not a key.

## Tech Stack

- **IaC:** Terraform, `azurerm` provider (pin to latest 4.x at build time)
- **Backend compute:** Azure Container Apps, Consumption plan, `min_replicas = 0`
- **Backend registry:** GitHub Container Registry (`ghcr.io`), public package, free
- **Frontend hosting:** Azure Static Web Apps, Free tier
- **Object storage:** Azure Blob Storage (sample documents), private container, no anonymous access
- **Secrets:** Azure Key Vault, Standard tier, RBAC authorization mode (not legacy access policies) — **deferred, not provisioned**; planned to be added with the first real secret (a Gemini key) without any re-architecture
- **Identity:** System-assigned managed identity on the Container App — no storage keys, no connection strings, no SAS tokens on the application path (the separate state storage account from the bootstrap script still has shared keys enabled)
- **State backend:** Azure Storage Account (remote), bootstrapped once via script, referenced via `-backend-config` (see Assumptions)
- **Region:** `northeurope` (switched from westeurope — see Assumptions note below)

## Commands

```bash
# Terraform (run from infra/)
terraform init
terraform fmt -check
terraform validate
terraform plan  -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
terraform destroy -var-file=terraform.tfvars

# Backend image
docker build -t ghcr.io/georgeanes/document-risk-auditor-backend:<tag> -f backend/Dockerfile .
docker push ghcr.io/georgeanes/document-risk-auditor-backend:<tag>

# Frontend
cd frontend && npm run build   # deployed to Static Web Apps (mechanism decided in Tasks)
```

## Project Structure

```text
infra/
  versions.tf                → terraform + azurerm provider version pins
  backend.tf                 → empty `backend "azurerm" {}` block; values supplied via -backend-config=backend.hcl
  backend.hcl                → committed; state storage account/container/RG names (not secrets)
  main.tf                    → resource group, tags
  container_app.tf           → Container Apps environment, Log Analytics workspace (capped ingestion + retention), backend container app, managed identity
  static_web_app.tf          → Static Web App resource
  storage.tf                 → storage account + private container, sample-doc upload, RBAC role assignment (Storage Blob Data Reader → backend identity)
  key_vault.tf                → DEFERRED, not built: Key Vault (RBAC mode) + RBAC role assignment, planned empty; Gemini secret resource is conditional (created only once var.gemini_api_key is supplied)
  budget.tf                   → Cost Management budget + alert (free) scoped to the resource group
  variables.tf                 → inputs; sensitive vars (e.g. gemini_api_key) default to null, sourced from TF_VAR_* env vars at apply time
  outputs.tf                    → backend FQDN, frontend URL, resource group name
  terraform.tfvars.example       → committed template, placeholder values only
  .gitignore                      → *.tfstate*, *.tfvars (except .example), .terraform/   (defense in depth — the azurerm backend keeps state out of the working tree entirely, this just covers anyone who overrides it locally)

scripts/
  bootstrap-tfstate.sh              → new; one-time az CLI script creating the state RG + storage account + container.
                                        ponytail: script, not a nested Terraform root — avoids the self-referential
                                        "state that stores its own state" problem; idempotent (checks before create).
                                        Upgrade path if this ever needs real lifecycle management: its own tiny
                                        Terraform root with local state.

backend/
  Dockerfile                       → new; multi-stage build for the FastAPI app
  app/main.py                      → modified; CORS origins become configurable via FRONTEND_ORIGIN
                                      (discovered during planning: hardcoded to localhost only today,
                                      would silently block the deployed frontend from calling the backend)

frontend/
  public/staticwebapp.config.json  → new; navigationFallback so direct nav/refresh on /scan, /overview,
                                      /findings/:claimId doesn't 404 on Static Web Apps (discovered during
                                      planning: BrowserRouter has no server-side fallback without this)

docs/
  architecture-azure.md             → new; Mermaid diagram of the deployed architecture
```

Both additions above were found during the Plan phase by tracing the actual code paths, not anticipated when this spec was first written — see `tasks/plan.md` for the full reasoning. Neither changes any architectural decision above; both are required for the deployed app to actually work.

## Code Style

- One resource *family* per file (see Project Structure above) — not one file per resource.
- Every resource tagged: `project = "document-risk-auditor"`, `environment = "prod"`, `managed_by = "terraform"`. Tags are how you'll confirm in the Azure cost view that nothing untagged is quietly costing money.
- Resource naming: `<type>-docaudit-prod-ne` (e.g. `cae-docaudit-prod-ne` for the Container Apps environment, `stdocauditprodne` for storage — storage accounts can't contain hyphens).
- No hardcoded secrets or subscription IDs in `.tf` files — everything sensitive comes from `variables.tf` backed by environment variables.

```hcl
resource "azurerm_container_app" "backend" {
  name                         = "ca-docaudit-prod-ne"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                 = "Single"

  identity {
    type = "SystemAssigned"
  }

  template {
    min_replicas = 0
    max_replicas = 2   # hard cap on worst-case cost/abuse exposure

    container {
      name   = "backend"
      image  = "ghcr.io/georgeanes/document-risk-auditor-backend:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  tags = local.common_tags
}
```

## Testing Strategy

No automated Terraform test framework (Terratest, etc.) — disproportionate for a single-operator, single-environment stack. Instead:

- `terraform fmt -check` and `terraform validate` before every `plan`.
- **Never `apply` without reading the `plan` diff first** — no blind applies, no `-auto-approve`.
- Post-apply manual verification checklist:
  - [ ] Backend FQDN `/health` returns 200
  - [ ] Frontend URL loads and runs the sample audit end-to-end against the live backend
  - [ ] Container App replica count drops to 0 within its idle cooldown window after traffic stops (proves scale-to-zero actually works, not just configured)
  - [ ] No API key, connection string, or storage key appears in `az containerapp show` output, Terraform state, or container logs
- `terraform destroy` is tested at least once before calling this spec done, and confirmed clean via `az resource list -g <rg>` returning empty afterward.

## Security & IAM Design

*(Threat-modeled per `security-and-hardening` before any Terraform is written, per your standing instruction.)*

| Threat (STRIDE) | Risk here | Mitigation |
|---|---|---|
| Spoofing | Someone impersonates the backend to read/write blobs or secrets | Managed identity (no shared keys to leak/spoof) |
| Tampering | Sample docs modified in storage | Blob container private, only the backend identity has `Storage Blob Data Reader` (read-only, not Contributor) |
| Information disclosure | Storage keys, Gemini API key, or connection strings leak via repo/logs/state | No keys generated for the application or its samples account — managed identity + RBAC only; secrets sourced from `TF_VAR_*` env vars, never committed; Key Vault (deferred) in RBAC mode when added, not access-policy mode |
| Denial of service / unbounded consumption | A traffic spike or scripted abuse of the public `/audit` endpoint scales the Container App and/or racks up Gemini API cost | `max_replicas = 2` hard cap; Cost Management budget alert at a low threshold (e.g. $5) as a safety net given a card is attached |
| Elevation of privilege | Backend identity granted broader rights than it needs | RBAC role assignments scoped to the *specific* storage account and, once one exists, the *specific* Key Vault only — never subscription- or resource-group-wide `Contributor`/`Owner` |

Concretely:
- **No Azure Container Registry, no registry secret** — the GHCR image stays public, so Container Apps pulls it with zero credentials.
- **No storage account keys or SAS tokens** — backend identity gets `Storage Blob Data Reader` scoped to the one container.
- **No Key Vault access policies** — Key Vault (deferred, not provisioned) will use RBAC authorization; backend identity gets `Key Vault Secrets User` scoped to the one vault, and only if Gemini is enabled (Open Question 2).
- **CORS on the FastAPI backend is restricted to the exact Static Web App origin** — no wildcard.
- **HTTPS-only** on both Container Apps ingress and Static Web Apps (both are HTTPS-only by default; nothing to configure to disable it — the "always do" here is *not accidentally weakening this default*).

## Cost Estimate (northeurope, before building anything)

| Resource | Idle | Light demo traffic |
|---|---|---|
| Container Apps (Consumption, min=0) | $0 — no vCPU/memory billed while scaled to zero | ~$0 — a few dozen requests/day is far inside the permanent free grant (180k vCPU-s / 360k GiB-s / 2M requests per month) |
| Log Analytics workspace (required by Container Apps env) | $0 | $0 — well under the 5 GB/month free ingestion, bounded by `daily_quota_gb = 0.1`, which stops most ingestion when hit. The cap is not exact and data collected above it is still billed. Retention is a separate meter and does not bound ingestion; `retention_in_days = 30` is set on its own merits (first 31 days are free) |
| GitHub Container Registry | $0 | $0 — free for public packages, unlimited bandwidth |
| Azure Static Web Apps (Free tier) | $0 | $0 — 100 GB/month bandwidth included, hard-capped not billed |
| Blob Storage (a few small sample docs) | ~$0.00 | ~$0.00–0.01 — storage cost on a handful of KB-sized files rounds to fractions of a cent (the app does not read them at runtime) |
| Key Vault (Standard, RBAC) — deferred, not provisioned | $0 | $0 until built; once Gemini is enabled, a few secret reads per cold start, priced per 10k ops, still ~$0.00 |
| Terraform remote state (Storage Account, tiny) | ~$0.01 | ~$0.01 — one small `.tfstate` blob, negligible storage + transaction cost |
| Outbound data transfer | $0 | $0 — well inside the 100 GB/month free egress allowance |
| **Total** | **~$0.01/month** | **~$0.01–0.06/month** |

This is inside Azure's *standing* free tiers/grants — it should hold **after** the 30-day trial and the $200 credit are gone, as long as pay-as-you-go billing stays enabled. The one realistic way this stops being $0 is abuse/traffic-spike scaling past the free grant, which is why `max_replicas = 2` and a Cost Management budget alert are in scope, not optional extras.

## Boundaries

- **Always:** review `terraform plan` before every `apply`; tag every resource; managed identity + RBAC only, never keys/connection strings/SAS; keep `*.tfstate*` and non-example `*.tfvars` gitignored; HTTPS-only ingress everywhere.
- **Ask first:** any Azure resource type beyond what's listed here (Front Door, VNet, Private Endpoints, Application Insights, etc.); changing region; adding the CI/CD pipeline; adding any new dependency (per `CLAUDE.md`).
- **Never:** use Azure Container Registry (explicit user instruction — costs ~$5/mo); commit secrets, state, or real `.tfvars`; create storage account keys or SAS tokens; grant subscription- or resource-group-scoped `Owner`/`Contributor` to any identity.

## Success Criteria

- [ ] `terraform apply` provisions the full stack (resource group, Container Apps env + backend app at `min_replicas=0`, Static Web App, Storage account + container with sample docs, managed identity, remote state; Key Vault + RBAC wiring deferred) with zero manual portal steps beyond the one-time bootstrap script
- [ ] `backend/Dockerfile` builds and the image runs correctly when pushed to GHCR as a public package, deployed with `LLM_MODE=off`
- [ ] Frontend (built via `npm run build`) is live on the Static Web Apps free tier and successfully calls the backend (`/health`, `/samples`, `/audit`) with CORS restricted to its own origin
- [ ] No API key, connection string, or storage key appears anywhere in plaintext (repo, Terraform state, container app config, or logs)
- [ ] Terraform state lives only in the remote Azure Storage backend — a clean checkout + `terraform init -backend-config=backend.hcl` reaches the existing state with no `.tfstate` file ever appearing in the working tree
- [ ] `terraform destroy` removes every resource created by the main config; `az resource list -g <rg>` returns empty afterward (state-backend RG from the bootstrap script is intentionally separate and outlives individual destroys)
- [ ] Confirmed idle replica count reaches 0 after the Container Apps cooldown window
- [ ] Monthly cost estimate above is validated against the actual Azure Cost Management view after a few days running
- [ ] A Mermaid architecture diagram exists at `docs/architecture-azure.md` and is linked from the README

## Open Questions

All architecturally-significant questions are resolved. Two small items are finalized below by default per the recommendations already in this spec — flag now if either should be different, otherwise Plan proceeds with these:

1. **Environments:** single `prod`-only (no dev/prod split) — finalized.
2. **`max_replicas = 2`** as the cost/abuse cap alongside `min_replicas = 0` — finalized.
3. **Cost Management budget alert** at $5/month threshold — finalized.
