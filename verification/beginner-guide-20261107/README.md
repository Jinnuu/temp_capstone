# Beginner guide verification — 2026-11-07

Baseline2c4106f; branchfeature/ui-redesign-three-modes. Actual Preview and services are unchanged. All browser users are synthetic. No fake meal/order/stock fixtures or automatic practice-mode business data were added.

Evidence:
- before.log:new required titles test fails before implementation.
- sqlite.log:365discovered/358pass/7skip. mariadb.log:365pass. Includes previous361cases plus4beginner requirements tests. Backend business code and migrations unchanged.
- tutorial-final.log:20tutorial tests pass after final wording change.
- javascript.log:19pass (17existing+2legacy-state/non-completion regressions).
- frontend-build.log:TypeScript/Vite successful final build.
- browser-initial.log:mobile navigation min-height failure caused by older global style specificity; fixed tutorial-only scope. No lowered expected height.
- browser-final.log/browser-results.json:12checkpoints, no page errors/500responses. All6steps, actual work GET links/back navigation, old v1 reading state/reset, keyboard,3modes/mobile, limited roles, denied supplier, blocked localStorage and JS-disabled fallback.
- screenshots/:9synthetic screenshots, desktop1920x1080 and full-page mobile390px.
- business-before/after.json +business-preservation.json:26business models' row counts and hashes unchanged (all empty fixtures); no business POST requests from guide/primary work-link visits. Login/session writes only in this isolated DB.
- services-before.json/services-protection.json:8existing containers' identity/image/start/mount/ports unchanged.
- cleanup.json:only current task-owned resources removed.

Isolation:task label beginner-guide-20261107, network snp-beginner-tests-20261107, tmpfs MariaDB10.6 aliasauth-db and Redis7 aliasauth-cache, source mount/workspace read-only, existing dependency image snp-ui-preview-web:tutorial-20261106, no production secrets. Private random AUTH_TEST_DB_PASSWORD only in ignored .ui-preview/audit/beginner-guide-20261107/test-db.env.

Reproduction requires a fresh isolated network/DB/cache with these aliases and schema snp_auth_verification (Django creates separate test_snp_auth_verification). Do not point aliases/settings at the actual Preview DB.

```sh
bash verification/beginner-guide-20261107/run_tests.sh config.test_settings
bash verification/beginner-guide-20261107/run_tests.sh config.auth_mysql_test_settings
npm --prefix frontend run build
node --test frontend/tests/*.test.mjs integration_tests/smart_order.test.cjs
```

Browser:separately task-labelled test container, PYTHONPATH=/workspace, config.auth_mysql_test_settings, loopback18051 only. Migrate the fresh task schema, execute seed_browser.py once, then run test-only Django runserver --noreload --insecure 0.0.0.0:8000. Run business_snapshot.py before/after, and node browser-guide.cjs. This test server is not an external deployment recipe. seed_browser.py asserts task DB hostname/schema and refuses duplicate synthetic accounts. Browser progress can be reset, no real work rows should be created.

Read docs/analysis/NUTRITIONIST_BEGINNER_TUTORIAL.md for teaching copy, limitations, deployment separation and unperformed1–2beginner participant test plan. Automation is not user acceptance or evidence that users actually finish within5–10minutes. Underlying Phase2-A remains un-deployed; no new delivery routes are promoted in guide content.
