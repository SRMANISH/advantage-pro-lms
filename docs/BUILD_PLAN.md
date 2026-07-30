# Advantage Pro LMS — Build Plan

> Source-of-truth build plan. Derived from `Advantage_Pro_LMS_Execution_Plan.pdf`.
> Status: **Planning — not yet building.** We build module by module with sign-off between each.

---

## 1. Confirmed decisions

| Area | Decision |
|------|----------|
| Backend | Django + Django REST Framework (DRF) |
| Database | PostgreSQL |
| Frontend | React + Vite + TypeScript |
| Styling | Tailwind CSS with a custom **light-blue & white** design system |
| Hosting | Hostinger (wired in later) — app built **portable** |
| Video storage/streaming | Files on Hostinger storage via a **storage adapter**; secure player built by us |
| Notifications | Provider-agnostic interface; email via Hostinger SMTP later, SMS/WhatsApp via 3rd-party later |

### Honest constraints to confirm with Hostinger before deployment
- Python + PostgreSQL generally needs a Hostinger **VPS or Cloud** plan (not basic shared hosting).
- We build the protected video player ourselves (no Hostinger DRM product); files live on its storage.
- Email/SMTP via Hostinger. SMS/WhatsApp likely via a **messaging third-party integration the user may already have** — we connect to it through the notification adapter; need the provider name + API docs when we reach notifications.

---

## 2. Architecture principles

- **Ports & adapters (hexagonal):** all external services (storage, video, email, SMS, WhatsApp, scheduler) sit behind interfaces. Dev uses local/stub adapters; Hostinger/3rd-party adapters drop in later via config — no rewrites.
- **Dynamic & config-driven (no hardcoding):** roles/permissions, courses, batches, notification templates, and every business threshold (video ≥80%, absence 50%, doubt ~3h window, reminder timings, link/OTP expiry) live in the **database/settings**, editable by Super Admin — not baked into code. Dashboards, theme tokens, and feature flags are data-driven too, so the platform flexes without redeploys.
- **Single source-of-truth permission matrix:** the PDF's permission table is seeded into a **DB-backed RBAC** and enforced server-side on every endpoint (frontend never trusted); Super Admin can tune it.
- **Thin, clean modules:** one Django app per domain; no duplicated logic; shared concerns in `core`.
- **Security by default:** least privilege, server-side authorization, audited sensitive actions, validated input everywhere. Target baseline: **OWASP ASVS Level 2** + defenses for the **OWASP Top 10**.

---

## 3. Security model (cross-cutting)

- **Auth:** httpOnly, secure, SameSite session cookies + CSRF protection (no tokens in localStorage).
- **Passwords:** Argon2 hashing. Strong-password policy. Lockout + rate limiting on login.
- **Two-step setup:** signed single-use 48h setup link → 6-digit email OTP → 6-digit phone OTP → set password. OTPs stored hashed, short expiry, attempt limits, rate limited.
- **RBAC:** 7 roles + object-level checks (faculty → only their batches; student → only own records).
- **Device policy:** device fingerprint bound on first login; change only during a live class with faculty approval; new-device alert → faculty; access closes at course end.
- **Video:** signed time-limited URLs, segmented HLS, dynamic per-student watermark (name/ID + moving overlay), no download button / direct file access (acknowledged: deters but cannot stop camera capture), resume + ≥80% = present.
- **Audit log:** append-only record of who did what, when, on which target.
- **Transport/data:** HTTPS only, input validation via serializers, ORM (anti-SQLi), secrets via env, regular dependency scanning.

---

## 4. Domain model (high level)

- **accounts:** `User` (role, status: pending/active/suspended/deactivated), `OTPCode`, `SetupToken`, `DeviceBinding`, `DeviceChangeRequest`
- **batches:** `Course`, `Batch` (Draft→Active→Completed), `BatchFaculty`, `Enrollment` (separate student ID per course — no merging across courses), `ImportJob`
- **content:** `Video`, `VideoProgress`, `Material/Note`
- **assessments:** `Test`, `Question`, `Choice`, `TestAttempt`; `Task`, `TaskSubmission`
- **attendance:** `AttendanceEvent` (source: LIVE/VIDEO/TEST/TASK), `PerformanceSnapshot`
- **liveclasses:** `LiveClass`, `LiveClassCheckIn`
- **forum:** `Thread`, `Reply` (per batch, resolvable)
- **notifications:** `Notification`, `ScheduledJob`
- **certification:** `Certificate`, `UpsellPrompt`
- **audit:** `AuditLog`

> Open detail to resolve in Module 4/5: login identifier when the same person enrols in two courses (same email, different student ID). Plan: **student ID / registration number is the login identifier**, email may repeat across enrolments.

---

## 5. Project structure

```
advantage-pro-lms/
├─ backend/
│  ├─ config/                 # settings (env-driven), urls, asgi/wsgi
│  ├─ core/                   # base models, permission matrix, RBAC, audit, adapter interfaces
│  ├─ adapters/               # storage/email/sms/whatsapp/scheduler implementations
│  ├─ accounts/  batches/  content/  assessments/
│  ├─ attendance/  liveclasses/  forum/  notifications/  certification/  audit/
│  └─ tests/                  # pytest + factory_boy
├─ frontend/
│  ├─ src/
│  │  ├─ app/                 # router + role-based portal shells
│  │  ├─ design-system/       # tokens, theme, shared UI components
│  │  ├─ features/            # one folder per module (auth, batches, content, ...)
│  │  ├─ lib/                 # api client, auth context, guards, query hooks
│  └─ ...
├─ docs/                      # this plan + per-module specs
└─ README.md
```

---

## 6. SDLC methods (chosen)

**Model: Agile, incremental delivery (Scrum/Kanban-lite) with a hard Definition of Done per module** — fits the module-by-module, sign-off-between-each way of working. Each module is a vertical slice (DB → API → UI → tests) that is shippable on its own.

- **Secure SDLC (DevSecOps):** lightweight threat-model per module; security is part of Definition of Done, not an afterthought.
- **Test strategy:** test pyramid (many unit, fewer integration, few E2E); TDD for core logic (validation, grading, attendance, RBAC). Backend pytest + pytest-django + factory_boy; frontend Vitest + React Testing Library; optional Playwright E2E.
- **Version control:** trunk-based with short-lived **one-branch-per-module**, PR + self-review checklist before sign-off.
- **CI/CD:** on every push — lint + type-check + tests + **SAST (bandit/semgrep)** + **dependency & secret scanning (pip-audit, npm audit, gitleaks)**. Automated deploy wired when Hostinger is connected.
- **Quality gates:** ruff + black + mypy (backend); eslint + prettier + tsc (frontend); pre-commit hooks. Nothing merges red. _All of these now run in GitHub Actions (`.github/workflows/ci.yml`) alongside pytest with an 85% coverage floor, vitest, Playwright E2E, `pip-audit`, `npm audit` and gitleaks._
- **Docs:** OpenAPI (drf-spectacular) for the API, short **ADRs** for decisions, per-module spec in `docs/`.
- **Config & releases:** 12-factor env config, reversible DB migrations, dev/staging/prod parity via Docker.
- **Per-module workflow:** Design (model + API contract + UI sketch) → backend (models, serializers, permissions, endpoints, tests) → frontend → tests green → security check → demo to you → **your sign-off** → next module.

## 6a. Algorithm & engineering choices ("best algorithm")

- **Passwords:** Argon2id (memory-hard) + strong-password policy + login throttling/lockout.
- **OTP & setup link:** CSPRNG codes (`secrets`), stored as HMAC-SHA256, constant-time compare, short expiry + attempt limits; setup link = signed, single-use, 48h.
- **Student import:** single-pass O(n) validation, set-based dedupe + DB unique constraints, **all-or-nothing atomic transaction** with bulk insert; row-by-row error report on any failure.
- **Video watched %:** **interval-merge** of watched ranges (not naive cumulative time) for a true unique-coverage figure → accurate ≥80% = present; resume from last position.
- **Attendance:** event-sourced `AttendanceEvent`s + indexed DB-side aggregation (no per-request recompute).
- **Performance & rank:** configurable **weighted composite** (tests/tasks/completion/video/attendance), normalized; batch rank via SQL window functions (`dense_rank`).
- **Forum search:** PostgreSQL full-text search with GIN index.
- **Scheduling:** idempotent due-time jobs for reminders/escalations; rate limiting via sliding-window/token-bucket.
- **Background jobs:** scheduler behind an adapter — default **django-q2** (DB-backed, light) with Celery+Redis as a scale-up option.

---

## 7. Design system — light blue & white (brand: Advantage Pro / Vectra Technosoft)

Palette derived from the Advantage Pro logo (brand blue + emblem violet accent). Exact hex to be confirmed by sampling the logo file once added to the repo.

- **Brand primary:** `#1565AF` · **primary strong/hover:** `#0E4E8A`
- **Light accent:** `#5BC2F0` · **tint surface:** `#EAF4FD`
- **App background:** `#F4F9FE` · **card surface:** `#FFFFFF` · **border:** `#DCEAF9`
- **Accent (violet, sparing):** `#6B3FA0`
- **Text:** `#13243B` · **muted:** `#5A6B85`
- **Semantic:** success `#1E8E5A`, warning `#B9770E`, error `#C0392B`
- All combos meet **WCAG AA** contrast. Tokens defined once and **dynamic** (theme-swappable / white-label ready).
- Logo to live at `frontend/src/assets/logo.png`, used on the login page and every portal header.
- Consistent components (buttons, cards, tables, forms, modals, toasts), spacing scale, rounded corners, soft shadows. Built once in `design-system/`, reused everywhere.

---

## 8. Module roadmap

### Stage 0 — Foundation (prep for everything)
| # | Module | Key deliverables |
|---|--------|------------------|
| 0 | Project foundation | Repo scaffold, Django+DRF+Postgres, React+Vite+TS, Tailwind + design system, adapter interfaces, RBAC + permission-matrix core, audit core, test harness, env config |

### Stage 1 — Foundations
| # | Module | Key deliverables |
|---|--------|------------------|
| 1 | Auth & role routing | **Separate login page per role** (role-bound — account signs in only via its own page), secure sessions, route to that role's portal; per-page rate limiting |
| 2 | Courses & batches | Course catalog, batch CRUD, Draft→Active→Completed, faculty assignment (dropdown) |
| 3 | Student bulk import | CSV/XLSX upload, all-or-nothing row-by-row validation, atomic import, confirmation report |
| 4 | Two-step account setup | 48h setup link → email OTP → phone OTP → password; first-login alert to Admin/MIS |
| 5 | Student & Faculty base portals | Student: own batch view. Faculty: dashboard of assigned batches |
| 6 | Faculty video upload + secure player | Upload via storage adapter, watermark, no-download, resume, progress tracking |
| 7 | Core notifications | Provider-agnostic layer + in-app + email (stub→real); import/first-login/new-content alerts |

### Stage 2 — Learning & tracking
| # | Module | Key deliverables |
|---|--------|------------------|
| 8 | MCQ tests | Build, schedule open/close, auto-grade, one attempt, show score |
| 9 | Tasks | Deadline, text/file submit, late flag, faculty score + feedback |
| 10 | Attendance engine | Auto-capture: live check-in / ≥80% video / test / task submit |
| 11 | Counselor workflow | Absence review, contact missed students, standard message script |
| 12 | Performance dashboards | Aggregate scores/completion/attendance, optional batch rank, role-scoped views |
| 13 | Device policy | First-login lock, live-class device-change request + faculty approval, course-end close |
| 14 | Escalation alerts | Test-not-completed and 50%-absence rules → right recipients |

### Stage 3 — Engagement
| # | Module | Key deliverables |
|---|--------|------------------|
| 15 | Doubt forum | Per-batch threads, replies, attachments, resolve, keyword search |
| 16 | Tech Support workflow | Forum-only access, unanswered-doubt reminders to faculty (~3h window) |
| 17 | Live classes | Admin schedules link, appears in portals, 1h/15m reminders, join + check-in |
| 18 | WhatsApp + SMS channels | Wire SMS/WhatsApp adapters into the notification layer |
| 19 | Certification follow-up | Recurring reminders until student enters Certificate ID |
| 20 | In-video upsell | Social-proof prompt under player using employment data (truthful only) |
| 21 | Reports & exports | Per-batch student/attendance/performance exports, role-scoped |

---

## 9. What I'll need from you (as we reach each module)
- Module 3: the **student import template** columns you want + a sample list.
- Module 2: your **course list** and batch naming convention.
- Module 7/18: chosen email + SMS + WhatsApp providers and credentials (when ready).
- Module 0: any **logo/branding** to fold into the light-blue theme.
- Pre-deploy: your Hostinger **plan type** (VPS/Cloud vs shared).

---

## 10. Progress

- **Module 0 — Project foundation: ✅ complete.**
  - Backend: Django + DRF + settings split (dev/prod), custom user, `core` (TimeStamped base,
    role enum, permission matrix, `MatrixPermission`, adapter interfaces + local adapters +
    registry), `audit` (append-only log). Migrations tracked. Gates green: 10 pytest, ruff,
    black, Django check.
  - Frontend: React + Vite + TS + Tailwind, CSS-variable brand theme, design-system
    (Button/Card/Input/Badge/Logo), role-bound login page, design showcase. Gates green:
    build, eslint, 2 vitest.
  - Infra: Docker (`docker-compose.yml` + backend `Dockerfile`) for PostgreSQL + API,
    `.env.example`, ADR 0001.
- **Module 1 — Auth & role routing: ✅ complete.**
  - Backend: `/api/v1/auth/{csrf,login,logout,me}`. Role-bound login (account must match the
    portal it signs in through), session auth + CSRF, per-page rate limiting (role+IP),
    inactive-account block, login/logout/failure auditing. `seed_demo` command (one active
    account per role). 16 pytest passing (6 auth), ruff/black clean.
  - Frontend: per-role functional login pages, `AuthProvider` (react-query `me`), `ProtectedRoute`
    (auth + role match), role portal placeholders with sign-out, Vite dev proxy for same-origin
    cookies/CSRF. Build/eslint/2 vitest green.
  - Verified end-to-end on a live server: correct-portal login 200, me ok, logout 204,
    post-logout 403, and faculty-creds-on-student-portal correctly rejected (401).
- **Module 2 — Courses & batches: ✅ complete.**
  - Backend `batches` app: `Course` + `Batch` (Draft→Active→Completed, forward-only guarded
    transitions), faculty M2M. APIs `/api/v1/{courses,batches,faculty}/`. Role-scoped (SA/AD/MIS
    all batches, Faculty own only), per-action RBAC via `MatrixPermission.get_required_action`
    (create/edit SA/AD/MIS, delete SA only, assign-faculty SA/AD/MIS/FAC on own batch), audited.
    25 pytest passing (9 new), ruff/black clean.
  - Frontend: `Select` component, `PortalLayout` with nav, Batches page (create course/batch,
    lifecycle buttons, faculty-assign dropdown), role-aware. Build/eslint/vitest green.
  - Verified live end-to-end (CSRF over the wire): create course/batch → transition → assign.
- **Module 3 — Student bulk import: ✅ complete.**
  - Backend `enrollments` app: `Enrollment` model (no cross-course merge; unique reg number);
    CSV/XLSX parser + row-by-row validator (`importer.py`) with all-or-nothing atomic import;
    `dry_run` validate step; `/api/v1/enrollments/` (role-scoped list) + `/enrollments/import/`
    (IMPORT_STUDENTS = SA/AD/MIS). 31 pytest passing (6 new), ruff/black clean.
  - Frontend: Enrolment page (download template, upload, Validate → row-by-row error table or
    "N valid → Confirm import", enrolled-students list), nav item for SA/AD/MIS.
  - `seed_demo` now also creates course FS, active batch FS-DEMO (faculty1), enrols student1.
- **Module 4 — Two-step account setup: ✅ complete.**
  - Backend: `SetupToken` (48h, single-use) + `OTPCode` (HMAC-stored, 10-min, attempt-capped)
    models; `accounts/setup.py` service (CSPRNG codes, constant-time compare, email→phone→password
    via adapters); endpoints `/auth/setup/{start,verify-email,verify-phone,complete,resend}`;
    DEBUG-only `dev_code`/`url` to make the flow testable; import now issues each student a setup
    link; **first-login alert to Admin/MIS** in `LoginView`. 36 pytest passing (5 new), ruff/black.
  - Frontend: public `/setup/:token` stepper (email code → phone code → set password → activate),
    plus an admin "Setup link" action for pending students in the Enrolment page.
- **Module 5 — Student & Faculty base portals: ✅ complete.**
  - Backend: `dashboard` app — `GET /api/v1/dashboard/` returns role-shaped summaries (student =
    their enrolled batch(es) + course/faculty/dates; faculty = batch list + student counts; admin/
    MIS/super = totals; counselor = student/batch totals). 39 pytest passing (3 new), ruff/black.
  - Frontend: real portal home screens per role — student batch cards, faculty batches + stats,
    admin/MIS/super stat tiles + quick actions, counselor stats. Replaces the placeholder card.
- **Module 6 — Faculty video upload + secure player: ✅ complete.**
  - Backend `content` app: `Video`, `Material`, `VideoProgress`; upload via storage adapter
    (faculty own-batch only, UPLOAD_VIDEOS/UPLOAD_NOTES); role-scoped list; access-gated
    **range-capable streaming** (`/videos/{id}/play/`, `/materials/{id}/view/`); progress endpoint
    marks **≥80% = completed**. 45 pytest passing (6 new), ruff/black clean.
  - Frontend: secure `VideoPlayer` (moving per-student watermark, no-download controls, resume
    from last position, throttled progress posts); faculty/admin Content page (upload video/note,
    list); student Videos page (watch + materials). Nav: Content (SA/AD/MIS/FAC), Videos (student).
- **Module 7 — Core notifications: ✅ complete.** (Stage 1 fully done.)
  - Backend `notifications` app: `Notification` model + provider-agnostic `notify`/`notify_many`
    service (in-app + email/SMS/WhatsApp via adapters); endpoints list / unread-count / read /
    mark-all-read. Wired triggers: student import → Admin/MIS; first login → Admin/MIS; new video →
    batch students. 48 pytest passing (3 new), ruff/black clean.
  - Frontend: `NotificationBell` in every portal header (unread badge, dropdown, mark read / mark
    all, navigates on click), polling every 20s.
- **Module 8 — MCQ tests: ✅ complete.**
  - Backend `assessments` app: `Test`/`Question`/`Choice`/`TestAttempt`/`AttemptAnswer`; nested
    create (faculty), scheduled open/close window, **one auto-graded attempt** per student,
    student take-view **hides correct answers**, role-scoped list; new-test notification.
    53 pytest passing (5 new), ruff/black clean.
  - Frontend: Tests page that branches by role — faculty/admin build tests (dynamic
    questions/choices, mark correct), students take (radio) and see their score.
- **Module 9 — Tasks: ✅ complete.**
  - Backend (in `assessments`): `Task` + `TaskSubmission`; faculty create with deadline; student
    one submission (text or file via storage adapter) with **late flag** computed vs deadline;
    faculty grade (score + feedback) via `task-submissions/{id}/grade/` + file streaming; new-task
    and feedback-given notifications. 60 pytest passing (7 new), ruff/black clean.
  - Frontend: Tasks page that branches — faculty/admin create tasks and grade submissions
    (per-submission score/feedback, file view), students submit text/file and see score + feedback.
- **Module 10 — Attendance engine: ✅ complete.**
  - Backend `attendance` app: `AttendanceEvent` (idempotent per student+source+item); auto-capture
    wired into ≥80% video / test submit / task submit (live check-in joins in M17); aggregation
    `student_summary` (present/total/percent, total = videos+tests+tasks[+live]); APIs
    `/attendance/me/` (student) and `/attendance/?batch=` (staff/faculty/counselor roster).
    66 pytest passing (6 new), ruff/black clean.
  - Frontend: Attendance page — student sees per-batch % with a progress bar; faculty/admin pick a
    batch and see a roster with <50% flagged red.
- **Module 11 — Counselor workflow: ✅ complete.**
  - Backend: `/attendance/batches/` (review picker) + `/attendance/follow-up/` (Counselor/Admin/MIS
    send a standard or custom absence message via in-app+email+SMS; audited); roster now returns
    student ids. 70 pytest passing (4 new), ruff/black clean.
  - Frontend: Counselor gets the Attendance roster (nav) with a per-student **Send reminder** button
    (<50% flagged red); "Sent ✓" confirmation.
- **Module 12 — Performance dashboards: ✅ complete.**
  - Backend `performance` module: composite of test% (avg attempt), task% (submission rate),
    video% (completed), attendance% → overall (avg of present components), with **dense batch rank**;
    APIs `/performance/me/` (own record + rank) and `/performance/?batch=` (ranked board, staff/
    faculty/counselor). 74 pytest passing (4 new), ruff/black clean.
  - Frontend: Performance page — student sees per-batch metric tiles + overall + "rank N of M";
    staff/faculty/counselor see a ranked board table.
- **Module 13 — Device policy: ✅ complete.**
  - Backend: `DeviceBinding` (first login binds) + `DeviceChangeRequest`; student login from a new
    device is blocked + raises a request and alerts faculty; faculty/admin approve→rebind or reject;
    course-end (all batches completed) closes student access. `device_id` added to login. Live-class
    gating of the approval is the M17 refinement. 84 pytest passing (5 new), ruff/black clean.
  - Frontend: device id persisted per browser + sent on login; login shows the real block reason;
    faculty/admin Devices page to approve/reject pending requests.
- **Module 14 — Escalation alerts: ✅ complete.** (Stage 2 fully done.)
  - Backend `escalations` app: `Escalation` ledger (each alert once); `run_escalations` —
    incomplete-test reminders (→ student + faculty + MIS) and the 50%-attendance rule (→ faculty +
    counselor + MIS); on-demand `/escalations/run/` (SA/AD/MIS) + `run_escalations` management
    command for the production scheduler. 88 pytest passing (4 new), ruff/black clean.
  - Frontend: MIS/Admin "Escalations" page with a Run-now button + result counts.
- **Module 15 — Doubt forum: ✅ complete.**
  - Backend `forum` app: `Thread` + `Reply`; per-batch scoped (SA/AD/MIS/TS read all, faculty own,
    students enrolled), post doubt + reply + resolve (faculty-of-batch or author), keyword search
    (`?q=` icontains), new-doubt → faculty + reply → author notifications. 93 pytest passing
    (5 new), ruff/black clean.
  - Frontend: Forum page — ask-a-doubt form (batch picker), searchable thread list, thread view
    with replies, reply box, and resolve. Nav for SA/AD/MIS/TS/faculty/student.
- **Module 16 — Tech Support workflow: ✅ complete.**
  - Backend: `/forum/monitor/` (unanswered, unresolved threads with hours-waiting + overdue flag vs
    configurable `FORUM_RESPONSE_WINDOW_HOURS=3`) + `threads/{id}/remind/` (TS/admins nudge batch
    faculty); forum-only role. 96 pytest passing (3 new), ruff/black clean.
  - Frontend: Tech Support "Monitor" page — unanswered doubts, overdue badges, per-thread "Remind
    faculty" button.
- **Module 17 — Live classes: ✅ complete.**
  - Backend `liveclasses` app: `LiveClass` + `CheckIn`; schedule (SCHEDULE_LIVE_CLASSES = SA/AD/MIS),
    role-scoped list, student `check-in` (creates CheckIn + LIVE attendance event, returns the
    meeting link); 1h/15m reminders via the scheduler adapter; new-class notification to students.
    Live classes now also count toward attendance totals. 100 pytest passing (4 new), ruff/black.
  - Frontend: Live classes page — admin schedule form; students Join & check-in; faculty/staff view.
  - (Device-change-during-live-class stays at faculty discretion in dev; the live-now signal exists
    to tighten it later.)
- **Module 18 — WhatsApp / SMS channels: ✅ complete.**
  - Backend: new-live-class now goes via in-app + email + SMS + WhatsApp; Super-Admin
    `/settings/channels/` (provider per channel + dev-stub flag) and `/settings/channels/test/`
    (send a test through any channel's adapter). 104 pytest passing (4 new), ruff/black clean.
  - Frontend: Super Admin "Channels" page — provider table + send-test form.
- **Module 19 — Certification follow-up: ✅ complete.**
  - Backend `certification` app: `Certificate` (one per enrolment); student enters Certificate ID
    for completed courses (`/certification/me`, `/submit`), recurring `run_certificate_reminders`
    (→ uncertified students) via `/certification/remind/` + management command. Reconciled device
    policy: course-end blocks device *changes* only — the bound device can still log in to certify.
    107 pytest passing (4 new + device test updated), ruff/black clean.
  - Frontend: student Certificate page (enter ID / view certified); admin "Send certificate
    reminders" on the Escalations page.
- **Module 20 — In-video upsell: ✅ complete.**
  - Backend `upsell` module: `/api/v1/upsell/` (student) — truthful next-course prompt using the
    student's employment company as social proof + lists courses they're not enrolled in; null when
    none. 110 pytest passing (3 new), ruff/black clean. Seed adds a 2nd course (DS) + employment.
  - Frontend: `UpsellPrompt` under the video player (LearningPage).
- **Module 21 — Reports & exports: ✅ complete.** (All 22 modules built.)
  - Backend `reports`: CSV exports `/reports/{students,attendance,performance}/?batch=` — role-scoped
    (students = SA/AD/MIS/FAC own; attendance/performance += Counselor). 114 pytest passing (4 new),
    ruff/black clean.
  - Frontend: Reports page — batch picker + CSV download links (students hidden for Counselor).
- **All feature modules (0–21) are done.**
- **UI + data overhaul — in progress:**
  - ✅ Real **landing page** at `/` (branded hero, sign-in CTAs, portal grid); dev showcase moved to `/showcase`.
  - ✅ **Sidebar app-shell** with lucide icons + responsive mobile drawer (replaces the plain top-nav),
    polished header with notification bell + sign-out.
  - ✅ **Rich demo seed** — 9 students, videos, 2 tests (6 attempts), 2 tasks (6 submissions), forum
    threads, 2 live classes, 34 attendance events — every screen is populated.
  - ⬜ Optional further polish: per-page metric cards/skeletons, table refinements.
- **Production hardening — in progress:**
  - ✅ **Real scheduler (cron path)** — live-class 1h/15m reminders are now an idempotent
    `send_due_reminders` command (+ `LiveReminder` dedupe); escalations & certificate reminders
    already have commands. All three wired to cron in `docs/DEPLOYMENT.md` (no Celery/Redis needed).
  - ✅ **Global API rate-limiting** (anon/user throttles, env-tunable) + login brute-force guard (tested).
  - ✅ **Prod fail-fast** — settings refuse to boot with a dev `SECRET_KEY` or default `ALLOWED_HOSTS`.
  - ✅ `docs/DEPLOYMENT.md` — full Hostinger go-live runbook (env, gunicorn/nginx, cron, provider swap, checklist).
  - ⬜ Still to do: actually run/verify on PostgreSQL (needs a PG instance), upload size/type limits,
    Sentry + structured logging, ~~CI pipeline~~ ✅ done, then real providers + deploy.
- **Tests: ~117 backend passing.**
