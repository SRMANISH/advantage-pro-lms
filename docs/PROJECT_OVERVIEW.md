# Advantage Pro LMS — Complete Functional & Technical Specification

> A single, self-contained description of everything this application currently does. Written
> to brief a reviewer (human or AI) who has never seen the codebase. Every claim here reflects
> code in this repository, not aspiration — planned-but-absent behaviour is called out
> explicitly in §13.

---

## 1. What this product is

An internal **Learning Management System** built for **Advantage Pro** (Vectra Technosoft), a
training institute that runs instructor-led courses in **batches**. It is not a public MOOC: every
user is created by staff, every student belongs to at least one batch, and the whole system is
organised around the batch as the unit of teaching, tracking, and reporting.

The application digitises the institute's real operating procedure end-to-end:

- Admissions staff **import** a batch of students from a spreadsheet; each gets a two-step
  account-setup invitation.
- Faculty **teach** (live classes, recorded videos, notes), **assess** (MCQ / file / Colab tests
  and tasks), and **answer doubts** in a forum.
- Students **learn** (watch, read, attempt, submit), and their **attendance is derived from
  logging in**, not from manual marking.
- Counselors and MIS staff **follow up** on absentees, low performers, and missing certificates.
- Management gets **batch-wise reporting**, engagement tracking, and a private feedback channel.

The defining characteristic of the system is that **who may do what is a first-class, centrally
enforced concern** — see §4.

---

## 2. Technology stack

### Backend
| Concern | Choice |
|---|---|
| Language / framework | Python, **Django 5.2.15** |
| API | **Django REST Framework 3.17.1** |
| Database | **PostgreSQL 16** in production (`DATABASE_URL`); SQLite for local dev/tests |
| Cache / rate-limit store | **Redis** in production (`REDIS_URL`); LocMemCache locally |
| Background jobs | **django-q2** (`qcluster`) for async notification fan-out |
| API schema | **drf-spectacular** (Swagger UI at `/api/v1/docs/`) |
| Password hashing | **argon2** |
| 2FA | **pyotp** (TOTP, staff-optional) |
| Secret encryption | **cryptography** (Fernet) |
| Spreadsheet import | **openpyxl** |
| Server | gunicorn behind nginx; WhiteNoise for static |
| Monitoring | Sentry SDK (env-gated) |

### Frontend
| Concern | Choice |
|---|---|
| Framework | **React 18** + **TypeScript** |
| Build | **Vite 7.3.6** |
| Styling | **Tailwind CSS** with a custom brand token set |
| Server state | **TanStack Query v5** |
| Routing | **React Router v6** |
| Animation | **framer-motion** (reduced-motion aware) |
| Charts | **Recharts**, lazy-loaded into a separate chunk |
| Device identity | **FingerprintJS** (OSS visitorId) |

### Quality tooling
`ruff` + `black` + `mypy` (backend) · `eslint` (with `jsx-a11y`) + `tsc` (frontend) ·
`pytest` + `pytest-django` + `pytest-cov` · `vitest` · `Playwright` (E2E) · `locust` (load).

---

## 3. Architecture

### 3.1 Modular monolith
One Django project, **15 registered domain apps** plus 4 view-only packages. Each app owns its
models, serializers, views, urls, and (where logic is non-trivial) a `services.py`.

**Apps with models:** `core`, `accounts`, `audit`, `batches`, `enrollments`, `content`,
`notifications`, `assessments`, `attendance`, `escalations`, `forum`, `liveclasses`,
`certification`, `engagement`, `feedback`.

**View-only packages** (no models — they read across apps): `dashboard`, `performance`,
`reports`, `upsell`.

### 3.2 Ports and adapters
All outbound integrations sit behind interfaces in `core/adapters/base.py`:
`EmailAdapter`, `SmsAdapter`, `WhatsAppAdapter`, `StorageAdapter`, `SchedulerAdapter`.

Implementations are selected by dotted path in `settings.LMS_ADAPTERS` (env-overridable):
- `core/adapters/local.py` — console/local stubs used in dev and tests
- `core/adapters/smtp.py` — Django SMTP
- `core/adapters/msg91.py` — MSG91 SMS
- `core/adapters/whatsapp_cloud.py` — Meta WhatsApp Cloud API

Provider credentials resolve **DB-first, then env** via `core/integrations.py`
(`integration_config(channel)`), so a Super Admin can edit connections from the UI without a
redeploy. See §7.5.

### 3.3 Single delivery seam
Every byte the app serves — course videos, notes, task submissions, test artefacts, forum
attachments, utility thumbnails — flows through `content/delivery.py::deliver()`. It authorises in
Django, then hands off to nginx via `X-Accel-Redirect` when `MEDIA_XACCEL_PREFIX` is set
(production), or streams with HTTP Range support in dev. `disposition="inline"` vs `"attachment"`
is what makes notes view-only but a student's own task file downloadable.

### 3.4 Async boundary
`notifications/services.py::notify()` / `notify_many()` write the in-app notification
synchronously, then hand email/SMS/WhatsApp to `notifications/dispatch.py::queue_external()`,
which runs inline in dev (`Q_CLUSTER` sync) and as a retried django-q2 task in production.

---

## 4. Roles and the permission matrix

### 4.1 The seven roles
| Role | Slug | Purpose |
|---|---|---|
| **Student** | `student` | Learns: watches, reads, attempts, submits, asks doubts |
| **Faculty** | `faculty` | Teaches one or more batches: uploads videos, schedules live classes, creates tests/tasks, grades, answers doubts |
| **Admin** | `admin` | Day-to-day operations: creates batches, assigns faculty, imports students |
| **MIS Executive** | `mis` | Monitoring & follow-up: notes upload, certificate chasing, video-access control, escalations |
| **Counselor** | `counselor` | Attendance follow-up and student welfare |
| **Tech Support** | `tech_support` | Keeps the doubt forum moving; approves out-of-class device changes |
| **Super Admin** | `super_admin` | Courses, staff accounts, system settings, permission matrix, private feedback inbox |

**Design decision worth understanding:** Super Admin is *deliberately absent* from operational
flows. It cannot create batches, assign faculty, upload notes/tests, schedule live classes, revoke
video access, or read the activity log. This is intentional separation of duties from the client's
operating procedure — not an oversight.

### 4.2 The matrix
`core/permissions_matrix.py` defines an `Action` constant per capability and a `MATRIX` dict
mapping each action to a frozenset of roles. It is the single source of truth.

| Action | Allowed roles |
|---|---|
| `CREATE_EDIT_BATCH` | Admin |
| `DELETE_BATCH` | Super Admin, Admin *(draft = Admin; started = Super Admin only, enforced in the view)* |
| `MANAGE_COURSES` | Super Admin |
| `IMPORT_STUDENTS` | Admin, MIS |
| `MANAGE_STAFF_ACCOUNTS` | Super Admin |
| `CHANGE_USER_ROLE` | Super Admin |
| `ASSIGN_FACULTY` | Admin |
| `UPLOAD_VIDEOS` | Faculty |
| `UPLOAD_NOTES` | MIS, Faculty |
| `CREATE_TESTS` | MIS, Faculty |
| `CREATE_TASKS` | MIS, Faculty |
| `SUBMIT_TASKS_TESTS` | Student |
| `VIEW_PERFORMANCE` | SA, Admin, MIS, Counselor, Faculty, Student |
| `MANAGE_ATTENDANCE` | SA, Admin, MIS, Counselor, Faculty, Student |
| `EXPORT_REPORTS` | SA, Admin, MIS, Counselor, Faculty |
| `ACCESS_AUDIT` | MIS, Faculty |
| `MANAGE_FORUM` | Tech Support, Faculty, Student *(MIS excluded by procedure)* |
| `SCHEDULE_LIVE_CLASSES` | Faculty |
| `REVOKE_VIDEO_INDIVIDUAL` | MIS |
| `CLOSE_COURSE_VIDEO_ACCESS` | Admin, MIS |
| `APPROVE_DEVICE_CHANGE` | Faculty, Tech Support, MIS |
| `SEND_NOTIFICATIONS` | SA, Admin, MIS, Counselor, Tech Support, Faculty |
| `SUSPEND_STUDENT` | SA, Admin, MIS |
| `SUSPEND_FACULTY` | SA, Admin |
| `MANAGE_SETTINGS` | Super Admin |

### 4.3 How it is enforced
1. **Server-side, always.** `core/permissions.py::MatrixPermission` reads each viewset's
   `get_required_action()` (or a view's `required_action`) and calls `can(role, action)`.
2. **Object-level scoping on top.** Faculty see only their own batches; students only their own
   records. Implemented per module (`content/access.py::accessible_batch_ids` /
   `can_access_batch`).
3. **Runtime-editable.** `core/models.PermissionOverride` lets Super Admin change any action's
   role set from the UI. `can()` consults default + override through a 60-second cache. A lockout
   guard prevents Super Admin from removing itself from `MANAGE_SETTINGS` or `CHANGE_USER_ROLE`.
4. **Pinned by test.** `tests/test_permissions.py` is a parametrized role × action regression test
   asserting the exact allow/deny table. **Any matrix change must update this test in the same
   commit.**
5. **Mirrored, not trusted, in the UI.** Route guards in `frontend/src/App.tsx` and nav sets in
   `PortalLayout.tsx` hide what a role cannot do. This is cosmetic — the server is authoritative.

---

## 5. Domain modules in detail

### 5.1 `accounts` — identity, login, devices, 2FA
**Models:** `User` (UUID pk, `username` = login id, non-unique `email` by design, `role`,
`status` ∈ pending/active/suspended), `SetupToken`, `PasswordResetToken`, `OTPCode`,
`DeviceBinding`, `DeviceChangeRequest`, `TOTPDevice`, `FacultyProfile`.

**Login.** One unified sign-in plus seven role-bound login pages. The identifier accepts username
**or** email (an ambiguous email asks for the Registration ID instead). Rejects non-active users.
Throttled at 10/min. On a student login it **records login attendance** (§5.9) and runs device
policy.

**Two-step account setup.** New accounts are created `PENDING` and emailed a single-use 48-hour
link → **email OTP** → **phone OTP** → set password (validated against Django's validators). All
codes are HMAC'd with expiry, attempt caps, and resend limits. `DEBUG` exposes `dev_code` for
demos only. Forgot-password mirrors the same two-OTP flow; change-password exists for active users.

**Enumeration-safe.** Forgot-password always returns `200` with the same response shape and a decoy
token, so it cannot be used to discover which accounts exist.

**Device binding.** A student is bound to the first device they sign in from (a FingerprintJS
visitorId, not a MAC address — see §13). A login from a different device is **blocked** and raises
a `DeviceChangeRequest`, routed by context: **Faculty** approve during one of that student's live
classes; **Tech Support** (notified) or **MIS** (silent capability) approve outside class hours.
After a course completes the bound device still works, but device *changes* are closed. The first
bind uses `get_or_create` to survive concurrent logins.

**TOTP 2FA.** Optional for staff (never students): enroll → confirm → step-up at login →
password-gated disable. Unconfirmed devices are never consulted.

### 5.2 `batches` — courses and batches
**Models:** `Course` (code, name, duration, fees), `Batch`.

Courses are **Super Admin only**. Batches are **Admin only** and carry a mandatory weekly schedule:
`class_days` (JSON list of `mon…sun`), `class_start_time`, `class_end_time`, plus `primary_faculty`
and a `faculty` M2M (the primary is always included in the M2M, so every faculty-scoped query works
unchanged; "soft faculty" = M2M minus primary).

**Faculty scheduling conflict check** (`batches/scheduling.py`): assigning a faculty whose existing
non-completed batch shares a weekday *and* overlaps in time is rejected with the clashing batch
codes in the error ("already occupied").

**Lifecycle:** `draft → active → completed`, forward-only. Completing a batch atomically closes
video access. Deletion is certificate-guarded and state-guarded (draft = Admin, started = Super
Admin).

**Faculty profiles** (`accounts.FacultyProfile`): skills + certifications, self-editable by faculty
and surfaced in the assignment dropdown so the assigner can match a person to a course.

### 5.3 `enrollments` — bulk import and roster
**Model:** `Enrollment` (student, batch, `registration_number` = the business identity, address,
guardian, employment company, plus welcome/goodies flags).

**Import.** CSV/XLSX upload with a downloadable template. Validation is **all-or-nothing**: every
row is checked (required fields, email format, duplicate registration numbers within the file,
unknown batch/course) and the response lists row/field/problem for each error; nothing is written
unless the whole file is valid. Capped at `MAX_IMPORT_ROWS` (5,000). Accepts `Registration ID` /
`reg_id` header aliases. On success each student is created `PENDING` and emailed a setup link.

**Roster.** Server-paginated with server-side search across registration number, name, username,
and batch code, ordered deterministically. MIS can revoke/restore an individual student's video
access from the roster.

**Welcome flow (post-enrolment).** A student's first portal visit shows a two-question popup: *is
your postal address on file?* and *have you received your Advantage Pro goodies?* Missing addresses
are captured and Admin/MIS are notified. Admin/MIS get a paginated **Addresses & goodies register**
where they mark goodies dispatched.

### 5.4 `content` — videos and notes
**Models:** `Video`, `Material`, `VideoProgress`, `VideoAccessRevocation`.

Faculty upload class videos; MIS and Faculty upload notes. Uploads are validated by size,
extension, declared content type, **and magic-byte signature** (`core/uploads.py`) so a renamed
executable is rejected.

**Playback** is gated per role and batch, served through the delivery seam with HTTP Range support,
and carries a **per-student moving watermark**. Reaching **≥80% watched** records an engagement
event. `controlsList="nodownload"`, PiP disabled, right-click suppressed.

**Notes are view-only:** rendered in an in-app viewer (PDF in a toolbar-suppressed iframe, images
inline) with no download affordance and the context menu blocked.

**Access closure.** MIS revokes/restores an individual student's video access; Admin + MIS close a
whole batch's access at course end (also automatic on batch completion). Enforced at play/view time
with a `403`.

### 5.5 `assessments` — tests and tasks
**Models:** `Test`, `Question`, `Choice`, `TestAttempt`, `AttemptAnswer`, `Task`, `TaskSubmission`.
Views are split into `views/tests.py` and `views/tasks.py`.

**Three test kinds:**
- **`mcq`** — faculty build questions/choices; auto-graded the instant the student submits;
  correct answers are never serialised to the student.
- **`file`** — faculty optionally attach a **starter sheet** (e.g. an Excel workbook) the student
  downloads, fills, and re-uploads; graded by hand out of `max_score`.
- **`colab`** — faculty provide a starter notebook link; the student submits their own Colab URL;
  graded by hand.

**One attempt per student**, guaranteed by a DB unique constraint with a race-safe friendly `400`
(not an `IntegrityError`). Open/close windows are enforced.

**Tasks** have `deadline_type` (daily/weekly/custom), automatic late flagging, text and/or file
submission, faculty grading with feedback, a "to grade only" filter, and student notification on
grade.

**File access rule:** a submission file is readable by its **owner**, or by a **non-student with
batch access** (faculty/staff grading). Batchmates cannot read each other's submissions.

### 5.6 `liveclasses` — scheduled sessions
**Models:** `LiveClass` (title, `scheduled_at`, platform, meeting link, status, cancel reason),
`CheckIn`, `LiveReminder`.

**Faculty** schedule classes for their own batches; scheduling immediately notifies the batch on
in-app + email + SMS + WhatsApp. Students check in (records attendance and opens the link).
Automated **60-minute and 15-minute reminders** run from cron, deduped per class/offset.

**Cancellation** sets status + reason and notifies immediately. Cancelling **within 24 hours**
requires explicit confirmation and is recorded as short-notice in the audit trail. Cancelled
classes are excluded from the device-approval "in class now" window.

**Weekly schedule endpoint** exposes each batch's recurring `class_days` + times so the student
calendar can plot the regular timetable, not just ad-hoc sessions.

### 5.7 `forum` — doubt clearing
**Models:** `Thread`, `Reply`, `ThreadAttachment`.

Students **ask**; only **Faculty** and **Tech Support** may **reply** — students cannot answer each
other, and **MIS has no forum access at all** (a deliberate procedure change). Threads carry a
status (`open → answered → resolved / escalated`).

Attachments are supported on threads and replies, gated by the same batch access as the forum;
**image attachments render inline** in the thread, other files download.

**Tech Support monitor:** counts of open / unanswered / overdue / resolved, plus per-thread
`hours_waiting` and an `overdue` flag against a configurable SLA
(`FORUM_RESPONSE_WINDOW_HOURS`, default 3h), and a "remind faculty" action.

### 5.8 `attendance` — login-based
**Models:** `AttendanceEvent` (source ∈ login/video/test/task/live), `AbsenceFollowUp`.

**The headline metric is login-based**, not event-based: a student is present for a day if they
logged in that day. Recorded idempotently per student/batch/day at login. Video/test/task/live
events are still recorded as *activity signals* but are excluded from the attendance percentage.

Percentages are bounded to the batch's `start_date..end_date` window on the read side, so
post-completion logins (allowed, so a student can retrieve their Certificate ID) cannot push
attendance above 100%.

`ATTENDANCE_COUNT_WEEKENDS=false` excludes Saturdays/Sundays from both expected and present days,
and suppresses weekend absentee reminders entirely.

**Follow-up:** a shared Counselor + MIS daily roster (logged-in vs absent) with per-student
follow-up status (pending / contacted / not reachable / resolved / escalated) and notes. Absentees
get an automated reminder, at most once per student per day.

### 5.9 `performance` and `reports`
Composite per-student scoring across tests, tasks, videos, and attendance, computed with **set-based
queries** (no per-student loops) and dense ranking. A student's own view reads from a 60-second
cached board rather than recomputing the whole batch. CSV exports for students, attendance, and
performance, all faculty-scoped.

### 5.10 `certification`
**Models:** `Certificate`, `CertificateFollowUp`.

A student enters their Certificate ID per completed enrolment. MIS/Admin get a paginated follow-up
board with status, reminder counts, and last-reminder timestamps. **Weekly reminders are fully
automatic** (cron) — there is deliberately no manual "send now" button or endpoint.

### 5.11 `escalations`
**Model:** `Escalation` (kind, student, batch, reference id — unique per triple).

Two rules: **incomplete test** (open test, no attempt) and **low attendance** (<50%). Each alert
fires **at most once**, guaranteed by the unique constraint plus batched
`bulk_create(ignore_conflicts=True)` writes. Notifies the student and/or faculty, counselors, MIS as
appropriate. Runs on cron or on demand, and the ledger is reviewable **batch-wise** in the UI.

### 5.12 `engagement` and `upsell`
**Models:** `LinkedInFollow`, `GoogleReview`, `CourseNextPlan`, `UtilityLink`.

Non-blocking student prompts, shown one at a time and **sequenced after** the welcome check:
- **LinkedIn follow** — post-login until confirmed
- **Google review** — at course completion
- **Course next-plan** — what the student wants to learn next, exported to Admin/MIS

Each has status tracking, dismissal ("Later" = this session only), and cron reminders with counts.
Reports are filterable **batch-wise**.

**Utility links:** an MIS-curated public notice board (YouTube sessions, resources) rendered on a
public page, with optional MIS-uploaded thumbnails (falling back to derived YouTube thumbnails).

`upsell` is a small views-only module for the honest in-video course-upsell prompt.

### 5.13 `feedback`
**Model:** `Feedback` (student, subject, message, plus registration/batch/course snapshot).

A student sends a private message to management. It is delivered to **every Super Admin** on in-app
+ WhatsApp with the student's context attached, and readable **only** in the Super Admin's private
inbox — not Admin, not MIS. Throttled at **5/hour per student** so the WhatsApp fan-out cannot be
abused.

### 5.14 `notifications`
**Models:** `Notification`, `IntegrationSetting`.

In-app bell with unread count, mark-read / mark-all-read, and **backoff polling** (20s → 5min,
resetting on activity). External channels go through the adapters, queued in production.

**Integration settings** let Super Admin edit each channel's provider, non-secret config JSON, and
secret. Secrets are **encrypted at rest** (Fernet, key derived from `SECRET_KEY`) and never
returned to the client — the API exposes only a `secret_set` boolean. Saving invalidates the config
cache so it takes effect immediately, including for the "send test message" button.

### 5.15 `audit`, `dashboard`, `core`
**`audit`** — `AuditLog` records actor, action, target, metadata, and client IP for every sensitive
operation. Readable by MIS (all) and Faculty (own batches), with date filtering. Super Admin and
Admin deliberately have no access.

**`dashboard`** — one endpoint returning role-shaped real aggregates: student (attendance %,
pending tasks, upcoming tests, login streak, video progress, up-next classes), faculty (batches,
students, unanswered doubts, submissions to grade), ops/SA/Admin/MIS (batch states, certificate
pending, device queue), counselor (active / logged-in / absent today), tech support (forum SLA
counts + pending device requests). The six-week login trend is a **single grouped `TruncWeek`
query**.

**`core`** — the matrix, permissions, pagination (`StandardResultsPagination` + `paginate_rows`),
upload validation, cron locking, retention, crypto, integrations, request-id middleware, uniform
error envelope.

---

## 6. Frontend structure

- `src/app/` — role definitions, route guards (`ProtectedRoute`).
- `src/design-system/` — ~30 shared components (Button, Card, Modal, Toast, Tabs, StatCard,
  TableShell, Skeletons, Paginator, PasswordRules, FileUpload, ProgressRing, LazyChart…) plus motion
  presets and the `cn` helper.
- `src/features/<domain>/` — one folder per domain, each with `api.ts` and its page components.
  28 feature folders mirroring the backend apps.
- `src/features/portal/PortalLayout.tsx` — the app shell: grouped nav filtered by role, animated
  active indicator, mobile drawer, notification bell, profile menu, skip-link, and the mounted
  student prompts.
- `src/features/portal/dashboards/` — one dashboard component per role.
- `src/lib/` — axios client with CSRF + global mutation-error toasts, `useServerTable` (server
  pagination + debounced search), device fingerprinting.

**Routing.** Public: landing, per-role login, `/setup/:token`, `/forgot-password`,
`/utility-links`, 404. Authenticated routes are generated per role from `ROLES`, each gated by an
explicit role `Set` that mirrors the backend matrix.

**Performance.** Every page is `lazy()`-loaded behind Suspense; manual vendor chunks
(react-vendor / motion / query); Recharts isolated into a chart chunk loaded only on dashboards.

**Accessibility & responsiveness.** `jsx-a11y` enforced with zero errors; reduced-motion honoured
globally; wide tables scroll inside `overflow-x-auto`; the shell collapses to a drawer on mobile.

---

## 7. Cross-cutting behaviour

### 7.1 Uniform error envelope
`core/exceptions.py` normalises every DRF error to `{"detail": ..., "errors": ...}` so the frontend
has one shape to render.

### 7.2 Request correlation
`core/request_id.py` puts a request id in a contextvar, a logging filter, and the `X-Request-ID`
response header.

### 7.3 Rate limiting
Global `anon` 60/min and `user` 240/min; `login` 10/min; `feedback` 5/hour (scoped). All
env-tunable. Backed by Redis in production so limits are shared across workers.

### 7.4 Cron safety
`core/cron.py::cron_lock` is a cache-based mutex wrapping every scheduled command, so overlapping
runs skip rather than double-fire.

### 7.5 Config precedence
Provider credentials: **DB (Super-Admin-edited, encrypted) → env/settings fallback**. The `.env`
path remains fully supported and is recommended for the strictest deployments.

### 7.6 Data retention
`purge_old_data` removes only activity data (old audit logs, read notifications) past a configurable
window. It never touches enrolments, attendance, submissions, or certificates.

---

## 8. Scheduled jobs

| Command | Cadence | Purpose |
|---|---|---|
| `send_due_reminders` | every 2–5 min | live-class 60/15-minute reminders |
| `run_escalations` | hourly | incomplete tests + <50% attendance |
| `send_absence_reminders` | daily | students who did not log in |
| `send_certificate_reminders` | weekly | certificate chasing |
| `send_engagement_reminders` | daily | LinkedIn / Google review / next plan |
| `purge_old_data` | weekly | retention sweep |

Plus `seed_demo` for local demo data (idempotent; repairs drifted demo accounts).

---

## 9. Security posture

- Session auth with CSRF; `SameSite=Lax`; secure cookies, SSL redirect, HSTS (1y + preload) in
  production, with fail-fast startup checks on `SECRET_KEY` / `ALLOWED_HOSTS` / `REDIS_URL`.
- argon2 password hashing; Django's full validator set surfaced in the UI on all three password
  screens.
- Optional TOTP 2FA for staff.
- Magic-byte upload sniffing; per-kind size and extension allowlists.
- Provider secrets encrypted at rest; never returned to any client.
- Login enumeration-safe; forgot-password enumeration-safe.
- Client IP recorded on login, setup completion, and every sensitive audited action.
- Content-Security-Policy and related headers documented for the nginx edge.
- Object-level scoping everywhere; submission files owner-or-reviewer only.

---

## 10. Testing

| Layer | Count / tool |
|---|---|
| Backend unit + integration | **309 pytest tests**, **87% branch coverage** |
| Permission regression | parametrized role × action matrix pin |
| Concurrency | duplicate submissions, escalation races, cron lock (real threads) |
| Frontend unit | **35 vitest tests** |
| End-to-end | **12 Playwright specs** against real dev servers (`workers: 1`) |
| Load | Locust scenarios — browsing, schedule burst, streaming |

E2E covers the named money-flows (enrol → setup → login, doubt lifecycle, test/task submit → grade,
device block → approve, complete → certify) plus the Procedure-v2 features (feedback → Super Admin
inbox, Colab test submit → grade).

CI runs the backend gates against **PostgreSQL 16**.

---

## 11. Deployment shape

nginx (TLS, serves `frontend/dist/`, internal `X-Accel` media alias, security headers) → gunicorn
(2×CPU+1) → Django; PostgreSQL 16; Redis; `manage.py qcluster` under systemd; cron for the six
commands; nightly `pg_dump`; Sentry DSN; health endpoint at `/api/v1/health/`.

Full runbook: `docs/DEPLOYMENT.md`.

---

## 12. Measured performance

From an actual local Locust run (`docs/LOADTEST.md`, 30 users / 30s): authenticated reads are
12–29 ms median (dashboard 29 ms / 380 ms p95, videos 16 ms, notifications 12–15 ms); login is
~0.8 s by design (argon2). **Caveat stated in the doc:** this was SQLite on a single dev-server
process, not a staging benchmark — re-run against Postgres + gunicorn before quoting SLAs.

---

## 13. Honest limitations — read before reviewing

These are deliberate and documented in code comments and UI copy. Please do not "fix" them by
overstating capability:

1. **MAC addresses cannot be captured by a web application.** Browsers do not expose them. Device
   identity is a **FingerprintJS visitorId** plus the client IP on audit rows. This is a strong
   deterrent against casual account sharing, **not** a hardware-level lock.
2. **"View-only" notes are a deterrent, not DRM.** Inline render, no download affordance,
   right-click suppressed — but the browser ultimately receives the bytes. Screenshots and devtools
   remain possible.
3. **The video watermark is likewise a deterrent**, not enforcement.
4. **Provider credentials in the DB are a convenience, not a hardening measure.** They are
   encrypted at rest and SA-gated, but the `.env` path is still recommended for the strictest
   deployments.
5. **Email is intentionally non-unique** (one account per course per person); ambiguous email
   logins fall back to the Registration ID.
6. **Client-side route/nav gating is cosmetic.** The server-side matrix is authoritative on every
   endpoint.
7. **~40 plain `APIView`s** return hand-built dicts, so the OpenAPI schema lists them without typed
   request/response bodies. The schema generates with zero warnings; this is a known cosmetic gap.
8. **Nothing has run on a production VPS yet.** Postgres/Redis/nginx/X-Accel/qcluster/Sentry/backup
   restore are configured and documented but not yet exercised on real infrastructure.

---

## 14. Conventions a reviewer should hold this code to

1. **Never hardcode a role check in a view or component.** Add or reference an `Action` in the
   matrix.
2. **Any matrix change must update `tests/test_permissions.py` in the same commit.**
3. **UI hiding is never sufficient** — every permission must also be enforced server-side.
4. **Model changes ship reversible migrations with safe defaults**; no dropping columns with live
   data without a back-fill.
5. **Every "at most once" rule is backed by a DB constraint**, not just an application check —
   and the create path must be race-safe (`get_or_create` / `bulk_create(ignore_conflicts=True)`,
   not check-then-create).
6. **All file serving goes through `content.delivery.deliver()`** — no new `FileResponse` or
   private `_stream` imports.
7. **List endpoints that can grow must paginate server-side**; the frontend must not fetch a
   large page and slice it client-side.
8. **Use "Registration ID"** in UI copy, **"MIS Executive"**, and the existing **"Counselor"**
   spelling.
9. Terminology and honesty: do not describe deterrents as guarantees.
