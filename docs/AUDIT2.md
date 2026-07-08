# Advantage Pro LMS — Production Audit v2

> Audited at commit `81123d7` (Procedure v2 Phase 1 complete). Every claim below was
> verified by running the suites/gates on this working tree today — evidence in §2.
> Supersedes nothing in AUDIT.md; this is the follow-up sweep after the audit-v1 fix
> program (P0–P4 all closed) and Phase 1 of the Procedure-v2 requirements.

---

## 1. Executive summary

The codebase is in materially better shape than at audit v1: every P0–P4 item from
AUDIT.md §16 is implemented and tested (pagination, set-based aggregates, async
notification queue, X-Accel media offload, real provider adapters, magic-byte upload
sniffing, suspend/role endpoints, forum attachments, editable permission matrix, staff
TOTP 2FA, request-id logging, cron locks, error envelope, concurrency tests, E2E suite,
Locust scenarios). The RBAC matrix remains the architectural spine and is pinned by a
parametrized regression test that was updated in lock-step with Phase 1's procedure
changes.

**Current verified state: 255 backend tests, ruff/black/mypy clean, zero missing
migrations, FE tsc/lint/build clean with 30 unit tests, and 10/10 Playwright E2E flows
green against real dev servers.** Production security posture is sound: all six Django
`security.W*` deploy warnings visible in dev are explicitly resolved in
`config/settings/prod.py` (SSL redirect, HSTS 1y + preload, secure cookies, DEBUG off)
with fail-fast guards on SECRET_KEY / ALLOWED_HOSTS / REDIS_URL.

This sweep found **no critical or high defects**. It found three genuine mediums (one
functional — the import template's `faculty` column silently does nothing; one
behavioral edge — weekend absentee reminders ignore the weekend flag; one dev-toolchain
dependency advisory) and a handful of lows. All are catalogued in §3 with fixes, and the
functional ones are folded into the Phase 2–7 execution plan (§5) at the point where
their module is already being touched.

**Verdict: ship-ready pending deploy-day configuration (§7). Continue the phased
Procedure-v2 build on this foundation.**

---

## 2. Verification evidence (run on this tree, this commit)

| Check | Result |
|---|---|
| Backend test suite (`pytest`) | **255 passed**, 0 failed |
| Lint / format / types (`ruff`, `black --check`, `mypy`) | All clean (199 files) |
| Migration drift (`makemigrations --check --dry-run`) | No changes detected |
| Django system check (`manage.py check`) | 0 issues |
| Django deploy check (dev settings) | 6 `security.W*` warnings — **all explicitly resolved in prod.py**; 13 `drf_spectacular.W001` schema-hint warnings (cosmetic, §3-L4) |
| Frontend types (`tsc --noEmit`) | Clean |
| Frontend lint (eslint + jsx-a11y) | 0 errors (7 known fast-refresh warnings, accepted baseline) |
| Frontend unit tests (Vitest) | **30 passed** (7 files) |
| Production build (`vite build`) | OK — entry ~67 kB, code-split per page, charts isolated |
| E2E (Playwright, real servers, workers=1) | **10/10 passed** (smoke ×4 + five money-flows) |
| `npm audit --omit=dev` (ships to users) | **0 vulnerabilities** |
| `npm audit` (dev toolchain) | 5 (1 critical / 1 high / 3 moderate) — all in vite/vitest/esbuild dev servers, §3-M3 |

---

## 3. Findings

No criticals. No highs.

### Medium

**M1 — Import template's `faculty` column is validated but never used.**
`enrollments/importer.py` requires a `faculty` column, errors on unknown names
(line ~146), then `do_import()` drops the value — no faculty is assigned to anything.
The template therefore implies an assignment that never happens; demo flows only work
because `seed_demo` separately assigns faculty1 to FS-DEMO. *Fix (folded into Phase 2,
which reworks faculty assignment anyway): either assign the named faculty to the row's
batch as soft faculty on import, or drop the column from REQUIRED and the template.
Given req 9/13 make assignment schedule-conflict-checked, the honest fix is to drop the
column and let Admin assign through the batch UI where the conflict check lives.*

**M2 — Weekend absentee flows ignore `ATTENDANCE_COUNT_WEEKENDS`.**
`attendance/services.py`: `expected_days` / `login_present_days` /
`batch_attendance_summaries` correctly skip weekends when the flag is off, but
`absentee_students`, `daily_roster` and `remind_absentees` do not. With the flag off and
the daily cron running 7 days/week, a Saturday run marks the entire roster absent and
messages every student "we missed you today". *Fix (small): short-circuit
`remind_absentees` (and annotate the daily roster) when the flag is off and the day is
Sat/Sun. Scheduled in Phase 6 alongside the other attendance-adjacent report work.*

**M3 — Dev-toolchain npm vulnerabilities (does not ship).**
`vite` (high: dev-server path traversal), `vitest` (critical: `--ui` server arbitrary
file read — mode never used here), `esbuild`/`@vitest/mocker`/`vite-node` (moderate).
All five are devDependencies; **the production bundle audits clean** (`--omit=dev` = 0).
*Fix: major-version upgrade (vite 6/7 + vitest 3) as a standalone tooling PR after the
feature phases — breaking-change surface (config, plugin API) doesn't belong mixed into
feature commits. Until then the exposure is limited to developer machines running the
dev server.*

### Low

**L1 — Two file endpoints bypass the X-Accel delivery seam.**
`assessments/views.py` imports the private `_stream` from `content.views` for task
submission files, and `forum.AttachmentDownloadView` serves via `FileResponse` — both
app-stream even in prod, unlike videos/materials which hand off via
`content._deliver`/X-Accel. Impact is small (task files/attachments are ≤25 MB docs, not
hour-long videos), but it is (a) an architecture inconsistency, (b) a private cross-app
import. *Fix: export `_deliver` as a public `content.delivery.deliver()` and use it in
all three places — scheduled in Phase 4, which touches file viewing anyway.*

**L2 — `seed_demo` cannot repair drift in existing rows.**
`get_or_create` everywhere means a manually-edited dev account (e.g. admin1's role,
found drifted to `mis` during E2E work) is never corrected by re-running the seed,
though DEMO_GUIDE.md implies re-seeding resets state. *Fix: use `update_or_create` for
the role/status fields of the fixed demo accounts, keeping student passwords untouched.*

**L3 — Manual certificate-reminder trigger still exists (req 19).**
The weekly auto-cadence is already correct (`run_certificate_reminders` is cron-driven,
at-most-weekly per student, counted per enrolment) — but `RunCertRemindersView` +
the MIS "send reminders" button remain. *Fix: remove the FE button and endpoint; keep
the report. Scheduled in Phase 6 (it is req 19 verbatim).*

**L4 — 13 drf-spectacular `W001` warnings.** SerializerMethodFields and UUID path params
lack type hints, so `/api/v1/docs/` renders those fields as bare strings. Cosmetic; fix
opportunistically with `@extend_schema_field` when each serializer is next touched.

**L5 — `Course.fees` serializes as a string** (DRF DecimalField default). The FE handles
it; documenting so no client ever does arithmetic on it without parsing.

### Accepted / by-design (unchanged from audit v1, re-verified)

- Device binding and the moving video watermark are **deterrents, not enforcement** —
  a determined user can spoof fingerprint signals or screen-record. Framed honestly in
  code comments and UI copy.
- **"View-only" notes (upcoming req 2) will be the same class of deterrent**: inline
  render, no download affordance, right-click suppressed — but a browser ultimately
  receives the bytes; nothing cryptographic prevents capture. Do not market otherwise.
- **MAC addresses cannot be captured by a web application.** Browsers do not expose
  them (req 8's "check MAC captured" is technically impossible on the web). What *is*
  captured after two-step verification: IP address on login/reset-complete/sensitive
  actions and the device fingerprint at login. Gap: `account_setup_completed` audit rows
  lack the IP — being added in Phase 3 alongside the password-rules UI.
- Email is intentionally non-unique (one account per course per person); ambiguous
  email logins fall back to Registration ID.
- Client-side route/nav gating is cosmetic; the server-side matrix is authoritative on
  every endpoint (verified by the pinned matrix test + per-module scoping tests).

---

## 4. Requirements coverage — the 26 Procedure-v2 items

Status after Phase 1 (✅ done & tested · 🔶 partial · ⏳ planned, phase noted):

| # | Requirement | Status |
|---|---|---|
| 1 | Student calendar + reminders on scheduling | ⏳ Phase 3 (immediate notify on schedule already exists) |
| 2 | View-only notes/whiteboard uploads | ⏳ Phase 4 (image uploads already supported) |
| 3a | Forum images/attachments in storage | ✅ (audit-v1 work; inline image rendering lands Phase 4) |
| 3b | Excel/Colab test kinds + submissions | ⏳ Phase 5 |
| 4 | No forum for MIS | ✅ threads/monitor/picker/attachments all closed + tested |
| 5 | Engagement/attendance/reports batch-wise | 🔶 attendance/reports already batch-scoped; engagement filter Phase 6 |
| 6 | TS device notifications; 3h SLA both roles, all see, only FAC+TS respond | ✅ routing, reply gating, SLA fields + overdue badges, tested |
| 7 | MIS gets no device notifications | ✅ tested (silent capability retained) |
| 8 | Password rules shown; MAC/IP capture check | 🔶 IP captured at login/reset; setup-complete IP + rules UI Phase 3; MAC impossible (§3 accepted) |
| 9 | Primary + optional soft faculty | ⏳ Phase 2 |
| 10 | Faculty skills section, shown at assignment | ⏳ Phase 2 |
| 11 | No staff creation on Admin page | ✅ matrix + view + nav/route, tested |
| 12 | SA chooses faculty by skills/certs | ⏳ Phase 2 (same surface as #10) |
| 13 | "Faculty already occupied" conflict block | ⏳ Phase 2 |
| 14 | Batch days + times mandatory | ⏳ Phase 2 |
| 15 | Only SA creates courses (+duration, fees) | ✅ new action/fields/SA page, tested |
| 16–17 | Address & goodies popup + admin register | ⏳ Phase 3 |
| 18 | Mobile friendly | ⏳ Phase 7 (shell already responsive; sweep pending) |
| 19 | Auto-only certificate reminders | 🔶 weekly auto-cadence already live; manual button removal Phase 6 (§3-L3) |
| 20 | Feedback → SA WhatsApp | ⏳ Phase 3 |
| 21 | SA-editable third-party connections | ⏳ Phase 6 |
| 22 | Utility-link image thumbnails + drop brown | ⏳ Phase 4 |
| 23 | Escalations batch-wise | ⏳ Phase 6 |
| 24 | Started-batch delete = SA only | ✅ tested (draft=AD, started=SA, cert-guard intact) |
| 25–26 | No faculty removal from ongoing batch | ✅ suspend + role-change guarded with batch list in the error, tested |

---

## 5. Execution approach for the remaining phases

Ground rules that keep this safe: one phase = one commit; every phase runs the full
backend suite + FE gates before commit; E2E after any phase that touches a money-flow;
the matrix pin test is updated in the same commit as any matrix change; model changes
ship reversible migrations with defaults so existing rows survive.

**Phase 2 — Batch scheduling & faculty (reqs 9, 10, 12, 13, 14 + fixes M1).**
Design decisions: `Batch` gains `class_days` (JSON list of `mon…sun`),
`class_start_time`, `class_end_time` — *serializer*-mandatory on create so existing rows
(empty defaults) stay valid. `primary_faculty` is a FK that is **auto-included in the
existing `faculty` M2M**, so every faculty-scoped query in content/forum/attendance/
notifications keeps working untouched; "soft faculty" = M2M minus primary. Conflict
check: `conflicts(faculty, days, start, end, exclude_batch)` = non-completed batches
where day-sets intersect AND time ranges overlap (`startA < endB and startB < endA`);
enforced on batch create (primary) and assign-faculty (soft), returning "«name» is
already occupied on «days» «time» by «batch»". New `FacultyProfile` (OneToOne: skills,
certifications) editable from a faculty "My profile" page; `FacultyListView` +
StaffPage expose skills/certs wherever a faculty is being chosen. Importer: drop the
dead `faculty` column (M1).

**Phase 3 — Student-facing (reqs 1, 16, 17, 20, 8).**
Calendar: month-grid page fed by the existing live-class list + the batch weekly
schedule; per-class "Add to Google Calendar" uses the zero-OAuth
`calendar.google.com/calendar/render?action=TEMPLATE` URL (no API keys, works for any
Google account); immediate reminders already fire on scheduling via notify_many.
Goodies/address: `StudentWelfare` (OneToOne student: address, address_collected,
goodies_received (student-set), goodies_sent (admin-set)); post-login popup asks the two
questions once, collects address when missing, notifies Admin; Admin "Goodies register"
page lists student/address/flags; student page to update later. Feedback: `Feedback`
model (student, subject, message + batch/course snapshot), POST student-only; delivery =
in-app to SA **plus WhatsApp via the existing adapter through the async queue**; SA-only
inbox page; throttled per-user. Password rules: shared `<PasswordRules/>` on setup /
change / reset screens mirroring the four active validators; add IP to the
setup-complete audit row.

**Phase 4 — Content & media (reqs 2, 3a-inline, 22 + fixes L1).**
Promote `_deliver` to `content.delivery.deliver()`; use it for task files + forum
attachments (closes L1). Materials FE: replace open-in-tab with an in-app viewer modal
(images `<img>`, PDFs `<iframe>`) with no download affordance and context-menu
suppressed — deterrent framing per §3. Forum: render image-type attachments inline.
Utility links: optional uploaded thumbnail (multipart, stored via adapter, public
thumbnail endpoint since the board is public) taking precedence over YouTube auto-thumbs;
restyle board from amber/brown to the sky/azure palette.

**Phase 5 — Test kinds (req 3b).**
`Test.kind` = `mcq` (default) | `file` (Excel attached) | `colab` (external URL);
create-serializer requires exactly the matching payload. Students: MCQ unchanged; file
kind exposes the sheet + accepts a filled-file upload; colab opens the link + accepts a
completion submission. Reuse `TestAttempt` with nullable file fields so the
one-attempt-per-student constraint keeps holding; faculty submissions view lists/serves
files (via the Phase-4 deliver()). Excel test sheets are intentionally downloadable —
the no-download rule (req 2) is for notes/whiteboard content, and a fill-in sheet cannot
be filled without the file.

**Phase 6 — Reports & ops (reqs 5, 19, 21, 23 + fixes M2, L3).**
Escalations: nullable `batch` FK populated at creation (test→test.batch,
attendance→batch), `?batch=` filter + FE selector; engagement report gains the same
batch filter. Certificate reminders: delete the manual endpoint/button (auto cron
remains the only trigger); report stays. Weekend guard in `remind_absentees` (M2).
Integrations: `IntegrationConfig` rows (channel → adapter path + credential fields)
edited from the SA Channels page; the adapter registry and provider adapters read
DB-config-first-then-env through a cached helper with invalidation on save —
**documented caveat: credentials move into the DB; acceptable only because access is
SA-gated and the DB is not world-readable, but the .env path remains supported and
recommended for the strictest setups.**

**Phase 7 — Mobile pass (req 18).**
Checklist sweep, not a redesign (the shell already has the drawer/breakpoints): every
table wrapped in `overflow-x-auto`; multi-column forms collapse ≤`sm`; calendar grid
degrades to a stacked agenda on narrow widths; popups sized `max-w` with padding;
touch targets ≥40px on primary actions; verified against 360px viewport in the E2E
browser + a Playwright mobile-viewport smoke.

---

## 6. Module scorecard (delta since audit v1)

| Area | v1 | Now | Notes |
|---|---|---|---|
| Requirement alignment | 88 | **93** | Phase-1 procedure changes in; Phases 2–7 tracked in §4 |
| Production readiness | 68 | **88** | Queue, offload, providers, pagination, cron locks, request-id, error envelope all landed; remaining gap is deploy-day config (§7) |
| Architecture | 82 | **90** | accounts/views + PortalPage split; dispatch/delivery seams; L1 inconsistency pending |
| Security | 78 | **88** | TOTP 2FA, magic bytes, editable-matrix lockout guard, prod fail-fasts; deterrent items unchanged by design |
| Performance | 55 | **85** | Set-based aggregates, pagination, async fan-out, X-Accel, scale indexes; Locust scenarios written (not yet run against staging) |
| Testing | — | **strong** | 255 BE + 30 FE + 10 E2E + concurrency suite; matrix pinned; load tests scripted |

---

## 7. Deploy-day checklist (unchanged blockers — need the VPS, not code)

1. `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` (Postgres 16), `REDIS_URL` — prod refuses to boot without them.
2. Provider env: `LMS_EMAIL_ADAPTER=core.adapters.smtp.SmtpEmailAdapter` + `EMAIL_*`; `LMS_SMS_ADAPTER=core.adapters.msg91.Msg91SmsAdapter` + `MSG91_*`; `LMS_WHATSAPP_ADAPTER=core.adapters.whatsapp_cloud.WhatsAppCloudAdapter` + `WHATSAPP_*` (SA WhatsApp feedback in Phase 3 rides this).
3. nginx: TLS, serve `frontend/dist/`, `location /protected/ { internal; alias <MEDIA_ROOT>/; }` + `MEDIA_XACCEL_PREFIX=/protected`; IP-allowlist `/admin/`.
4. Processes: gunicorn (2×CPU+1) + `python manage.py qcluster` under systemd.
5. Cron (all overlap-locked): run_escalations, send_absence_reminders, send_certificate_reminders, send_engagement_reminders, send_due_reminders (2–5 min), purge_old_data (daily).
6. Nightly `pg_dump` + a rehearsed restore; Sentry DSN; UptimeRobot on `/api/v1/health/` (returns request-id header for correlation).
7. Delete/replace demo accounts; create the real Super Admin; rotate `student1`'s known demo password.
8. Real `VITE_LINKEDIN_URL` / `VITE_GOOGLE_REVIEW_URL` at FE build time.
9. Set `ATTENDANCE_COUNT_WEEKENDS` per institute policy **after** M2's weekend guard lands (Phase 6) if weekends are excluded.
