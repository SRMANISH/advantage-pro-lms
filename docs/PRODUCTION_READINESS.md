# Advantage Pro LMS — A‑to‑Z Production Readiness Analysis

_Snapshot of the codebase as built. Honest assessment of what is production-grade, what is
in bits/pieces or stubbed, what must be wired to real data stores/services, and what must be
done on Hostinger. Grades: ✅ done · 🟡 partial/dev-only · ⛔ missing._

---

## 0. Snapshot
- **Backend:** Django + DRF, 16 domain apps, **~117 tests passing**, ruff/black clean, migrations tracked.
- **Frontend:** React + Vite + TS + Tailwind, per-role portals + sidebar shell + landing page; wired to the API.
- **Runs locally** on SQLite + console/local adapters. **Not yet deployed; not yet on PostgreSQL or real providers.**
- **Architecture is sound and decoupled** (REST API + ports/adapters). The remaining work is mostly **integration + ops + a UI redesign**, not rewrites.

---

## 1. FRONTEND (UI → production)

| Area | State | What's needed for production |
|------|:--:|------|
| Visual design / UX | 🟡 | **Full redesign** (you flagged this). Current pages are functional but plain. Biggest FE item. |
| App shell / nav | ✅ | Sidebar + icons + responsive drawer in place. |
| API wiring | ✅ | All features call the real API (axios + session cookie + CSRF). |
| Loading / empty / error states | 🟡 | Minimal. Need consistent skeletons, error toasts, empty illustrations, retry. |
| Error boundaries | ⛔ | No React error boundary — one render error blanks the app. Add boundaries. |
| Form validation | 🟡 | Mostly relies on backend errors. Add inline client validation. |
| Accessibility (a11y) | 🟡 | Some aria labels; needs a pass (focus order, contrast already AA, keyboard nav, labels). |
| Video player | 🟡 | In-app `<video>` + moving watermark + no-download deterrents. No HLS/adaptive/DRM; seeded videos are placeholders. |
| Device identifier | ⛔ | `lib/device.ts` is a `localStorage` UUID — cleared storage = "new device"; trivially bypassed. Needs a real fingerprint (e.g. FingerprintJS) for the device policy to mean anything. |
| Auth UX | 🟡 | No "forgot password" UI; no password-change screen (see backend gap). |
| Branding/meta | ⛔ | No favicon, page `<title>`/meta, social tags, 404 page styling. |
| Frontend tests | 🟡 | Only 1 component test. Add component + a few E2E (Playwright) flows. |
| Build & serve | 🟡 | `npm run build` works; needs Nginx serving `dist/` + `VITE_API_URL`/same-origin + cache headers. |
| i18n / locale | ⛔ | English only; dates shown in browser locale. Add if needed. |

---

## 2. BACKEND CORE

| Area | State | What's needed |
|------|:--:|------|
| Architecture / apps | ✅ | Clean modular apps, REST API, ports & adapters. |
| RBAC + object scoping | ✅ | Matrix enforced server-side, per-role querysets, tested. |
| Passwords / OTP setup | ✅ | Argon2id; two-step OTP (HMAC-stored, expiring, attempt-capped). |
| **Forgot/reset password** | ⛔ | **Missing.** Only initial setup exists; active users can't reset a forgotten password. Build a reset flow (email token → new password). |
| Password change (logged-in) | ⛔ | No change-password endpoint. Add. |
| Sessions | 🟡 | DB-backed (Django default) — fine for one server; move to cache/Redis at scale. |
| **Cache backend** | ⛔ | No `CACHES` config → default **LocMemCache (per-process)**. With multiple gunicorn workers, **throttling becomes per-worker (inconsistent)**. Add **Redis** for cache (and ideally sessions). |
| Rate limiting | ✅ | Global anon/user throttles + login brute-force guard (tested). Needs shared cache to be reliable (above). |
| File upload limits/validation | ⛔ | No explicit size/type limits on video/material/task uploads. Add `DATA_UPLOAD_MAX_*`, per-endpoint size + content-type/extension validation. |
| Full-text search (forum) | 🟡 | Uses `icontains` (works on any DB). Upgrade to PostgreSQL full-text/GIN for scale. |
| Audit log | ✅ | Append-only, on sensitive actions. Add retention/rotation policy. |
| Logging | ⛔ | No `LOGGING` config. Add structured logging (JSON) + request logging. |
| Error monitoring | ⛔ | No Sentry/error tracking. Add. |
| Settings hardening | ✅ | prod.py: HTTPS/HSTS/secure cookies/nosniff + **fail-fast on dev SECRET_KEY/ALLOWED_HOSTS**. |
| Secrets management | 🟡 | Via env/`.env`; ensure real secrets vault/host env on Hostinger; never commit `.env`. |
| mypy / type-checking | 🟡 | Configured (django-stubs) but not run in CI. Run + fix. |
| API docs | ✅ | drf-spectacular schema + Swagger at `/api/v1/docs/`. |

---

## 3. PER-MODULE "bits & pieces"

| Module | Backend | What's stubbed / left |
|--------|:--:|------|
| Accounts / auth / role login | ✅ | Add forgot/reset + change password; optional staff 2FA. |
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
- ⛔ **CI/CD** — gates configured (ruff/black/mypy/pytest, eslint/tsc/vitest) but no pipeline runs them. Add GitHub Actions (pairs with the deferred GitHub setup).
- ⛔ **Monitoring/alerting** — add Sentry (errors) + uptime + basic metrics.
- ⛔ **Structured logging** + log shipping.
- ⛔ **Backups** + restore drills.
- 🟡 **Tests** — strong on security/business logic; add E2E + more edge/concurrency + run mypy. No load testing yet.

---

## 8. DATA & COMPLIANCE
- PII held: student name, email, phone, **employment company**, performance. Define **retention**, access policy, and (for India) DPDP-style consent/erasure; audit log already supports accountability.
- Add data export/delete for a student on request; document who can see what (the matrix already enforces it).

---

## 9. PRIORITISED ROADMAP

**Phase 1 — must-have to launch (blockers):**
1. PostgreSQL run + verify; Redis for cache/throttle. 2. Real adapters: SMTP email, SMS, WhatsApp, object storage. 3. Secrets + HTTPS + Nginx/gunicorn/systemd on Hostinger. 4. Cron jobs live. 5. **Forgot/reset password** + change password. 6. Upload size/type limits. 7. Backups + basic Sentry/logging. 8. Remove demo accounts; create real Super Admin.

**Phase 2 — should-have:**
UI redesign; CI pipeline + mypy; E2E tests; full-text search (PG); video hardening (object storage signed URLs / HLS); stronger device fingerprint; email templates.

**Phase 3 — nice-to-have:**
WhatsApp templated campaigns; analytics; i18n; Zoom/Meet auto-create; load testing; PWA/offline.

---

### Bottom line
The **core + security architecture is production-grade and well-tested**, and thanks to the adapter design the path to production is a **defined integration/ops checklist (Phase 1)** plus a **UI redesign** — not a rewrite. The two true *code* gaps to add regardless of infra are **forgot/reset password** and **upload validation**; everything else in Phase 1 is wiring real services + deploying.
