# Security Best Practices Report

## Executive Summary

The project has a solid baseline for JWT verification and webhook signature validation, but it currently has one critical web security issue and several high to medium hardening gaps. The critical issue is CSRF exposure when API auth falls back to Clerk `__session` cookies without CSRF enforcement. If deployed without configuration hardening, the current defaults can also expose debug and cookie transport risks.

## Critical Findings

### [SEC-001] Cookie-based API auth bypasses CSRF protection on state-changing endpoints
- Severity: Critical
- Impact statement: An attacker-controlled site can trigger authenticated state changes in a victim account if the victim browser sends the Clerk session cookie.
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/authentication.py:63`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/project_settings/settings.py:152`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/urls.py:21`
- Evidence:
  - Cookie token accepted as auth source:
    - `cookie_token = request.COOKIES.get("__session")`
    - `if cookie_token: return cookie_token`
  - Only custom auth backend is configured:
    - `"DEFAULT_AUTHENTICATION_CLASSES": ("api.authentication.ClerkJWTAuthentication",)`
  - State-changing route exists:
    - `path("projects/", ProjectListCreateView.as_view(), name="project-list")`
  - Validation test performed with CSRF checks enabled and no CSRF token:
    - Command used APIClient(`enforce_csrf_checks=True`) with only `__session` cookie
    - Response status: `201`
- Impact:
  - CSRF is not enforced for the cookie-authenticated API flow.
  - Cross-site requests can perform actions like project creation if cookie policy allows transmission.
- Fix:
  - Preferred: disable cookie fallback for API auth and accept bearer JWT only.
  - Alternative: enforce CSRF validation whenever auth comes from `__session` cookie.
  - Keep state-changing API routes on token auth only if frontend can send bearer JWT.
- Mitigation:
  - Set restrictive cookie SameSite policy at Clerk and serve API on a separate subdomain with no ambient auth cookies.
  - Add origin checks for unsafe methods as defense-in-depth.
- False positive notes:
  - Risk depends on browser cookie behavior for your Clerk cookie settings, but the server currently has no CSRF backstop for this auth path.

## High Findings

### [SEC-002] Insecure-by-default runtime settings can lead to production compromise if env is missing
- Severity: High
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/project_settings/settings.py:13`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/project_settings/settings.py:14`
- Evidence:
  - `SECRET_KEY = config("DJANGO_SECRET_KEY", default="change-me-before-production")`
  - `DEBUG = config("DJANGO_DEBUG", cast=bool, default=True)`
- Impact:
  - Accidental deployment with defaults can leak stack traces and sensitive internals.
  - Weak/predictable secret can undermine signing-based security controls.
- Fix:
  - Fail closed on missing `DJANGO_SECRET_KEY` in non-dev environments.
  - Default `DJANGO_DEBUG` to `False` and require explicit opt-in for local dev.
- Mitigation:
  - Add startup checks that abort boot when `DEBUG=True` outside localhost.
  - Add CI policy to block deploy when env safety checks fail.
- False positive notes:
  - If your deployment pipeline always injects hardened env vars, exploitability is reduced, but template defaults remain risky.

## Medium Findings

### [SEC-003] TLS/cookie transport hardening settings are missing in app config
- Severity: Medium
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/project_settings/settings.py`
- Evidence:
  - `manage.py check --deploy` returned:
    - `security.W008` (`SECURE_SSL_REDIRECT` not True)
    - `security.W012` (`SESSION_COOKIE_SECURE` not True)
    - `security.W016` (`CSRF_COOKIE_SECURE` not True)
    - `security.W004` (`SECURE_HSTS_SECONDS` not set)
- Impact:
  - Session and CSRF tokens may traverse non-TLS paths if deployment edge is not enforcing redirect and secure cookie flags.
- Fix:
  - In production settings enable:
    - `SESSION_COOKIE_SECURE = True`
    - `CSRF_COOKIE_SECURE = True`
    - `SECURE_SSL_REDIRECT = True` (or enforce at edge with documented equivalent)
    - Evaluate `SECURE_HSTS_SECONDS` once HTTPS-only behavior is confirmed.
- Mitigation:
  - If TLS redirect is handled at ingress/CDN, document and test it in deployment checks.
- False positive notes:
  - Some controls can live at reverse proxy/CDN; verify runtime headers and redirect behavior.

### [SEC-004] JWT validation constraints are optional and can be too broad if omitted
- Severity: Medium
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/clerk.py:42`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/clerk.py:56`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/clerk.py:66`
- Evidence:
  - Audience verification only when configured:
    - `"verify_aud": bool(audience)`
  - Authorized party check only when configured:
    - `if authorized_parties: ...`
- Impact:
  - If `CLERK_JWT_AUDIENCE` and `CLERK_AUTHORIZED_PARTIES` are unset, tokens may be accepted more broadly than intended for multi-app Clerk setups.
- Fix:
  - Require `CLERK_JWT_AUDIENCE` and `CLERK_AUTHORIZED_PARTIES` in production.
  - Fail startup when these values are empty in production mode.
- Mitigation:
  - Keep separate Clerk instances per environment/app when possible.
- False positive notes:
  - Lower risk if a single Clerk app exists and strict key isolation is guaranteed.

### [SEC-005] CORS fallback can become overly permissive under debug with credentials
- Severity: Medium
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/project_settings/settings.py:146`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/project_settings/settings.py:148`
- Evidence:
  - `CORS_ALLOW_CREDENTIALS = ... default=True`
  - `if DEBUG and not CORS_ALLOWED_ORIGINS: CORS_ALLOW_ALL_ORIGINS = True`
- Impact:
  - If `DEBUG` is left enabled in reachable environments, any origin can issue credentialed browser requests to the API.
- Fix:
  - Remove wildcard CORS fallback even in debug.
  - Require explicit local origins (`5173`, `8000`) and fail fast when missing.
- Mitigation:
  - Add deployment assertion that blocks startup when `DEBUG=True` and host is not localhost.
- False positive notes:
  - This is mostly a misconfiguration hazard, but template defaults should still be safer.

## Low Findings

### [SEC-006] Dependency versions are not pinned, increasing supply-chain drift risk
- Severity: Low
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/requirements.txt:1`, `/Users/will/Code/CodexProjects/DjangoStarter/frontend/package.json:12`
- Evidence:
  - Backend packages are unpinned (`Django`, `djangorestframework`, etc.)
  - Frontend uses caret ranges (`"@clerk/clerk-react": "^5.52.0"`)
- Impact:
  - Builds can drift over time and pull vulnerable or breaking versions unexpectedly.
- Fix:
  - Pin exact versions and commit lockfiles (`requirements.txt` with pinned versions, `package-lock.json` or pnpm lock).
  - Run vulnerability scans in CI (`pip-audit`, `npm audit` with policy).
- Mitigation:
  - Add scheduled dependency update workflow with security review.
- False positive notes:
  - Some teams prefer floating versions during early MVP phase; still risky for production.

### [SEC-007] Public resource identifiers are sequential integers
- Severity: Low
- Location: `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/migrations/0001_initial.py:38`, `/Users/will/Code/CodexProjects/DjangoStarter/backend/api/urls.py:22`
- Evidence:
  - `Project.id` uses `BigAutoField`
  - Route pattern exposes integer primary key: `projects/<int:pk>/`
- Impact:
  - Enables easy ID enumeration and rough record volume inference.
- Fix:
  - Add a public UUID field for external APIs and route by UUID instead of numeric PK.
- Mitigation:
  - Continue strict owner scoping (already present) to prevent IDOR.
- False positive notes:
  - Existing owner-based queryset filtering reduces direct data exposure risk.

## Positives Observed
- Clerk JWT signature verification uses JWKS and explicit algorithm allowlist.
- Clerk webhook endpoint verifies Svix signatures before dispatching handlers.
- Project querysets are owner-scoped, reducing horizontal data access risk.
- Frontend rendering avoids dangerous raw HTML sinks.

## Recommended Remediation Order
1. Fix `SEC-001` by removing cookie fallback or adding CSRF enforcement for cookie-authenticated requests.
2. Harden production settings defaults and deploy guards (`SEC-002`, `SEC-003`, `SEC-005`).
3. Tighten JWT audience and authorized-party requirements (`SEC-004`).
4. Improve long-term resilience (`SEC-006`, `SEC-007`).
