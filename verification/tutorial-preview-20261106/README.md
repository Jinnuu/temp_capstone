# Tutorial + approved Preview rollout evidence

2026-11-06 KST, starting HEAD3236e07, feature/ui-redesign-three-modes. Only the user-approved Preview deployment, PK1 username transition and public-signup approval opt-in changed live state. No remote push, stable branch merge, real-user login, password change, actual order/inspection/inventory mutation or schema change.

## New execution results

- Candidate image: `snp-ui-preview-web:tutorial-20261106`, proxy equivalent. Verified candidates are also tagged `three-modes` for the regular Preview Compose entrypoint. Old images retain `pre-tutorial-3236e07` tags.
- SQLite325 discovered:321pass/4row-lock skips. MariaDB325pass. Same325cases repeated, not650unique cases. Existing309+new16.
- JavaScript17pass:existing10+reading-progress7; TypeScript/Vite build passes.
- business21, portal13, guide15 checkpoints are3workflow scenarios, not additional Django cases. Public anonymous read-only7checkpoints are separate.
- Guide images: screenshots/{green,civic,reference}-guide-{desktop,mobile}.png. Portal screenshots cover Green/Civic9screens×2viewports. Public screenshots show empty anonymous signup forms, never real credentials.

## Isolation and reproduction

`run_tests.sh` uses the candidate dependency image with current source mounted read-only, task network`snp-tutorial-tests-20261106`, tmpfs MariaDB`snp-tutorial-db-20261106` aliasauth-db, tmpfs Redis`auth-cache`, and settings config.test_settings/config.auth_mysql_test_settings. Credentials are only in ignored private task env, never logs/Git. It runs check, drift, migrate/check and full tests.

The task browser app used a separate SQLite`/tmp/sprint7-integration.sqlite3`, private browser_settings derived from auth_test_settings (public approval opt-in true), explicit task Compose labels, source/synthetic AI-data read-only mounts, Gunicorn `--no-control-socket` and Nginx bound127.0.0.1:18031. All accounts/password literals in isolated scripts are synthetic test fixtures, never actual Preview credentials. The guarded prior seed created fixtures; the rename command changed only the synthetic root toadmin before browser tests. seed_guide adds preapproved synthetic roles only in that SQLite.

Reproduction after cleanup requires creating new task-labelled resources with unused names/ports and a new random private test credential; do not connect these settings/aliases to the real Preview DB. Candidate runs:

```sh
bash verification/tutorial-preview-20261106/run_tests.sh
bash verification/tutorial-preview-20261106/run_tests.sh config.auth_mysql_test_settings
npm --prefix frontend run build
node --test frontend/tests/*.test.mjs integration_tests/smart_order.test.cjs
SNP_BROWSER_BASE=http://127.0.0.1:18031 SNP_TEST_MODE=green \
 SNP_UI_EVIDENCE_DIR=verification/tutorial-preview-20261106/business \
 node verification/tutorial-preview-20261106/business-flow.cjs
node verification/tutorial-preview-20261106/browser-portal.cjs
# After guarded task-only seed_guide
node verification/tutorial-preview-20261106/browser-guide.cjs
# Anonymous GET/mode changes only; no real user auth or registration
node verification/tutorial-preview-20261106/browser-public-readonly.cjs
```

The database backup/restore/deployment scripts are **not a test-suite setup routine**. They require explicit Preview operation authorization and verified host/name boundaries. Do not rerun rename/seed/deploy against real data merely to reproduce tests. Fixed fixture dates need deliberate refresh for future runs; keep business validation intact.

## Backup, account identity and service evidence

- db_snapshot.py outputs table-level fingerprints/counts only. Full SQL backup, env original, secret comparisons and sensitive snapshots remain private and excluded from image/Git.
- backup-verification.json:latest backup,37source/restored tables match; restore_rehearsal.py tests rename, existing attributes, seed and reverse rename only inrestore_check.
- deployment-gates.json:all test/backup gates passed and live data still matched latest backup before changes.
- rename-dry-run.log/rename-apply.log:actual approved CLI operations, no passwords. Exactly one account.username_changed event added.
- data-preservation.json:9accounts, samePK1/credentials/flags/groups/links, all existing rows preserved after normalizing only the approved username and excluding the added audit row.
- live-readonly.json:deployed source/assets match checkout, actual admin/approval settings, authorized views rendered with in-memory RequestFactory, never login/session save.
- readonly-seed-after-rename.json:actual deployed seed rerun with SQL mutations blocked before execution;12SELECT,0writes, noverify-admin recreation.
- service-protection.json:original8000/8007/8010+Preview DB/cache unchanged; only web/mail/proxy replaced;5healthy. cleanup.json records only task-owned temporary resource removal.

## Initial failures and scope

`tutorial-before.log` records the missing routes/guide assertions before implementation;`signup-copy-before.log` records incorrect immediate-login copy under approval opt-in. `guide-js-before.log` shows absent progress module; frontend-build-before.log shows a closure nullability type error fixed before candidate build. Original response bodies with temporary CSRF markup are omitted, not committed.

Public harness first searched for text inside a collapsed supplier details element. The visible header was correct; radio selection reveals the supplier-specific approval explanation. Later it misclassified Cloudflare `/cdn-cgi/rum` analytics POST as application writes. Path-only diagnostics confirmed that endpoint; final harness blocks that telemetry in its own browser and still rejects every application mutation. It did not change Cloudflare/tunnel/server settings. Final public browser result is7pass with0application mutations and no real account authentication/signup.

This is not actual dietitian acceptance, full load/penetration/accessibility certification or proof of real SMTP delivery. Phase2 exception workflows remain design-only, as stated in the three new analysis reports.
