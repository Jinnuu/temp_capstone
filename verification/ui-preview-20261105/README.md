# Docker preview evidence

All business records are synthetic and live in the separate `snp-ui-preview` Compose project. Existing operational DBs were never opened.

- `flow/initial-progress.json`: seven passed setup/CRUD checkpoints before a missing prediction CSV was detected.
- `flow/initial-attempt.*`: retained failed first attempt; not counted as passing AI.
- `flow/browser-result.json`: fifteen remaining business checkpoints passed after adding synthetic prediction history, without resetting the DB.
- `ui/ui-result.json`: 16 UI checkpoints, three modes, real proxy/static serving and preview MariaDB.
- `db-*-restart.json`: row counts/digests only for synthetic business tables; no rows or credentials exported.
- `restart-*.json`: existing cookie session, green mode and ledger survived restarting these three services.
- `protection-final.json`: compare original container IDs/images/mounts/networks/PIDs/start timestamps plus existing/new HTTP endpoints.
- `image-content.json`: runtime asset/model/content checks, no inherited legacy app environment/data.
- `ai-final-image.json`: additional real inference through the final image. Synthetic input, no accuracy claim.

Local raw Docker inventory and session/secret files remain under ignored `.ui-preview/`, not in Git. `check_protection.py` needs that private audit directory to rerun. Browser wrappers load the ignored random demo password; they never embed it in code or log it.

The full business generator is for an empty isolated DB only. Do not rerun it against this populated service. UI-only checks can be repeated:

```sh
SNP_BROWSER_BASE=http://127.0.0.1:8011 node verification/ui-preview-20261105/browser-ui-preview.cjs
```

See `docs/ui-redesign/DOCKER_PREVIEW_TEST_REPORT.md` for environment, commands, warnings and limitations.
