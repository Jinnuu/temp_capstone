# Nutritionist hardening — Phase 0/1 evidence

2026-11-06 KST, starting commit3ad73a8, UI redesign branch only. Reports: `docs/analysis/NUTRITIONIST_IMPLEMENTATION_REPORT.md`, `NUTRITIONIST_TEST_REPORT.md`, `NUTRITIONIST_OPERATION_READINESS.md`.

## Isolated execution

`run_tests.sh` reuses the existing Preview dependency image with the **current checkout mounted read-only**, not the deployed source. No image rebuild or Preview deployment is performed. It checks Django/migration drift, migrates a disposable database and runs all tests. Source/requirements/models remain compatible with the preserved runtime.

The task created its own network `snp-hardening-tests-20261106`, tmpfs MariaDB alias `auth-db`, Redis alias `auth-cache`, and a loopback Gunicorn/Nginx test app on18021. It never connected the test database to a production network/socket. Database credentials exist only in the ignored private task env file, not in this evidence directory. Test sources contain clearly synthetic fixture passwords; they are not public Preview credentials and must not be reused outside isolated tests.

To reproduce after cleanup, explicitly recreate the task resources (never substitute the Preview DB):

1. Inspect Docker resources/ports and require the test names/network to be unused. Create a new task-labelled network.
2. Generate a random `AUTH_TEST_DB_PASSWORD` into a0600 file under the private task audit directory; do not print its value.
3. Run MariaDB10.6 on that network with aliasauth-db and tmpfs`/var/lib/mysql`, the private env file, and an entrypoint that exports its random value to MARIADB_ROOT_PASSWORD before the image entrypoint. Wait for readiness and create only test database`snp_auth_verification`.
4. Run Redis7 on that network with aliasauth-cache, disabled persistence and no published port. Override inherited Compose project labels on containers using the dependency image; task ownership is additionally labelled`snp.task=nutritionist-hardening-20261106`.
5. `bash verification/nutritionist-hardening-20261106/run_tests.sh` and the same command with`config.auth_mysql_test_settings`.
6. For browsers, start the task-only app with`config.auth_test_settings`,`PYTHONPATH=/workspace`, tmpfs`/tmp`, source mount/read-only synthetic AI data mount, own Redis namespace, migrate the disposable SQLite, and run the existing guarded`verification/fresh-portal-20261105/seed_isolated.py`. Gunicorn uses`--no-control-socket`; Nginx serves checkout static assets, binding only127.0.0.1:18021. Use the fixture and browser commands in the test report. The hardening seed additionally requires explicit`SNP_HARDENING_BROWSER=1`.
7. Stop/remove only containers with this task label and names you just created, including their anonymous volumes; remove the empty task-owned network. Keep private diagnostic files/credentials out of Git.

`cleanup.json` records resources actually removed. The final repository does not start test servers automatically. Fixed scenario dates require deliberate fixture refresh for future runs; do not remove delivery-date validation to keep an old fixture passing.

## Evidence map

- `p0-before.log` / `p0-after.log`:18 original reproductions before/after.
- `admin-before.log`: missing bootstrap/rename tools before implementation,12 synthetic contracts.
- `targeted.log`: intermediate39 passing tests, not final total.
- `admin-ui-before.log`, `empty-month-before.log`, `delete-audit-before.log`: concrete additional failures subsequently fixed. Full HTML responses that could carry temporary CSRF tokens are omitted.
- `*-setup-failure.log`, `*-permission-failure.log`, `browser-setup.log`: test infrastructure issues preserved, not successful functional runs.
- `sqlite-305.log` / `mariadb-305.log`, `*-307.log`: earlier successful suite snapshots. Use `*-final.log` for final counts.
- `javascript.log`, `frontend-build.log`: JS10 and TypeScript/Vite build.
- `business-green/`:21-checkpoint dietitian workflow, real UI input/download/print. Scenario source is reused from the fresh-portal evidence directory via explicit base/output environment variables.
- `browser-portal.json` / `portal-screenshots/`:12-checkpoint supplier/admin workflow,36 screenshots.
- `browser-hardening.json`:8 new P0/UI checks, actual form/CSRF requests and report download.
- `accessibility-smoke.json`:2mode dashboard smoke checks using **CSS zoom**, not native zoom/WCAG/user acceptance.
- `stock-consistency.json`: task SQLite stock/lot totals for4synthetic ingredients match and are nonnegative.
- `preview-preflight.json`, `preview-after.json`: authorized non-sensitive actual account summaries; actual rename/policy change not performed.
- `containers-before.json`, `containers-after.json`, `protection.json`: protected container identities/images/start times/mounts/networks. Docker Mounts array order is normalized by destination; initial false order comparison retained in `protection-initial.json`.

Public login GET returns200 with curl; Python urllib got403. The cause of the client-dependent response was not diagnosed and is not described as an application/authentication success. No new public-browser login or deployment was performed. Original8000/8007/8010 login pages returned200.

Screenshots deliberately include synthetic QA/XSS regression strings as escaped text. They are engineering evidence, not cleaned presentation/customer master data. Do not represent them as actual dietitian acceptance or production data.
