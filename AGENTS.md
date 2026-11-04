# SNP (Smart Nutritionist Program) — Codex Agent Instructions

## Project context
- This repository is the Django-based Smart Nutritionist Program (SNP), a graduation capstone supporting a dietitian's meal planning, recipes, headcount forecasting, procurement, goods inspection, inventory, reporting, and cooking instructions.
- The active integration checkout is `/home/woohyeak/sprint7-integration` on branch `integration/sprint7-kanghoon`. Verify the actual working directory, branch, and Git status before every substantial task; do not assume these remain unchanged.
- `/home/woohyeak/sprint7` is the original Sprint 7 checkout and must remain unchanged unless the user explicitly authorizes otherwise.
- The existing services `my-capstone` (host port 8000) and `my-capstone-sprint7` (host port 8007) are not deployment targets without explicit approval.

## Priority and source of truth
1. Explicit instructions in the current user request.
2. Current, versioned requirements and acceptance criteria in `docs/reference/` and `docs/analysis/`, when present.
3. Real dietitian feedback and actual example documents, interpreted as user-provided requirements or examples as appropriate.
4. Existing code and tests, including functionality from both Sprint 7 and the Kanghoon integration.
- Do not assume an item marked `완` in historical feedback still works. Verify it against the integrated code.
- Do not invent details from missing or truncated documents. Report ambiguities and unsupported assumptions.
- Reference documents and example spreadsheets are read-only inputs, not production seed data.

## Non-negotiable safety boundaries
- Never edit the original `~/sprint7` checkout, existing production-like containers, attached databases, Docker volumes, or networks without explicit user authorization.
- Never execute destructive supplier-reset commands, including `reset_and_assign_suppliers`, against real data.
- Never run `flush`, destructive migrations, bulk deletion, or database reset against existing databases.
- Do not push to remotes, create PRs, or deploy without explicit approval.
- Use isolated databases, ephemeral containers, and temporary ports for verification. Clean up only resources created by the current task.
- Preserve user changes. Inspect `git status` before editing; do not reset, overwrite, or discard uncommitted work.
- Keep `docs/reference/` unchanged and out of commits unless the user explicitly asks to version those documents.
- Never commit credentials, `.env`, database dumps, or sensitive operational data.

## Engineering principles
- Preserve existing Sprint 7 and Kanghoon features, including `release_patch_views` routes and upload, inventory-deduction, dashboard, and procurement behaviors.
- Prefer targeted changes with regression tests. Avoid replacing working flows wholesale or silently changing business rules.
- Maintain consistency across Django models, services, views, URLs, templates, navigation, and migrations.
- Use decimal-safe arithmetic, explicit units, transaction boundaries, idempotency safeguards, and input validation for procurement, inspection, and inventory.
- Distinguish predicted headcount, manually entered headcount, and final confirmed headcount. Do not silently substitute one for another.
- Convert required ingredient quantities to purchase packages only with explicit supplier/product specifications. Do not infer a package weight from free-text labels; report missing or incompatible specifications.
- Check Friday/weekend procurement grouping, repeated ingredients, safety-stock double counting, inspection acceptance quantities, stock movements, and duplicate submissions.
- Do not treat a weekly recipe report, procurement plan, and cooking instruction sheet as interchangeable documents.
- Cooking instruction examples are formatting/workflow references, not fixed quantities or production data.
- Keep AI forecasting model files and compatible dependencies intact; verify model loading/inference when changing related code.

## Verification and reporting
- Start with a concise plan and inspect existing code/tests before changes.
- Where practical, run `manage.py check`, `makemigrations --check --dry-run`, isolated migration tests, Django unit/integration tests, and relevant browser/export tests.
- Report exact commands, pass/fail counts, and limitations. Never claim success for unexecuted tests.
- Keep requirement traceability and implementation notes in `docs/analysis/` up to date when changing document-driven features.
- Report what changed, what was preserved, unresolved issues, migration implications, and what needs explicit approval before deployment.
- If a task is too large, finish and verify a coherent subset, then list remaining items; do not loop indefinitely or repeatedly rerun unchanged suites without a reason.
