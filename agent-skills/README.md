# DjangoStarter Agent Skills

These are optional project-specific skill templates for coding agents.

## Included skills

- `revenue-loop-audit`: verify one paid loop from catalog to fulfillment.
- `schema-ownership-guard`: enforce Django migration ownership and safe DB workflow.
- `frontend-backend-contract`: keep UI payloads aligned with API contracts.
- `preflight-validator`: run signed-in preflight checks before feature work.

## Install pattern

Copy any folder into your local Codex skills directory:

```bash
cp -R agent-skills/<skill-name> "$CODEX_HOME/skills/<skill-name>"
```

Then restart Codex.
