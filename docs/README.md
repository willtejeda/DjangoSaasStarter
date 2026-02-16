# DjangoStarter Wiki

This is the working wiki for builders, operators, and AI agents.

## Read this first

- `/Users/will/Code/CodexProjects/DjangoStarter/README.md`
- `/Users/will/Code/CodexProjects/DjangoStarter/AGENTS.md`

## Wiki order

1. `/Users/will/Code/CodexProjects/DjangoStarter/docs/01-quickstart.md`
2. `/Users/will/Code/CodexProjects/DjangoStarter/docs/02-first-revenue-loop.md`
3. `/Users/will/Code/CodexProjects/DjangoStarter/docs/03-api-cheatsheet.md`
4. `/Users/will/Code/CodexProjects/DjangoStarter/docs/04-troubleshooting.md`
5. `/Users/will/Code/CodexProjects/DjangoStarter/docs/05-customize-template.md`
6. `/Users/will/Code/CodexProjects/DjangoStarter/docs/06-resend-transactional-email.md`
7. `/Users/will/Code/CodexProjects/DjangoStarter/docs/07-agent-skills-playbook.md`
8. `/Users/will/Code/CodexProjects/DjangoStarter/docs/08-security-pass-phase-1.md`
9. `/Users/will/Code/CodexProjects/DjangoStarter/docs/09-agent-frameworks-2026.md`
10. `/Users/will/Code/CodexProjects/DjangoStarter/docs/StackAnalysis.md`

## Philosophy

- Monetization first
- Integration proof before feature depth
- Server-side payment truth
- Schema ownership clarity
- Modular code that users can delete safely

## Minimum success criteria

A user can clone the repo, run preflight checks, complete one paid order, verify fulfillment, and send one transactional email.

## Quality gates

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd /Users/will/Code/CodexProjects/DjangoStarter/frontend
npm run build
```
