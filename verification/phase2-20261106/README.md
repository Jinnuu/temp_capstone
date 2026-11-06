# Phase 2-A isolated verification — 2026-11-06

Source baseline2d3ac0b, branchfeature/ui-redesign-three-modes. Only additive delivery/receipt functionality in this milestone; no actual Preview deployment.

- sqlite-final.log:361discovered,354pass/7skip; mariadb-final.log:361pass. The325existing cases are included, not added again.
- sqlite-targeted.log:31new functional tests pass. Final suites include3additional MariaDB row-lock races +2migration preservation/rollback guards.
- javascript.log:17pass.
- browser-results.json:10checkpoints, genuine Chromium form entry/save/reload on task-only MariaDB. browser-data-consistency.json:105delivered/100accepted/5rejected/0remaining/100stock,3receipts/3IN logs/lots100.
- screenshots/:9synthetic-only PNGs, three modes, desktop buyer/supplier and mobile buyer.
- services-before.json/services-protection.json:8existing containers have identical identity/image/start/mount/port metadata. Docker mounts are compared after sorting by destination because inspect order is not stable.
- preview-schema-readonly.json/preview-schema-after.json:live Preview SELECT/read-only schema/counts only, no new delivery tables. Counts unchanged; not a full row-content hash.
- cleanup.json:only this task's containers/network were removed, leaving the existing Preview and other services running.

Initial failures are retained: sqlite-initial.log has28fixture errors (missing required order_unit_price) while321existing cases pass/4skip. Production schema was not weakened. browser-initial.log is an incorrect text locator timeout, fixed to the actual rendered href. The first task browser startup needed PYTHONPATH=/workspace; no real service setting changed.

## Reproduce safely

`run_tests.sh` expects a fresh task-owned network snp-phase2-tests-20261106, isolated MariaDB10.6 aliasauth-db, schema snp_auth_verification, Redis7 aliasauth-cache and ignored private env `.ui-preview/audit/phase2-20261106/test-db.env` containing a new random AUTH_TEST_DB_PASSWORD. Never copy production secrets/data or resolve auth-db to a real service. Both DB/cache used tmpfs, no existing volumes.

```sh
bash verification/phase2-20261106/run_tests.sh config.test_settings
bash verification/phase2-20261106/run_tests.sh config.auth_mysql_test_settings
node --test frontend/tests/*.test.mjs integration_tests/smart_order.test.cjs
```

For browser verification start a separately labelled, source-read-only, PYTHONPATH=/workspace container with config.auth_mysql_test_settings and loopback18041. Run migrations only on that empty task schema, execute seed_browser.py once (DB host/schema assertions), then `manage.py runserver --noreload --insecure 0.0.0.0:8000` only for isolated verification. This is not a deployment recommendation. Run browser-deliveries.cjs with installed Playwright at/tmp/snp-browser and Chromium1223, then runcheck_browser_data.py via task container. The script's business writes must not be rerun against the already-completed fixture; use a new empty isolated task DB.

readonly_schema.py is deliberately metadata/SELECT-only; it was executed in the actual Preview web container under a read-only DB transaction, without login/session/seed/account/password writes. Do not generalize that approval to mutating commands.

No actual SMTP, load, comprehensive accessibility or dietitian/supplier acceptance proof. Order cancellation/corrections/physical returns/document versions are not implemented in this milestone. Read the three new Phase2 analysis reports before interpreting evidence.
