# Engineering Standards

## Git workflow
- Trunk-based development: short-lived feature branches, PRs into `main`. Never push directly to `main`.
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`.
- No commit without a passing test suite.
- Keep commits under ~100 lines where practical.
- Do not add `Co-Authored-By` trailers to commits.

## Testing
- Test-driven: write the failing test first, then the implementation.
- Screenshot the rendered result before declaring UI work done — green tests are not proof the page looks right.

## Security
- No secrets in the repo, ever. Environment variables and Key Vault only.

## Infrastructure
- Terraform state is gitignored.
- Every resource must be destroyable.
- Cost is a first-class constraint: give a monthly estimate before building.

## Dependencies
- Do not add a dependency without asking first.

## Ponytail (lazy = efficient, not careless)
- Ponytail is active: climb the YAGNI ladder before writing anything.
- Lazy means efficient, not careless. IaC, tests, and honest negative results are never the thing to cut.
