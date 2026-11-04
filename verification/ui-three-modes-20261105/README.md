# Experimental UI verification evidence

All records/accounts are synthetic and run inside task-owned ephemeral containers. No production DB was accessed. `flows/{reference,green,civic}/browser-result.json` each represents **one** full workflow scenario with 22 checkpoints, not 22 independent test cases. Those runs used the real existing AI models offline.

`browser-ui.cjs` separately checks switching, persistence, work-in-progress data, comparison, tablet layouts and print. It requires the populated task database from the full flow. UI screenshots are under `docs/ui-redesign/screenshots/`.

Rerun using a new isolated app, not existing services:

```sh
# Follow the isolated container setup in docs/ui-redesign/TEST_REPORT.md first.
SNP_BROWSER_BASE=http://TASK_IP:8000 SNP_TEST_MODE=reference \
  SNP_UI_EVIDENCE_DIR=verification/ui-three-modes-20261105/flows/reference \
  node verification/ui-three-modes-20261105/business-flow.cjs
SNP_BROWSER_BASE=http://TASK_IP:8000 node verification/ui-three-modes-20261105/browser-ui.cjs
```

Each business-flow run needs an empty ephemeral business database and the three account-only fixtures in `verification/comprehensive-20261104/seed_accounts.py`. Do not seed or reset an existing database. Prepare the two upload XLSX fixtures in the evidence directory before running. Playwright and Chromium paths in scripts reflect the installed local test tools and must be adjusted on another machine.

Earlier development attempts exposed a test timing race (wait for hidden unit fields after navigation) and Django's default iframe DENY policy. The final tests retain the business assertions and add limited SAMEORIGIN preview/header/auth regression tests. Connection-refused attempts during a server restart are not counted as passed tests. Final results, not partial browser-progress JSON, are authoritative.
