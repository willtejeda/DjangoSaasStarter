# Stack Analysis: Django + React + Clerk + Supabase (+ Resend)

Django REST API backend, React frontend, Clerk for auth/billing, Supabase as Postgres control plane, and Resend for outbound lifecycle email.

---

## Why This Stack Works

| Choice | Why It Works |
|---|---|
| **Django as API + ORM** | Excellent ORM, migrations, admin panel, battle-tested ecosystem. DRF makes building APIs clean. |
| **React frontend** | Industry standard, massive ecosystem, pairs naturally with any REST/GraphQL API. |
| **Clerk for auth + billing** | Removes the most painful parts of SaaS (auth flows, session management, Stripe integration). Huge time saver. |
| **Supabase as DB** | Managed Postgres with a great dashboard, built-in RLS, realtime subscriptions, and a generous free tier. |
| **Resend for email** | Simple transactional API for order and booking lifecycle communication. |

---

## The Architectural Tension: Django ORM + Supabase

Two overlapping data layers exist:

1. **Django ORM** - wants to own the schema via `backend/api/models/` + `makemigrations` + `migrate`
2. **Supabase** - also wants to own the schema via its dashboard/migrations, and provides its own PostgREST API, auth, and RLS

### Resolution

Django owns the schema. Supabase provides the managed Postgres hosting + RLS when you need per-user row isolation.

- Django ORM handles migrations and model management → connects to Supabase Postgres via `DATABASE_URL`
- Supabase Python client is used only for RLS-scoped queries (forwarding the Clerk JWT)

> [!IMPORTANT]
> **Schema ownership must be clear.** Django runs `makemigrations` / `migrate` against Supabase Postgres. Do not create tables through the Supabase dashboard if Django needs to manage them.

### Deployment posture

A practical default for cost and control:

- Self-host Django/frontend through Coolify
- Self-host or managed-host Supabase depending budget and ops constraints
- Keep external dependencies minimal (Clerk and Resend)

---

## Alternatives Considered

| Alternative | Trade-off |
|---|---|
| **Drop Django, use Next.js API routes** | Simpler stack (one language), but you lose Django's ORM, admin panel, and mature ecosystem. Only makes sense if your backend is thin. |
| **Drop Supabase, use managed Postgres directly** (Neon, Railway) | Removes the "two data layer" tension entirely. You lose Supabase's dashboard/RLS/realtime, but Django ORM replaces most of it. |
| **Drop Django, go full Supabase** (PostgREST + Edge Functions) | Minimal backend code, but locked into Supabase's ecosystem and lose Python. |
| **FastAPI instead of Django** | Faster async, better type hints, but you lose Django's admin, mature ORM migrations, and ecosystem breadth. |

---

## When This Stack Is the Right Call

- You want Python on the backend (mature, lots of libraries, AI/ML friendly)
- You need a structured ORM with proper migrations (Django's is best-in-class)
- You want to move fast on auth/billing (Clerk eliminates weeks of work)
- You want managed Postgres without DevOps (Supabase)
- Your frontend needs to be dynamic/interactive (React)

---

## Implementation Notes

### Django ↔ Supabase
- `backend/api/models/` defines schema, Django runs migrations against Supabase Postgres
- Supabase Python client used for RLS-scoped queries only
- Service-role key available for server-side operations that bypass RLS

### Clerk ↔ Django
- Custom DRF authentication backend verifies Clerk JWTs via JWKS (RS256/ES256/EdDSA)
- Supports both `Authorization: Bearer <token>` and `__session` cookie
- Clerk Backend SDK (`clerk-backend-api`) enables server-side user lookup and metadata management
- Svix library verifies webhook signatures

### Clerk ↔ React
- Use `@clerk/clerk-react` SDK on the frontend
- `useAuth()` hook provides JWT tokens to send to Django API
- Clerk handles login/signup UI, session management, and billing portal

### Supabase RLS + Clerk
- Forward Clerk JWT to Supabase PostgREST via the Python client
- RLS policies reference `auth.jwt() ->> 'sub'` to match Clerk's `sub` claim

---

## Verdict

> **This is a strong, production-ready stack for SaaS products.** The Django + Supabase combo requires a clear decision on schema ownership (Django), and the starter template handles this correctly. Clerk removes the hardest infrastructure problems. React is the safe frontend choice. Ship it.
