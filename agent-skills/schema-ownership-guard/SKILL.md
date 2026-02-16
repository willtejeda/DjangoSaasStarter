---
name: schema-ownership-guard
description: Use when models or migrations change to ensure Django remains schema source of truth.
---

# Schema Ownership Guard

## Workflow

1. Inspect changed files under `backend/api/models/` and `backend/api/migrations/`.
2. Ensure schema changes are represented in Django migrations.
3. Reject plans that require manual table edits in Supabase dashboard for Django-managed tables.
4. Verify migration application in local environment.

## Output contract

Return:

- model files changed
- migration files changed
- missing migration warnings
- safe next migration command

## Validation

- `cd backend && python3 manage.py makemigrations --check --dry-run`
- `cd backend && python3 manage.py migrate --plan`
