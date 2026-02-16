# 07 Agent Skills Playbook

Goal: create skills that help agents ship revenue-critical work safely.

## Skill quality bar

Each skill should:

1. Have a narrow trigger condition
2. Produce a concrete artifact
3. Include validation commands
4. Respect payment and schema contracts
5. Be easy to delete or replace

## Skill structure

- `SKILL.md` with:
  - trigger
  - inputs
  - steps
  - output format
  - validation checks
- Optional reference files for long examples
- Optional script folder for repeatable commands

## Good skill patterns for this repo

- Revenue loop audit
- Schema ownership guard
- Frontend-backend contract checker
- Preflight validator
- Offer copy optimizer
- Onboarding funnel analyzer

## UX-first authoring checklist

Before finalizing a skill, answer from beginner viewpoint:

1. What button or endpoint do I touch first?
2. What should happen next if it works?
3. What failure message should I expect?
4. What is the one command to confirm success?

## Example validation block

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput

cd /Users/will/Code/CodexProjects/DjangoStarter/frontend
npm run build
```

## Keep skills outcome-focused

Bad: "Refactor models"

Good: "Add usage limit model for image generation and expose summary API with tests"

## Related files

- `/Users/will/Code/CodexProjects/DjangoStarter/agent-skills/README.md`
- `/Users/will/Code/CodexProjects/DjangoStarter/AGENTS.md`
