# ADR 0001 — Foundation stack & module-0 architecture

- Status: Accepted
- Date: 2026-06-22

## Context
Advantage Pro LMS needs a secure, clean, dynamic, batch-centric platform with seven
role-isolated portals, deployed on Hostinger later. We needed a foundation that supports
strict server-side RBAC, an audit trail, and swappable external services.

## Decision
- **Backend:** Django + Django REST Framework. **DB:** PostgreSQL (SQLite fallback for
  quick local dev via `DATABASE_URL`). **Frontend:** React + Vite + TypeScript + Tailwind.
- **Ports & adapters:** storage / email / SMS / WhatsApp / scheduler behind interfaces
  (`core/adapters`), selected from settings via a registry. Hostinger/3rd-party adapters
  drop in via config.
- **RBAC:** single source-of-truth permission matrix (`core/permissions_matrix.py`)
  mirroring the execution plan, enforced by `MatrixPermission`. Code-defined now;
  promotable to a DB-backed, Super-Admin-editable matrix later without changing callers.
- **Auth model:** username-keyed custom user (email intentionally non-unique to allow a
  separate student record per course); role-bound login pages.
- **Security baseline:** Argon2id hashing, hardened prod settings (HTTPS, HSTS, secure
  cookies), DRF session auth + CSRF, append-only audit log.
- **SDLC:** incremental module delivery with a Definition of Done; quality gates
  (ruff, black, mypy, pytest / eslint, prettier, tsc, vitest); Docker for dev/prod parity.

## Consequences
- Switching providers or the database is configuration, not code changes.
- The matrix is testable in isolation and is covered by tests.
- Python is pinned to 3.12 in Docker for wheel/compat stability (local dev used 3.14).
