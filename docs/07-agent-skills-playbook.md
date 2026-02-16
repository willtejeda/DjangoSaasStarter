# 07 Agent Skills Playbook

Goal: define how to build reliable project-specific skills and agent instructions for this repo.

## What research says works

These patterns were used to design the recommendations in this file:

- OpenAI Agents Python docs emphasize explicit instructions plus guardrails for tool safety and predictable behavior.
  - https://github.com/openai/openai-agents-python
- OpenAI Cookbook examples show better outcomes when prompts include strict output contracts and evaluation loops.
  - https://github.com/openai/openai-cookbook
- Codex `skill-creator` guidance emphasizes concise skills, progressive disclosure, and reusable scripts.
  - `/Users/will/.codex/skills/.system/skill-creator/SKILL.md`

## Skill design rules for DjangoStarter

1. Keep trigger descriptions specific.
2. Define exact outputs and acceptance criteria.
3. Use deterministic scripts for fragile tasks (migrations, fixtures, test orchestration).
4. Keep `SKILL.md` short, move long references to `references/`.
5. Include safety checks that enforce project non-negotiables.
6. Add an eval step at the end of each skill workflow.

## Non-negotiables every skill must enforce

- Do not bypass webhook-based payment truth in production.
- Keep Django as schema owner.
- Keep production flags safe:
  - `ORDER_CONFIRM_ALLOW_MANUAL=False`
  - `ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM=False`
- Run quality gates before completion:
  - `python3 manage.py test api -v2 --noinput`
  - `python3 manage.py check --deploy`
  - `npm run build`

## Skill template

```md
---
name: skill-name
description: When this skill should trigger and what it produces.
---

# Skill Name

## Inputs expected
- ...

## Workflow
1. ...
2. ...
3. ...

## Output contract
- ...

## Validation
- command 1
- command 2
```

## Project skills included in this repo

- `agent-skills/revenue-loop-audit/SKILL.md`
- `agent-skills/schema-ownership-guard/SKILL.md`
- `agent-skills/frontend-backend-contract/SKILL.md`
- `agent-skills/preflight-validator/SKILL.md`

## How to use these skills

1. Copy selected folders to your Codex skills directory (`$CODEX_HOME/skills`).
2. Keep names and descriptions short and explicit so trigger matching works.
3. Run each skill on a real task, then tighten ambiguous wording.
4. Keep only reusable workflow logic in skills. Keep product specifics in repo docs.

## Fast QA checklist for new skills

- Trigger sentence is clear and narrow.
- Output format is explicit.
- Safety checks are present.
- Workflow references real repo paths.
- Validation commands run successfully.
