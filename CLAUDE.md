# Claude Code Notes

Read `/Users/will/Code/CodexProjects/DjangoStarter/AGENTS.md` first.

Core rules:

1. Webhook-first payment fulfillment in production.
2. Django owns schema and migrations.
3. Keep non-essential demos in `/frontend/src/features/examples/`.
4. Verify `/app` preflight before feature work.

Run before handoff:

```bash
cd /Users/will/Code/CodexProjects/DjangoStarter/backend
DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
DJANGO_DEBUG=False DJANGO_SECRET_KEY='replace-with-a-64-char-random-secret-key-value-example-1234567890' python3 manage.py check --deploy

cd /Users/will/Code/CodexProjects/DjangoStarter/frontend
npm run build
```
