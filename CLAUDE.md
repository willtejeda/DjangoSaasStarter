# Claude Code Notes

Read `./AGENTS.md` first.

Use webhook-first payment fulfillment.
Do not enable direct client payment confirmation in production.

Run before handoff:

```bash
cd ./backend && DB_NAME='' DB_USER='' DB_PASSWORD='' DB_HOST='' DB_PORT='' DATABASE_URL='sqlite:///local-test.sqlite3' python3 manage.py test api -v2 --noinput
cd ./frontend && npm run build
```
