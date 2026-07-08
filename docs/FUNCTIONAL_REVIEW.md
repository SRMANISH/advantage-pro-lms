# Advantage Pro LMS — End-to-End Functional & Architecture Review

> Companion to AUDIT2.md, at the same commit (`81123d7`). AUDIT2 verified the gates and
> catalogued findings from a targeted sweep; **this document walks every existing
> functionality end-to-end** (backend flow → API contract → frontend page → tests) and
> consolidates *everything that needs fixing, with the fix approach*, into one register
> (§3) and one execution order (§5).
>
> Baseline evidence (re-verified on this tree): 255 backend tests, ruff/black/mypy
> clean, no migration drift, FE tsc/lint/build clean, 30 unit tests, 10/10 E2E.

---

## 1. Method

Each module below was reviewed as a full path: model → service → view/permission →
serializer contract → FE api module → page/UX → test coverage. "Works" means the flow
was verified in code and is covered by at least one passing test or E2E flow; every gap
found gets an ID (`R-xx`) in the fix register.

---

## 2. Module-by-module functional review

### 2.1 Authentication & sessions — **works, 2 fixes**
Role-bound + unified login (email falls back to Registration ID on ambiguity), generic
error copy, ACTIVE-status gate, login throttle (10/min shared via Redis in prod),
session+CSRF, per-request id echoed in `X-Request-ID`, first-login alert to Admin+MIS,
login-day attendance capture, TOTP second factor for staff (enroll→confirm→login
step-up→password-gated disable; unconfirmed devices never consulted). E2E covers
login/wrong-password; 9 TOTP tests.
→ **R-01** forgot-password start is an account-existence oracle (404 vs 200 tells an
attacker which Registration IDs/emails exist). **R-02** `account_setup_completed` audit
row lacks the client IP (login/reset rows have it).

### 2.2 Two-step setup & forgot password — **works, 1 fix (R-01 shared)**
Email link (48h, single-use) → email OTP → phone OTP → password with Django validators;
HMAC'd codes, expiry, attempt caps, resend limits; reset mirrors setup. DEBUG exposes
`dev_code` for demos only. E2E covers the full setup→login journey.
→ Password *rules* are not displayed on any of the three password screens (planned
req 8) — tracked as **R-03**.

### 2.3 Devices — **works, 1 bug**
First login binds; mismatch blocks + raises a request routed Faculty (in-class) / Tech
Support (outside, notified) / MIS (outside, silent); approve/reject audited; E2E covers
block→approve→login. Post-Phase-1 tests pin the TS routing.
→ **R-04 (bug)** `active_live_class_for_batches()` does not exclude *cancelled*
classes, so a cancelled class still opens the "faculty approves / TS-MIS blocked"
window for its 2-hour duration. One-line fix + test.

### 2.4 Staff administration — **works**
SA-only create/list (two-step setup for new staff), suspend/reactivate
(student/faculty, matrix-gated by target role, login-enforced), SA role change,
ongoing-batch faculty lock with the blocking batch codes in the error. All tested.

### 2.5 Courses & batches — **works, 1 fix**
SA-only course CRUD (duration/fees), Admin-only batch create/edit/assign/lifecycle,
forward-only state machine with atomic completed→video-closure, cert-protected +
state-guarded delete (draft=AD, started=SA). Faculty scoping verified.
→ **R-05** the *batch board* dashboard card for Tech Support doesn't surface pending
device requests (MIS's does) even though TS now owns outside-class approvals — small
dashboard addition alongside req 6.

### 2.6 Enrolment & import — **works, 1 fix**
Template download, all-or-nothing validation with row/field/problem detail, 5k row cap,
atomic import, per-student setup links, resend, roster with pagination + MIS
video-access controls. E2E covers import→setup→login.
→ **R-06** the required `faculty` CSV column is validated then **discarded** —
misleading (AUDIT2-M1). Approach: drop the column from REQUIRED/template; assignment
belongs in the batch UI where Phase 2's conflict check will live.

### 2.7 Content: videos & materials — **works, 1 consistency fix**
Faculty-only upload (magic-byte-sniffed), role-scoped lists, gated play with Range
support, X-Accel offload in prod, per-student moving watermark (deterrent framing),
≥80% completion → attendance event, MIS individual revoke/restore + AD/MIS course-end
closure enforced at play/view.
→ **R-07** task-submission files (`assessments`, via private `content.views._stream`
import) and forum attachments (`FileResponse`) bypass the X-Accel seam — promote a
public `content.delivery.deliver()` and use it in all three places (AUDIT2-L1).

### 2.8 Assessments: tests & tasks — **works, 1 perf note**
MCQ builder → auto-grading with hidden answers, one-attempt constraint enforced at the
DB with a friendly race-safe 400 (concurrency-tested); tasks with deadline types, late
flag, file submissions (validated uploads), grading + student notification, to-grade
filter. E2E covers create→attempt→grade both ways.
→ File-kind/Colab tests are Phase 5 scope (req 3b). `assessments/views.py` will outgrow
one file then — plan the `views/{tests,tasks}.py` split *in* Phase 5 (**R-08**).

### 2.9 Attendance & follow-up — **works, 2 fixes**
Login-based capture (idempotent per student/batch/day), batch roster + daily
logged-in/absent view, shared Counsellor+MIS follow-up status & notes, absence
reminders (cron, deduped per day), weekend-exclusion flag for percentages.
→ **R-09 (bug)** percentages can exceed 100%: completed-batch logins (allowed, for
certification) still write attendance rows and `login_present_days`/
`batch_attendance_summaries` don't bound dates to `start_date..end_date` while the
denominator is capped. Fix: bound the present-day queries to the batch window (2
queries) and stop recording login-attendance rows for completed batches.
**R-10** `remind_absentees`/`daily_roster` ignore `ATTENDANCE_COUNT_WEEKENDS` — Saturday
cron with the flag off would message the whole roster (AUDIT2-M2). Fix: weekend
short-circuit + roster annotation.

### 2.10 Performance — **works, 1 perf fix**
Set-based `batch_performance` (tests/tasks/videos/attendance composite, dense ranks);
per-batch board with faculty scoping; CSV export reuses it.
→ **R-11** `MyPerformanceView` builds the *entire* board per enrolment to show one
student's row — on a 1,000-student batch every student dashboard visit computes 1,000
rows. Approach: cache `batch_performance(batch)` for ~60s (`cache.get_or_set`, key by
batch id + updated-at watermark) — one-line change that also speeds the board page; no
contract change.

### 2.11 Doubt forum — **works (post-Phase-1 rules), Phase-4 polish pending**
Students ask (with attachments); only Faculty/TS reply (server- and UI-enforced); MIS
fully excluded; statuses open→answered→resolved/escalated; TS monitor with SLA counts;
remind-faculty; 3h `hours_waiting`/`overdue` on every list for both responder roles.
Batch scoping tested; attachments gated + spoof-rejected.
→ Inline image rendering for image attachments is Phase 4 (req 3a display). No defects
found.

### 2.12 Live classes — **works, R-04 applies**
Faculty schedule (own batches) → immediate multi-channel notify; student check-in
(records attendance + opens link); 60/15-min deduped reminders via cron;
cancellation with <24h confirm gate + immediate notice.
→ Same cancelled-class window bug as §2.3 (**R-04** — the fix lives here).

### 2.13 Certification — **works, req-19 cleanup**
Student enters Certificate ID per completed enrolment; MIS/Admin follow-up board with
status/notes/reminder counts; weekly auto-reminders (cron, at-most-weekly per student,
counted).
→ **R-12** two manual trigger surfaces remain (CertFollowUp page button *and* an
EscalationsPage "remind" button + `RunCertRemindersView`) — req 19 says auto-only:
remove both buttons and the endpoint, keep the report (AUDIT2-L3, expanded).

### 2.14 Engagement & upsell — **works, batch filter pending**
LinkedIn-follow / Google-review / next-plan popups (dismissable, never block learning),
cron reminders with counts, Admin/MIS report; utility links (MIS-managed, public board);
separate honest in-video upsell prompt.
→ Report is global-only today — batch-wise filter is Phase 6 (req 5). Utility-link
uploaded thumbnails + board restyle are Phase 4 (req 22).

### 2.15 Escalations — **works, batch filter pending**
Incomplete-test + <50%-attendance rules, once-only ledger (race-safe get_or_create),
on-demand run + overlap-locked cron.
→ Batch-wise view is Phase 6 (req 23): nullable `batch` FK populated at creation,
`?batch=` filter, FE selector.

### 2.16 Notifications — **works**
In-app sync (bell with backoff polling, mark-read/all, unread count); email/SMS/WhatsApp
queued via django-q2 with retry; real SMTP/MSG91/WhatsApp-Cloud adapters env-selected;
SA channel test-send.
→ Editable adapter/credential config from the UI is Phase 6 (req 21) — note the
secrets-in-DB caveat already documented in AUDIT2 §5.

### 2.17 Reports, dashboard, activity — **works, 1 low**
Per-batch CSVs (students/attendance/performance) with faculty scoping; role dashboards
on real aggregates (bounded queries verified — the student streak and 6-week trend are
fine); MIS/Faculty activity log with pagination + date filter.
→ **R-13** `/showcase` (design-system demo page) is publicly routed — harmless content
but an unauthenticated, unlisted surface; gate it behind `import.meta.env.DEV` or drop
the route in prod builds.

---

## 3. Consolidated fix register

| ID | Sev | What | Approach | Lands in |
|---|---|---|---|---|
| R-04 | **Medium (bug)** | Cancelled live class still counts as "active" for the device-approval window | `.exclude(status=CANCELLED)` in `active_live_class_for_batches`; test: cancelled class → MIS/TS may approve, faculty may not | **Quick-fix batch** |
| R-09 | **Medium (bug)** | Attendance % can exceed 100 after course end | Bound present-day queries to `start_date..end_date` (2 spots); skip login-attendance writes for completed batches; test | **Quick-fix batch** |
| R-01 | **Medium (sec)** | Forgot-password start reveals whether an account exists | Always 200 with generic "if an account exists, a code was sent"; only include `token`/masked email when real; FE copy handles both | **Quick-fix batch** |
| R-10 | Medium | Weekend absentee reminders ignore the weekend flag | Short-circuit `remind_absentees` on Sat/Sun when flag off; annotate daily roster | Phase 6 |
| R-06 | Medium | Import `faculty` column validated but discarded | Remove from REQUIRED/template/validator; assignment via batch UI (conflict-checked) | Phase 2 |
| R-11 | Medium (perf) | Full board computed per student on /performance/me | 60s cache around `batch_performance` | **Quick-fix batch** |
| R-07 | Low | Task files + forum attachments bypass X-Accel seam | Public `content.delivery.deliver()`; use in 3 call sites | Phase 4 |
| R-12 | Low | Manual cert-reminder triggers (2 surfaces + endpoint) despite auto cadence | Delete buttons + `RunCertRemindersView`; keep report + cron | Phase 6 |
| R-02 | Low | Setup-complete audit row missing IP | Pass `get_client_ip(request)` | Phase 3 |
| R-03 | Low | Password rules not shown on the 3 password screens | Shared `<PasswordRules/>` mirroring active validators | Phase 3 |
| R-05 | Low | TS dashboard lacks pending-device-requests count | Add to `_tech_support()` aggregates + card | Phase 3 (dashboard touch) |
| R-08 | Low (arch) | `assessments/views.py` will outgrow one file with test kinds | Split `views/{tests,tasks}.py` when Phase 5 lands | Phase 5 |
| R-13 | Low | `/showcase` publicly routed | Register route only when `import.meta.env.DEV` | **Quick-fix batch** |
| R-14 | Low (ops) | `seed_demo` can't repair drifted demo accounts (AUDIT2-L2) | `update_or_create` role/status for fixed accounts | Quick-fix batch |
| R-15 | Low (deps) | vite/vitest dev-toolchain advisories (prod bundle clean) | Standalone major-version tooling PR after phases | After Phase 7 |
| R-16 | Info | 13 drf-spectacular W001 schema hints; `fees` serialized as string | `@extend_schema_field` opportunistically; document contract | Opportunistic |

**No critical or high defects found.** Everything above is additive or one-liner-class;
nothing requires redesign.

---

## 4. Architecture review

**Sound and worth keeping exactly as-is:** modular monolith of 16 domain apps with
services modules; the RBAC matrix as single enforcement point (`MatrixPermission` +
pinned parametrized test + DB overrides with lockout guard); ports-and-adapters for
email/SMS/WhatsApp/storage/scheduler with env selection; async boundary in
`notifications/dispatch` (sync in dev, queued+retry in prod); uniform error envelope;
request-id correlation; cache-mutex cron locks; DB-level uniqueness backing every
"at most once" rule (attempts, submissions, escalations, reminders, attendance);
FE feature folders + design system + role dashboards split per file; test pyramid
(255 unit/integration + concurrency + 30 FE + 10 E2E on real servers + Locust scripted).

**Debts, with approach (all mapped in §3):** one delivery seam not yet universal
(R-07); one file that will need splitting when it grows (R-08); one heavy read path
worth a tiny cache (R-11); a dev-only route (R-13); dev-toolchain versions (R-15).
The `upsell` micro-app is views-only — acceptable; fold into `engagement` only if it
ever gains models. No boundary violations beyond R-07's private import; no god modules;
no untested critical paths found.

---

## 5. Execution order (fix plan, end to end)

1. **Quick-fix batch (next commit, ~small):** R-04, R-09, R-01, R-11, R-13, R-14 — the
   two behavior bugs, the enumeration fix, the cheap cache, the dev-route gate, the
   seed repair. Each with a pinning test; full gates before commit.
2. **Phase 2 – Batch scheduling & faculty** (+ R-06) — as specified in AUDIT2 §5.
3. **Phase 3 – Calendar, goodies/address, feedback→SA WhatsApp, password rules**
   (+ R-02, R-03, R-05). Note: goodies/address should *reuse* `Enrollment.address`
   (already captured at import) as the seed value rather than duplicating it.
4. **Phase 4 – View-only viewer, inline forum images, utility thumbnails** (+ R-07).
5. **Phase 5 – Excel/Colab test kinds** (+ R-08 split).
6. **Phase 6 – Batch-wise engagement/escalations, auto-only cert reminders, editable
   integrations** (+ R-10, R-12).
7. **Phase 7 – Mobile pass**, then **R-15** tooling upgrade as its own PR.

Per-phase discipline stays: full backend suite + FE gates + (money-flow-touching) E2E
before each commit; matrix pin test updated in the same commit as any permission change;
reversible migrations with safe defaults.
