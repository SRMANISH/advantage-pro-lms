# CodeRabbit review prompt

Paste everything below the line into the CodeRabbit CLI (`coderabbit review`) or the VS Code
extension chat. It is deliberately self-contained — assume the reviewer has no prior context.

---

You are performing a **deep production-readiness review** of the Advantage Pro LMS. Be
skeptical and specific. I want findings I can act on, each with `file:line`, a concrete
failure scenario, and a suggested fix. Prefer a small number of *verified, high-confidence*
findings over a long list of speculation — but do not soften genuine problems.

## 1. What this codebase is

An internal Learning Management System for a training institute that runs instructor-led
courses in **batches**. Not a public MOOC: every account is staff-created, every student
belongs to a batch.

- **Backend:** Django 5.2 + DRF 3.17, ~15 domain apps (modular monolith) + 4 model-less
  read-only aggregator packages (`dashboard`, `performance`, `reports`, `upsell`).
  PostgreSQL 16 in prod / SQLite locally. Redis for cache + throttling. django-q2 for async
  notification fan-out. Session-cookie auth with CSRF (no JWT).
- **Frontend:** React 18 + TypeScript + Vite 7 + Tailwind + TanStack Query v5, one feature
  folder per backend domain.
- **Roles (7):** Student, Faculty, Admin, MIS Executive, Counselor, Tech Support, Super Admin.

Read `docs/PROJECT_OVERVIEW.md` first — it is a complete functional + technical spec including
the permission matrix and the architecture rationale.

## 2. Output format I want

For each finding:
```
[SEVERITY: critical | high | medium | low]  <one-line claim>
Where:     path/to/file.py:123
Scenario:  <concrete inputs/state -> wrong outcome. Not "this could be unsafe".>
Fix:       <specific change>
Confidence: <high | medium — say if you could not fully verify>
```
Then finish with: (a) a **scored verdict** out of 100 for each of
*Requirement Alignment, Production Readiness, Architecture & Modularity, Security,
Performance, UI/UX*, each with one sentence of justification; and (b) the **three changes
that would most improve production safety**, ranked.

## 3. Priority 1 — Security & robustness

Verify each of these independently. State clearly whether the property **holds or is
violated**, and cite the exact lines you checked. Do not assume my framing is correct.

1. **Upload path safety.** Trace an uploaded filename end-to-end: from
   `core/uploads.py::validate_upload` → the storage-key construction sites
   (`content/serializers.py`, `forum/views.py`, `assessments/serializers.py`,
   `assessments/views/tasks.py`, `assessments/views/tests.py`, `engagement/views.py`) →
   `core/adapters/local.py::_path`. **Can a crafted `upload.name` escape `MEDIA_ROOT`?**
   Consider names containing `../`, absolute paths, backslashes, URL-encoded separators, and
   null bytes. Note that an extension allowlist is applied — assess whether it actually
   prevents traversal or merely constrains the extension.
2. **Auth endpoint throttling.** Which authentication-adjacent endpoints are rate-limited and
   which are not? Check `accounts/views/auth.py`, `accounts/views/setup.py`,
   `accounts/views/password.py`, `accounts/views/totp.py`, and
   `accounts/throttling.py`. Identify any OTP-verification, TOTP-verification, or
   account-setup endpoint reachable without a dedicated throttle, and assess the brute-force
   exposure given the global DRF defaults in `config/settings/base.py`.
3. **Production misconfiguration guards.** `config/settings/prod.py` fails fast on
   `SECRET_KEY`, `ALLOWED_HOSTS`, and `REDIS_URL`. **Is there any equivalent guard preventing
   a deploy that silently keeps the console/stub notification adapters** (`LMS_EMAIL_ADAPTER`,
   `LMS_SMS_ADAPTER`, `LMS_WHATSAPP_ADAPTER` defaulting to `core.adapters.local.*`)? What is
   the real-world consequence if this ships unnoticed?
4. **Demo seeder safety.** `accounts/management/commands/seed_demo.py` creates accounts with a
   known hardcoded password. **Can it be run against a production database?** Is there any
   DEBUG/environment guard or confirmation flag?
5. **Authorization correctness.** The RBAC matrix (`core/permissions_matrix.py`) is enforced by
   `core/permissions.py::MatrixPermission`, supports DB overrides
   (`core.models.PermissionOverride`), and is pinned by `tests/test_permissions.py`. Look for:
   any endpoint bypassing the matrix with a hardcoded role check; any list/detail endpoint
   missing object-level scoping (faculty → own batches, student → own records); and whether the
   lockout guard genuinely prevents Super Admin from removing its own access.
6. **Secret handling.** `core/crypto.py` (Fernet, key derived from `SECRET_KEY`) and
   `core/integrations.py` (DB-first-then-env provider config). Assess: key-rotation behaviour,
   whether plaintext secrets can leak into logs/responses/cache, and the `secret_set`-only
   API contract in `notifications/views.py`.
7. **Race conditions.** This codebase has a stated rule that every "at most once" guarantee is
   backed by a DB constraint *and* a race-safe write. Audit for surviving check-then-create or
   read-modify-write patterns — especially `assessments/` (one attempt per student),
   `escalations/services.py`, `attendance/services.py`, and `accounts/device.py`.

## 4. Priority 2 — Feature reality check (is it real, or a shell?)

For each area below, determine whether it is **fully implemented**, **config-dependent**
(works only when env/credentials are supplied), or a **genuine gap/simulation**. Base this on
the code, not on documentation claims. Flag any frontend page rendering **mock/hardcoded data
instead of API responses**.

Backend apps: `accounts`, `batches`, `enrollments`, `content`, `assessments`, `attendance`,
`forum`, `liveclasses`, `certification`, `engagement`, `feedback`, `escalations`,
`notifications`, `audit`, `core`, plus `dashboard`, `performance`, `reports`, `upsell`.

Frontend feature folders: `frontend/src/features/*`.

Specifically confirm or refute each of these:
- Every role dashboard is driven by real aggregates (`dashboard/views.py`), not placeholders.
- Forum attachments genuinely upload, store, and serve (`forum/views.py`).
- Media delivery uses an nginx `X-Accel-Redirect` seam in prod and streams in dev
  (`content/delivery.py`) — and that **all** file-serving paths go through it.
- Upload validation performs real magic-byte sniffing, not just extension checks
  (`core/uploads.py`).
- The permission-matrix editor actually persists and takes effect at runtime.
- The device-binding approval workflow is complete end-to-end (`accounts/device.py`).
- **Certificates:** confirm this is ID-entry + follow-up tracking only, with **no PDF
  generation** anywhere.
- **Payments:** confirm there is no payment/billing implementation (`Course.fees` is a stored
  field only).
- **Seeded videos:** confirm `seed_demo` writes placeholder blobs, not real media.
- **Notifications:** confirm email/SMS/WhatsApp default to console stubs unless env-configured.

## 5. Priority 3 — Architecture, modularity, duplication

- Assess the standard `models / serializers / views / urls` pattern and whether the deliberate
  deviations are justified: model-less aggregator apps (`dashboard`, `performance`, `reports`,
  `upsell`), `attendance`'s serializer-less hybrid, and the `views/` packages in `accounts`
  and `assessments`.
- Evaluate coupling direction. Is the dependency flow (leaf features → `accounts`/`batches` →
  `core`) actually respected, or are there sideways imports between feature apps?
- **Duplication I already suspect — confirm and propose the cleanest extraction:**
  - `attendance/views.py::_resolve_batch` vs `reports/views.py::_batch_for` (near-identical).
  - A hand-rolled batch `<select>` repeated across ~9 frontend pages (`ManageTests`,
    `TasksPage`, `AttendancePage`, `BatchesPage`, `ContentPage`, `EngagementReportPage`,
    `EscalationsPage`, `PerformancePage`, `ReportsPage`).
  - ~33 backend test files each redefining local `user()` / `client_for()` helpers instead of
    shared fixtures.
- Flag any module that has outgrown its file and should be split, and any abstraction that is
  over-engineered for its single caller.

## 6. Priority 4 — CI, deployment, and documentation drift

- `.github/workflows/ci.yml`: identify what is **not** covered. Specifically assess the absence
  of dependency/vulnerability scanning (pip-audit / npm audit), any SAST or secret scanning,
  and whether the existing Playwright specs in `frontend/e2e/*.spec.ts` are wired into CI at
  all. What can currently reach `main` broken?
- `docker-compose.yml` vs `docs/DEPLOYMENT.md`: the docs describe a production topology
  including a django-q2 `qcluster` worker and Redis. **Does the compose file actually provide
  them?** Report any contradiction between the two.
- Cross-check `docs/PRODUCTION_READINESS.md` and `docs/BUILD_PLAN.md` against the code and flag
  claims that are no longer true (documentation drift).
- `pyproject.toml` has opt-in coverage config — comment on whether coverage should gate CI.

## 7. Accepted limitations — please do NOT report these as findings

These are deliberate, documented in `docs/PROJECT_OVERVIEW.md` §13, and will not be changed.
Reporting them is noise:

1. **A web application cannot read a device's MAC address.** Device identity is a FingerprintJS
   visitorId + client IP on audit rows. It is a deterrent against casual account sharing, not a
   hardware lock. Do not suggest MAC capture.
2. **"View-only" notes and the video watermark are deterrents, not DRM.** The browser
   necessarily receives the bytes. Do not propose DRM.
3. **Client-side route/nav gating is cosmetic by design.** The server matrix is authoritative.
   Do not report the frontend role `Set`s as a security hole — but *do* report any case where
   the server fails to enforce what the UI hides.
4. **Email is intentionally non-unique** (one account per course per person); ambiguous email
   logins fall back to the Registration ID.
5. ~~40 plain `APIView`s return hand-built dicts...~~ **Fixed.** All 71 now declare request and
   response bodies via `@extend_schema`; the schema generates with zero errors and zero warnings,
   and `SILENCED_SYSTEM_CHECKS` is empty.
6. **Nothing has run on a production VPS yet** — Postgres/Redis/nginx/qcluster/Sentry/backup
   restore are configured and documented but not yet exercised on real infrastructure.

## 8. Invariants this code is meant to hold — flag any violation

1. Permissions come **only** from `core/permissions_matrix.py`; no hardcoded role checks in
   views, serializers, or components.
2. Any change to `MATRIX` must update `tests/test_permissions.py` in the same commit.
3. Object-level scoping is required **in addition to** the matrix.
4. Every "at most once" rule is backed by a DB constraint **and** a race-safe create.
5. All file serving goes through `content/delivery.py::deliver()` — no bare `FileResponse`, no
   importing private streaming helpers across apps.
6. List endpoints that can grow must paginate server-side; the frontend must not fetch a large
   page and slice it client-side.
7. Model changes ship reversible migrations with safe defaults.
8. Deterrents must never be described in code or UI copy as guarantees.

Begin with the Priority 1 security verification, then work down. Where you cannot verify
something with confidence, say so explicitly rather than guessing.
