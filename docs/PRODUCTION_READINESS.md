# Advantage Pro LMS — A‑to‑Z Production Readiness Analysis

> ## ⚠️ Historical document — largely superseded
>
> This was written at **~117 backend tests**, before the audit programme, the Procedure-v2
> build, and the production-hardening phases. The current consolidated assessment is
> **[`docs/PRODUCTION_REVIEW.md`](./PRODUCTION_REVIEW.md)** — read that first.
>
> It is kept for history, but several items below are **no longer accurate**. Specifically,
> every one of these former ⛔ blockers is now implemented and tested:
>
> | Was a blocker here | Current state |
> |---|---|
> | Forgot / reset password | ✅ Two-step (email OTP → phone OTP → reset), enumeration-safe, throttled, resend-capped |
> | Change-password screen | ✅ Implemented, with the validator rules shown in the UI |
> | Upload size / type validation | ✅ Per-kind size caps, extension + content-type allowlists, **magic-byte sniffing**, and **server-generated UUID storage keys** — the client filename never reaches a path — with MEDIA_ROOT containment on save/open/delete |
> | Shared-cache throttling (Redis) | ✅ Redis-backed; `prod.py` fails fast without `REDIS_URL` |
> | Dependency scanning in CI | ✅ `pip-audit` + `npm audit` + secret scan + deploy check (`.github/workflows/ci.yml`) |
> | Security headers / CSP | ✅ Documented and shipped in `deploy/nginx.conf` |
> | Staff 2FA | ✅ Optional TOTP for staff accounts |
> | Object storage | ✅ Adapter seam + X-Accel delivery; provider swap is env-only |
> | Prod booting on dev stubs | ✅ `prod.py` refuses to start on console adapters unless `LMS_ALLOW_CONSOLE_ADAPTERS` is set |
> | Demo data reachable in prod | ✅ `seed_demo` raises `CommandError` unless `DEBUG` or `--force` |
> | Brute-forcing a TOTP code | ✅ 5-attempt per-device cap, claimed atomically — a throttle alone cannot stop an IP-rotating attacker |
> | Super Admin self-lockout | ✅ Role change refuses self-demotion and demotion of the last active Super Admin |
> | Duplicate device-change requests / absence reminders | ✅ Enforced by database constraints, not by check-then-write application logic |
> | Unbounded list endpoints | ✅ Feedback inbox and forum monitor are server-paginated |
>
> The one caveat that still stands, unchanged: **nothing has yet run on a production VPS.**

_Snapshot of the codebase as built. Honest assessment of what is production-grade, what is
in bits/pieces or stubbed, what must be wired to real data stores/services, and what must be
done on Hostinger. Grades: ✅ done · 🟡 partial/dev-only · ⛔ missing._

---

## 0. Snapshot
- **Backend:** Django + DRF, 15 apps with models + 4 model-less aggregator packages (`dashboard`, `performance`, `reports`, `upsell`), **387 tests passing**, black/mypy clean, migrations tracked.
- **Frontend:** React + Vite + TS + Tailwind, per-role portals + sidebar shell + landing page; wired to the API. **35 vitest tests** + Playwright E2E specs, both run in CI.
- **Runs locally** on SQLite + console/local adapters; PostgreSQL via `docker-compose.yml`. **Not yet deployed to a VPS, and no real provider credentials have been exercised.**
- **Architecture is sound and decoupled** (REST API + ports/adapters). The remaining work is mostly **integration + ops + a UI redesign**, not rewrites.

---

## 1. FRONTEND (UI → production)

| Area | State | What's needed for production |
|------|:--:|------|
| Visual design / UX | 🟡 | **Full redesign** (you flagged this). Current pages are functional but plain. Biggest FE item. |
| App shell / nav | ✅ | Sidebar + icons + responsive drawer in place. |
| API wiring | ✅ | All features call the real API (axios + session cookie + CSRF). |
| Loading / empty / error states | 🟡 | Minimal. Need consistent skeletons, error toasts, empty illustrations, retry. |
| Error boundaries | ✅ | Global React error boundary in place. _(was ⛔)_ |
| Form validation | 🟡 | Mostly relies on backend errors. Add inline client validation. |
| Accessibility (a11y) | 🟡 | Some aria labels; needs a pass (focus order, contrast already AA, keyboard nav, labels). |
| Video player | 🟡 | In-app `<video>` + moving watermark + no-download deterrents. No HLS/adaptive/DRM; seeded videos are placeholders. |
| Device identifier | ✅ | FingerprintJS visitorId, recomputed each time (never trusts cached storage). Still a deterrent, not a hardware lock — see PROJECT_OVERVIEW §13.1. _(was ⛔)_ |
| Auth UX | ✅ | Forgot-password and change-password screens shipped, with the active validator rules surfaced inline. _(was 🟡)_ |
| Branding/meta | ⛔ | No favicon, page `<title>`/meta, social tags, 404 page styling. |
| Frontend tests | ✅ | 35 vitest unit tests + 12 Playwright E2E money-flow specs, both enforced in CI. _(was 🟡)_ |
| Build & serve | 🟡 | `npm run build` works; needs Nginx serving `dist/` + `VITE_API_URL`/same-origin + cache headers. |
| i18n / locale | ⛔ | English only; dates shown in browser locale. Add if needed. |

---

## 2. BACKEND CORE

| Area | State | What's needed |
|------|:--:|------|
| Architecture / apps | ✅ | Clean modular apps, REST API, ports & adapters. |
| RBAC + object scoping | ✅ | Matrix enforced server-side, per-role querysets, tested. |
| Passwords / OTP setup | ✅ | Argon2id; two-step OTP (HMAC-stored, expiring, attempt-capped). |
| **Forgot/reset password** | ✅ | **Implemented.** Two-step email OTP → phone OTP → reset; HMAC-stored codes, expiry, attempt cap, resend cap, enumeration-safe responses, throttled. _(was ⛔)_ |
| Password change (logged-in) | ✅ | Endpoint + UI shipped, throttled. _(was ⛔)_ |
| Sessions | 🟡 | DB-backed (Django default) — fine for one server; move to cache/Redis at scale. |
| **Cache backend** | ✅ | Redis when `REDIS_URL` is set (LocMem only in dev); `prod.py` refuses to boot without it, so throttles are shared across workers. _(was ⛔)_ |
| Rate limiting | ✅ | Global anon/user throttles + login brute-force guard (tested). Needs shared cache to be reliable (above). |
| File upload limits/validation | ✅ | **Implemented** in `core/uploads.py`: per-kind size caps, extension + content-type allowlists, magic-byte content sniffing, and filename sanitisation backed by a MEDIA_ROOT containment check in the storage adapter. _(was ⛔)_ |
| Full-text search (forum) | 🟡 | Uses `icontains` (works on any DB). Upgrade to PostgreSQL full-text/GIN for scale. |
| Audit log | ✅ | Append-only, on sensitive actions. Add retention/rotation policy. |
| Logging | ✅ | `LOGGING` configured to stdout with a request-id filter (`core/request_id.py`) and `X-Request-ID` echoed on responses. _(was ⛔)_ |
| Error monitoring | ✅ | Sentry SDK initialised in prod behind `SENTRY_DSN`. _(was ⛔)_ |
| Settings hardening | ✅ | prod.py: HTTPS/HSTS/secure cookies/nosniff + **fail-fast on dev SECRET_KEY/ALLOWED_HOSTS**. |
| Secrets management | 🟡 | Via env/`.env`; ensure real secrets vault/host env on Hostinger; never commit `.env`. |
| mypy / type-checking | ✅ | Clean, and enforced in CI. _(was 🟡)_ |
| API docs | ✅ | drf-spectacular schema + Swagger at `/api/v1/docs/`. |

---

## 3. PER-MODULE "bits & pieces"

| Module | Backend | What's stubbed / left |
|--------|:--:|------|
| Accounts / auth / role login | ✅ | Forgot/reset + change password shipped and throttled; staff TOTP 2FA shipped with a 5-attempt device cap. |
| Two-step setup (OTP) | ✅ | Codes only **logged to console** until real email/SMS wired; `dev_code` exposed in DEBUG (off in prod). |
| Device policy | 🟡 | Logic + faculty approval done; **fingerprint is weak (FE)**. "Change only during live class" is faculty-discretion, not strictly gated to a live session. |
| Courses / batches | ✅ | Complete. |
| Student import | ✅ | All-or-nothing CSV/XLSX validation + atomic. Solid. |
| Content / video | 🟡 | Upload + range streaming from **local filesystem**. Needs **object storage** + signed/expiring URLs + (ideally) HLS transcoding. |
| Notes / materials | 🟡 | Same storage story as video. |
| MCQ tests | ✅ | Auto-grade, one attempt, scheduled window, hidden answers. |
| Tasks | ✅ | Deadline, late flag, file submit, grading. File on local storage → object storage. |
| Attendance | ✅ | Auto-capture (video/test/task/live) + aggregation. |
| Performance | ✅ | Composite + dense rank. |
| Counselor follow-up | ✅ | Sends via notify (email/SMS console until wired). |
| Doubt forum | ✅ | Threads/replies/resolve/search. |
| Tech-support monitor | ✅ | Unanswered + overdue + remind faculty. |
| Live classes | 🟡 | Schedule + check-in + attendance. **1h/15m reminders run via cron command** (real, but cron must be configured on the server). Meeting links are external (paste Zoom/Meet) — fine. |
| Notifications | 🟡 | In-app fully real (DB). **Email/SMS/WhatsApp are console stubs** until adapters wired. |
| Escalations | ✅ | Incomplete-test + 50%-attendance rules; cron-driven; idempotent. |
| Certification | ✅ | Enter Certificate ID + recurring reminders (cron). |
| Reports / exports | ✅ | CSV exports, role-scoped. |
| In-video upsell | ✅ | Truthful, employment-based, real courses. |
| Audit / dashboard | ✅ | Complete. |

---

## 4. INTEGRATIONS — data stores & services to wire

| Service | Today (dev) | Production target | Effort |
|---------|------|------|:--:|
| **Primary DB** | SQLite | **PostgreSQL** (configured via `DATABASE_URL`; **not yet run/tested on PG**) | M |
| **Cache / Redis** | none (LocMemCache) | **Redis** for throttle + sessions (+ optional job queue) | S |
| **Object storage** (videos, notes, task files) | local filesystem (`LocalStorageAdapter`) | S3/Cloudflare R2/Hostinger storage → write a `StorageAdapter` + signed URLs | M |
| **Email** | `ConsoleEmailAdapter` (logs) | Hostinger SMTP (Titan) → `EmailAdapter` + templates | S–M |
| **SMS** | `ConsoleSmsAdapter` (logs) | 3rd-party gateway (e.g. MSG91/Twilio) → `SmsAdapter` | M |
| **WhatsApp** | `ConsoleWhatsAppAdapter` (logs) | Meta Cloud API / provider → `WhatsAppAdapter` (templates) | M |
| **Scheduler / jobs** | cron → mgmt commands (works) | Keep cron, or django-q2/Celery+Redis for a worker | S (cron) |
| **Live meeting** | manual link paste | fine as-is; optional Zoom/Meet API for auto-create | — |
| **Video transcoding/CDN** | none | optional: HLS + CDN for scale/DRM | L |

Every adapter is selected by an env var (`LMS_*_ADAPTER`) — wiring a provider is **a new class + credentials**, no call-site changes.

---

## 5. HOSTINGER — what to provision & connect

1. **Plan** — VPS or Cloud (Python + PostgreSQL). Basic shared hosting won't run Django+PG.
2. **PostgreSQL** — create DB/user; set `DATABASE_URL`; run `migrate`. (Hostinger provides MySQL on shared; use PG on VPS/Cloud, or switch ORM to MySQL — PG recommended.)
3. **Python + Node** — Python 3.12 venv (prod requirements), Node 20 to build the frontend.
4. **App server** — gunicorn under **systemd**; **Nginx** reverse proxy for TLS + serving the frontend `dist/` + `/media`.
5. **Domain + DNS + SSL** — point domain, issue Let's Encrypt cert.
6. **Email** — Hostinger **Titan/SMTP** → email adapter.
7. **SMS + WhatsApp** — **not native to Hostinger**; sign up with a gateway (India-friendly e.g. MSG91) and wire adapters.
8. **Object storage** — Hostinger storage or S3/R2 for uploaded videos/notes/tasks (don't keep on the app disk long-term).
9. **Cron** — add the 3 jobs from `DEPLOYMENT.md` (reminders / escalations / certificate).
10. **Redis** — install for cache + throttle (and sessions/jobs if desired).
11. **Backups** — automated PostgreSQL dumps + media backup; test restore.
12. **Secrets** — real `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, CSRF/CORS origins in host env (not in git).

---

## 6. SECURITY CHECKLIST
- ✅ RBAC, object scoping, Argon2id, OTP, CSRF, session auth, HTTPS/HSTS (prod), audit log, login throttle, secret fail-fast.
- ⛔/🟡 to add: shared-cache throttling (Redis), upload size/type validation, forgot/reset password, broader brute-force/lockout, security headers via Nginx (CSP), dependency scanning (pip-audit/npm audit) in CI, secrets in a vault/host env, PII handling/retention policy, optional staff 2FA.

---

## 7. DEVOPS / QA / OBSERVABILITY
- ✅ **CI/CD** — GitHub Actions runs four jobs: backend (ruff/black/mypy/pytest with `--cov-fail-under=85`), frontend (eslint/tsc/vitest/build), security (`pip-audit`, `npm audit`, gitleaks, `check --deploy`), and Playwright E2E. _(was ⛔)_ **The pipeline has not yet had a green run on GitHub** — it is unverified until the first PR.
- ⛔ **Monitoring/alerting** — add Sentry (errors) + uptime + basic metrics.
- ⛔ **Structured logging** + log shipping.
- ⛔ **Backups** + restore drills.
- ✅ **Tests** — 387 backend + 35 frontend, plus Playwright E2E and a dedicated concurrency suite; mypy runs in CI; Locust load test written and run once against a local server. _(was 🟡)_

---

## 8. DATA & COMPLIANCE
- PII held: student name, email, phone, **employment company**, performance. Define **retention**, access policy, and (for India) DPDP-style consent/erasure; audit log already supports accountability.
- Add data export/delete for a student on request; document who can see what (the matrix already enforces it).

---

## 9. PRIORITISED ROADMAP

**Phase 1 — must-have to launch (blockers):**
1. PostgreSQL run + verify; Redis for cache/throttle _(compose + `prod.py` fail-fast done; not yet run on a VPS)_. 2. Real adapters: SMTP email, SMS, WhatsApp, object storage _(all written; no live credentials exercised)_. 3. Secrets + HTTPS + Nginx/gunicorn/systemd on Hostinger _(`deploy/nginx.conf` + `docker-compose.prod.yml` written, never deployed)_. 4. Cron jobs live. 5. ~~Forgot/reset password + change password~~ ✅ done. 6. ~~Upload size/type limits~~ ✅ done (size, extension, declared type, magic bytes, UUID storage keys). 7. Backups + basic Sentry/logging. 8. Remove demo accounts; create real Super Admin _(`seed_demo` now refuses to run unless `DEBUG` or `--force`)_.

**Phase 2 — should-have:**
~~CI pipeline + mypy~~ ✅ done; ~~E2E tests~~ ✅ done; UI redesign; full-text search (PG); video hardening (object storage signed URLs / HLS); stronger device fingerprint; email templates.

**Phase 3 — nice-to-have:**
WhatsApp templated campaigns; analytics; i18n; Zoom/Meet auto-create; load testing; PWA/offline.

---

### Bottom line
The **core + security architecture is production-grade and well-tested**, and thanks to the adapter design the path to production is a **defined integration/ops checklist (Phase 1)** plus a **UI redesign** — not a rewrite. The two true *code* gaps to add regardless of infra are **forgot/reset password** and **upload validation**; everything else in Phase 1 is wiring real services + deploying.
