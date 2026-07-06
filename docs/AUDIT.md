# Advantage Pro LMS Full Production Audit

> Audited against the *Revised Operating Procedure* (source of truth). Scores are graded
> against a top ed-tech production bar, not effort. Facts verified in code; file paths cited.

## 1. Executive Summary

Functionally complete, well-tested Django+DRF / React+Vite LMS that closely follows the
operating procedure. Strongest assets: single source-of-truth RBAC matrix
(`backend/core/permissions_matrix.py`) enforced server-side and pinned by parametrized tests;
~196 passing backend tests; atomic all-or-nothing student import; two-step OTP setup/reset
(HMAC'd codes, expiry, attempt caps); clean domain-driven app layout with a ports-and-adapters
seam for email/SMS/WhatsApp/storage; CI running the suite on PostgreSQL.

Weakest axis is **scalability under load**, not correctness: no API pagination, several
O(N×queries) hot paths (`performance/services.py:batch_performance`,
`reports/views.py:AttendanceReport`, `escalations/services.py`), synchronous notification
fan-out inside request cycles (no queue), and video streamed through Django workers
(`content/views.py:_stream`). Security fundamentals are solid; device policy and watermarking
are honest deterrents, not enforcement. A few documented features exist only as matrix entries
with no endpoint (suspend user, change role); the forum lacks the image/file attachments the
doc promises.

**Verdict: fix incrementally. Do not rewrite.**

## 2. Requirement Alignment Score — 88/100

Implemented and verified: role-bound portals ×7, batch-centric everything, Registration ID as
recognition ID, Admin-only batch create/assign, MIS/CO attendance follow-up, login-based
 notes/tests/tasks, TS forum answer+remind+escalate, audit access MIS+FAC only, video closure
AD+MIS, weekly cert reminders + MIS follow-up, LinkedIn/Google/next-plan flows, two-step forgot
password, staff/Counsellor creation. Deductions: forum attachments/photos missing
(`forum/models.py:Thread` text-only); suspend/deactivate + change-role have matrix actions but
no endpoint/UI; cancellation "≥1 day before" notified but not enforced; employment details have
no update UI; two user-approved deviations (batch delete = Admin; SA keeps read access).

## 3. Production Readiness Score — 68/100

Green: CI (ruff/black/mypy/pytest on Postgres 16 + FE gates), pinned requirements, env-driven
config with prod fail-fast, upload validation, retention job, logging, optional Sentry, deploy
runbook, idempotent cron commands. Red: no pagination; no background worker (all notifications
synchronous — `notifications/services.py:notify_many`); media on app disk streamed by app
workers; console-only providers (OTP email/SMS undeliverable until adapters wired); SQLite in
dev; throttling per-process unless `REDIS_URL` set.

## 4. Architecture Score — 82/100

Green: 15 domain apps, services modules, adapter registry (`core/adapters/`), central matrix +
`MatrixPermission`, FE feature folders + real design system + route-level code splitting.
Deductions: business logic sometimes in views; `accounts/views.py` ~500 lines (login+setup+
password+devices+staff — split it); `performance/services.py` N+1; no task-queue abstraction;
FE tests ≈ one file; stale docstring in `accounts/device.py`.

## 5. UI/UX Score — 72/100

Green: coherent light-blue token system; consistent SectionHeading/TableShell/EmptyState/
StatCard/Badge across ~24 pages; role dashboards on real data; skeletons; animated shell;
mobile drawer; reduced-motion; notifications dropdown; drag-drop upload. Deductions: inner
pages visually thin (addressed in the richness pass); no table search/filter/sort/pagination
UI; toasts on few mutations (now global error bridge); a11y unaudited (axe); SetupPage plain
(now restyled).

## 6. Security Score — 78/100

Strong: Argon2id; role-bound login with generic errors; HMAC OTPs w/ caps; session+CSRF
(SameSite=Lax); DRF throttling incl. login 10/min; matrix pinned by tests; object-level scoping
verified (reports `_batch_for`, forum/content/attendance querysets); append-only AuditLog; prod
fail-fast on secrets; upload allowlists; uuid4 storage keys behind gated endpoints. Weaknesses
in §13.

## 7. Performance & Scalability Score — 55/100

Honest weak spot. `batch_performance()` ≈5 queries **per student** (leaderboard, `/performance/`,
CSV, dashboards) → ~5k queries for a 1k-student batch; all list endpoints unpaginated;
`LiveClassViewSet.create/cancel` + `run_escalations` send email+SMS+WhatsApp per student
in-request; `content/views.py:_stream` occupies a gunicorn worker per viewer; SQLite dev masks
contention. Mitigants: code-split FE, lazy charts, Redis-ready cache, idempotent crons, indexes.

## 8. Critical Issues

| Issue | Area | Severity | Why it matters | Recommended fix |
|---|---|---|---|---|
| No pagination on any list API | Backend | **Critical** | Unbounded lists → slow pages, memory spikes, timeouts | Global `PageNumberPagination` (25–50) + FE pagers |
| N+1 aggregation (`performance/services.py`, `reports/views.py:AttendanceReport`, `escalations/services.py:_escalate_low_attendance`) | Backend/DB | **Critical** | 1k-student batch ≈ 5k queries/request; cron degrades platform | Set-based `annotate` over TestAttempt/TaskSubmission/VideoProgress/AttendanceEvent |
| Synchronous notification fan-out (`notify_many` in liveclasses create/cancel, escalations, reminders) | Backend | **Critical** | 500-student class schedule = 1.5k provider calls in-request → timeout; no retry | Queue (django-q2/Celery+Redis); enqueue per-user sends, retry/backoff |
| Video streamed by app workers (`content/views.py:_stream`) | Performance | **Critical** | ~8–12 concurrent viewers exhaust gunicorn workers | Object storage + signed URLs (`StorageAdapter.url()` contract exists); nginx X-Accel interim |
| Provider adapters are console stubs | Deploy | **Critical (launch blocker)** | OTP/notifications can't reach real users | SMTP + SMS/WhatsApp adapters; set `LMS_*_ADAPTER` |
| Client-supplied device fingerprint (`lib/device.ts`) | Security | **High** | Anti-sharing bypassable by copying localStorage | FingerprintJS + server drift heuristics; market as deterrent |
| Suspend/deactivate + change-role: matrix-only, no endpoint | Requirements | **High** | Documented day-one workflows missing | Endpoints gated by SUSPEND_*/CHANGE_USER_ROLE + Staff UI + notify |
| Forum lacks attachments/images (doc §15) | Requirements | **High** | Students can't share screenshots | `ThreadAttachment` reusing `core/uploads`; gated fetch; FE picker |
| Login throttle per-process without Redis | Security | **Medium** | 10/min × N workers | Fail-fast in prod without `REDIS_URL` |
| MIME trusted from client (`core/uploads.py`) | Security | **Medium** | Spoofed type passes | Magic-byte sniffing (python-magic) |

## 9. Frontend Audit

Stack: React 18 + Vite + TS + Tailwind + TanStack Query + framer-motion + Recharts (lazy) +
lucide. Feature folders (`src/features/*` = api.ts + page); shared kit `src/design-system/`;
guards in `App.tsx` route Sets + `PortalLayout` NAV (UI-only; server authoritative).

Working: role dashboards on real `/dashboard/` aggregates (count-ups, sparkline, charts,
up-next); shell (grouped nav, active pill, workspace card, profile menu, drawer); code
splitting (entry ~64 kB, vendors split, charts own chunk); skeletons; EmptyState; ErrorBoundary;
reduced-motion; learner-POV login/landing.

Gaps: data-dense pages lack search/filter/sort/pagination + sticky headers (blocked partly on
backend pagination — client-side toolbar shipped as interim); some mutations still silent
(global axios error-toast bridge added); FileUpload now on Enrolment/Content/Tasks; a11y needs
an axe pass (skip-link added, select labels partially); tablet form reflow partial.

Direction (implemented in richness pass): icon+tint+delta StatCards, ProgressRing,
status-rail Task cards, timeline Live cards, table toolbar with client search+pagination,
toast-on-mutation, hero geometry from logo, 8-pt spacing, 32/20/16/14/11-caps type scale.

## 10. Backend Audit

Strong: matrix + `get_required_action()` per action; scoping consistent
(`content/access.py:accessible_batch_ids`, forum `_forum_batch_ids`, attendance
`_resolve_batch`, reports `_batch_for`); atomic import (`enrollments/importer.py`); OTP
machinery shared by setup+reset; audit logging on sensitive actions; unique constraints kill
double-submit races; idempotent reminder dedupe; upload allowlists.

Flaws: (1) no pagination; (2) fat `accounts/views.py` — split into
`views/{auth,setup,password,devices,staff}.py`; (3) sync fan-out → queue; (4) N+1 aggregates;
(5) inconsistent error envelope; (6) sparse view-level logging (add request-id middleware);
(7) minor race in `escalations._already/_mark` (use `get_or_create`); (8) stale device.py
docstring; (9) `icontains` search fine now, FTS later; (10) no provider retry (queue solves).

## 11. Database Audit

Schema good: UUID user PKs; explicit TextChoices state machines; business-rule uniqueness
(registration_number, student+batch, test/task+student, attendance triple, next-plan);
deliberate indexes (attendance `(batch,source,date)`, notification `(recipient,kind)` +
`(created_at)`, status fields, audit indexes).

Findings: Registration ID model consistent (new course → new account by design; add nullable
`person_ref` later if a person-level view is wanted). **Hard deletes cascade certificates** —
batch delete would erase legal records: block deletion when certificates exist, or archive
(`is_archived`). Retention job preserves academic/legal data (365/180 defaults). Wrap batch
transition + video-closure in one `transaction.atomic`. Postgres-ready; consider
`(student,batch,source,date)` composite on AttendanceEvent and `(student,completed)` on
VideoProgress at scale.

## 12. Architecture Audit

Modular monolith, right-sized. Debuggable: yes (permission bugs localize to matrix; feature
bugs to one app pair). Scales with features: yes. Team-ready: yes after: split
`accounts/views.py`; extract set-based `performance/aggregates.py`; add
`notifications/dispatch.send_async()` over a queue; extract FE `DataTable`. Oversized files:
`accounts/views.py`, `PortalPage.tsx` (~450, splits per role), `content/views.py`
(stream+revoke concerns), `App.tsx` (route boilerplate, acceptable).

## 13. Security Audit

| Finding | Severity | Detail |
|---|---|---|
| Client-supplied device fingerprint | High | `lib/device.ts` value copyable; policy = deterrent; add FingerprintJS + server signals |
| No async/queue → OTP delivery has no retry | High (operational) | Transient SMTP failure silently drops setup email |
| MIME trusted from client | Medium | Add magic-byte sniffing |
| Throttles per-process w/o Redis | Medium | Enforce `REDIS_URL` in prod |
| No staff 2FA at login | Medium | Two-step exists for setup/reset only; consider TOTP for staff |
| Watermark client-side | Medium (accepted) | Overlay removable via devtools; framed honestly as leak-tracing |
| Django admin exposed at `/admin/` | Low | Superuser+Argon2; IP-allowlist advisable |
| IDOR sweep | Pass | Scoping verified + tested (forum/content/attendance/reports/devices/submissions) |
| XSS/SQLi/CSRF | Pass | React escaping, ORM-only, CSRF + CORS pinned |
| Secrets | Pass | No secrets in repo; prod refuses dev key |
| Two-step flows | Pass | Email→phone enforced; hashed, single-use, capped codes |

## 14. Performance Audit

Fix order: (1) `batch_performance` set-based rewrite (feeds board, report, dashboards);
(2) AttendanceReport + `_escalate_low_attendance` grouped aggregates; (3) global pagination;
(4) queue for fan-out; (5) media offload (signed URLs / X-Accel) — the #1 concurrency fix;
(6) notification refetch backoff; (7) wrap batch transition atomic + cron overlap lock;
(8) cap import size (~5k rows).

## 15. Design System Recommendation

Logo-derived: azure `#00A0E0` primary (hover `#007AB0`), royal `#163A8C`, sky tints
`#E6F6FD/#F0F8FE`, semantic green/amber/red, logo red/yellow sparingly (streaks/alerts).
Inter or system stack; 32/24/20/16/14/12+11-caps. Buttons: solid azure/soft/ghost/danger-soft,
44px forms. Cards: white, 1px `#D6EBF8`, radius 16–20, shadow-card, hover-lift when clickable.
Tables: TableShell + toolbar (search/filter/sort), 25/page. Widgets: StatCard v2 (tinted icon,
delta, sparkline), ProgressRing, timeline, leaderboard medals. States: per-layout skeletons,
friendly empties, toast every mutation, inline field errors. Motion: ≤400ms transform/opacity,
count-ups, draw-ins, pill slides, `reducedMotion="user"`. 8-pt spacing; sidebar 264; topbar 64;
content pad 32; max 1400.

## 16. Module-by-Module Improvement Plan

| Module | Current Problem | Required Change | Priority | Complexity | Suggested Smaller-Model Prompt |
|---|---|---|---|---|---|
| Pagination (BE+FE) | None anywhere | Global DRF PageNumberPagination(25) + FE pagers | P0 | M | "Add DRF PageNumberPagination (page_size 25) in config/settings/base.py; update features/{enrollments,forum,notifications,staff,activity} api+pages to consume {count,results} with a pager. No auth changes." |
| Performance aggregates | N+1 | `performance/aggregates.py` set-based; same shapes; tests pass | P0 | L | "Rewrite batch_performance/student_summary callers to grouped ORM queries over TestAttempt/TaskSubmission/VideoProgress/AttendanceEvent; keep return shapes; test_performance/test_attendance/test_escalations must pass." |
| Background queue | Sync fan-out | django-q2 + Redis; `send_async`; swap call sites; retry=3 | P0 | L | "Introduce django-q2; create notifications/dispatch.send_async enqueuing per-user notify; replace notify_many in liveclasses/views.py, escalations/services.py, mgmt commands." |
| Media delivery | App-worker streaming | S3-compatible adapter + presigned GET; play authorizes then redirects | P0 | L | "Implement core/adapters/s3.py (boto3 presigned 15min) per StorageAdapter; VideoViewSet.play redirects to signed URL when supported; local keeps streaming." |
| Providers | Console stubs | SMTP + SMS + WhatsApp adapters via env | P0 (deploy) | M | "Write core/adapters/smtp.py and msg91.py implementing base adapters; env config; no call-site changes." |
| Auth & onboarding | Fat views file | Split accounts/views.py package | P1 | M | "Split accounts/views.py into views/{auth,setup,password,devices,staff}.py preserving URL names; pytest green." |
| Suspend/role-change | Matrix-only | Endpoints + Staff UI + notify + audit | P1 | M | "Add user suspend/reactivate + change-role endpoints gated by SUSPEND_*/CHANGE_USER_ROLE via MatrixPermission; email 'Account suspended'; buttons in StaffPage; tests like test_staff_accounts.py." |
| Forum attachments | Text-only | ThreadAttachment + gated fetch + FE picker | P1 | M | "Add forum attachments: model+migration, reuse core/uploads validate_upload('document'), gated /attachments/{id}/ respecting _forum_batch_ids, FE file chip in ForumPage." |
| Batch mgmt | Non-atomic transition; cascade deletes certs | atomic + block delete w/ certificates | P1 | S | "Wrap transition+VideoAccessRevocation in transaction.atomic; destroy returns 409 if batch has Certificates; tests." |
| Import cap | Unbounded rows | Reject >5000 rows | P2 | S | — |
| Student portal UX | Thin cards | StatCard v2 / ProgressRing / status-rail Task cards / FileUpload submit | P1 | M | (shipped in richness pass) |
| Faculty portal | Default inputs | FileUpload on Content; to-grade filter | P2 | M | (FileUpload shipped) |
| Attendance rule | Calendar-day denominator | `ATTENDANCE_COUNT_WEEKENDS` env option | P1 (decision) | S | "Add env flag; expected_days skips Sat/Sun when false; tests." |
| Live classes | <24h cancel allowed | Require confirm_short_notice + record | P2 | S | — |
| Device policy | Spoofable ID | FingerprintJS visitorId swap | P2 | M | "Replace getDeviceId body with FingerprintJS OSS dynamic import; keep async signature." |
| Video access | Restore has no UI | MIS restore button | P2 | S | — |
| Audit/activity | Capped 200 | Paginate + date filter | P1 | S | (with pagination module) |
| SA settings | Code-defined matrix | DB-backed editable matrix later | P3 | L | — |
| UI polish | "Too simple" | §15 execution | P1 | L | (largely shipped) |

## 17. Implementation Roadmap

**Immediate:** providers; enforce Redis in prod; real LinkedIn/Google URLs; certificate-protect
batch delete; atomic transition. **Phase 1 (1–2 wks):** pagination; aggregates rewrite; queue;
split accounts views. **Phase 2 (1–2 wks):** suspend/role-change; forum attachments; attendance
working-days decision; audit filters; counsellor note UI. **Phase 3 (1 wk):** S3+signed URLs
(or X-Accel); magic bytes; FingerprintJS; monitoring + backup rehearsal. **Phase 4 (1–2 wks):**
remaining UI polish; axe a11y pass; Playwright E2E; Locust load tests.

## 18. Testing Strategy

Have: 196 backend tests incl. full matrix pin. Missing: FE (one file), E2E, load, concurrency.
Priorities: Playwright E2E for the five money-flows (enrol→setup→login; doubt lifecycle; device
block→approve; test/task submit→grade; complete→certify — DEMO_FLOWS.md is the spec); Vitest
for guards/forms/FileUpload; concurrency (parallel submits, duplicate escalation runs); Locust
(200 browsing, 500-student schedule burst, 8 concurrent streams pre/post offload). Keep the
matrix test as the permanent regression gate; new endpoint = new test in the same style.

## 19. Deployment & Monitoring Plan

Hostinger **VPS (KVM)** required — shared hosting cannot run Django/Postgres/Redis/cron. nginx
(TLS, dist/, media X-Accel) → gunicorn (2×CPU+1) → Django; Postgres 16 (nightly pg_dump, weekly
restore rehearsal, 7/4 retention); Redis (cache/throttle + queue broker); django-q2 worker via
systemd; cron = six documented commands. **Email via Hostinger SMTP ✔; SMS/WhatsApp are NOT
Hostinger products — third-party (MSG91/Twilio, Meta WhatsApp Cloud) required.** No Hostinger
object storage — VPS disk first, Cloudflare R2/Backblaze B2 when video grows. Sentry env-gated;
UptimeRobot on /api/v1/health/; alert on 5xx + queue depth. Rollback = last 3 releases +
DB restore; reversible migrations in review. CI/CD: existing Actions + tag-deploy job.

## 20. Final Recommendation

Fix incrementally — a rewrite destroys value. Domain model, RBAC and tests are good; every
critical gap is additive and independently shippable (ideal for smaller-model tasking). Follow
§17 order: providers+Redis (launch blockers) → P0 scalability quartet → requirement gaps →
polish. Never market device-binding/watermarking as hard enforcement — keep the doc's honest
framing.
