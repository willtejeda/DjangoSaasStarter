# DjangoStarter Docs Wiki

Use this folder as the project wiki for operators, product builders, and coding agents.

## Read in order

1. `01-quickstart.md`
2. `02-first-revenue-loop.md`
3. `03-api-cheatsheet.md`
4. `04-troubleshooting.md`
5. `05-customize-template.md`
6. `06-resend-transactional-email.md`
7. `07-agent-skills-playbook.md`
8. `StackAnalysis.md`

## Quick links

- Root guide: `README.md`
- Agent contract: `AGENTS.md`
- Backend API map: `backend/api/README.md`
- Backend tools map: `backend/api/tools/README.md`
- Frontend map and examples: `frontend/src/README.md`
- Backend env reference: `backend/.env.example`
- Frontend env reference: `frontend/.env.example`

## Operating principles

- Django is the schema owner.
- Clerk webhooks are the payment truth in production.
- Resend is best-effort transactional delivery.
- Keep modules deletable and composable so this stays a real starter.

## Quality gates before shipping

```bash
cd backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd ../frontend
npm run build
```
