# CodeRabbit review prompt — round 2

Round 1 (`docs/CODERABBIT_REVIEW_PROMPT.md`) covered upload safety, auth throttling, production
misconfiguration guards, the RBAC matrix, secret handling, race conditions, feature-reality,
duplication, and CI/docs drift. **Every finding from that round is closed** — see
`docs/PRODUCTION_REVIEW.md` §6 (P-01…P-18). Please do not re-report them.

This round targets what round 1 did **not** examine. The system has been made to work; this
review is about whether it will keep working — under load, under failure, under concurrency,
over time, and in the hands of someone who did not write it.

---

## 0. How to review

- **Verify, don't assume.** Where I assert something below, treat it as a claim to be checked,
  not a fact. I have been wrong: I previously reported an "exploitable path traversal" that
  turned out to be contained by Django one layer down. If my framing is wrong, say so.
- **Severity by consequence.** For each finding, state the concrete failure: the input or
  sequence, and what a user or operator actually experiences. "This is not idempotent" is not
  a finding; "a retried cron sends every student a second SMS" is.
- **Cite lines.** `path/file.py:123`.
- **Distinguish** *bug now* / *bug under load or concurrency* / *maintainability risk* /
  *style*. I will act on the first three.
- If a whole section below is clean, say so explicitly. Silence is ambiguous.
- **Rank by expected cost**, not by how easy the finding was to spot.

---

## 1. Context

Django 5.2.16 + DRF 3.17 modular monolith; 15 apps with models plus 4 model-less aggregator
packages (`dashboard`, `performance`, `reports`, `upsell`). React 18 + TS + Vite SPA.
PostgreSQL in production, SQLite in local dev. Redis for cache/throttle. django-q2 for async
notification fan-out (`sync` inline in dev, `qcluster` in prod). Session-cookie auth (no JWT).

Scale it must survive: a training institute — low hundreds of concurrent students, a few
thousand rows per table, daily cron jobs, bulk CSV enrolment. **Not** a high-throughput
system. Please calibrate: I do not want horizontal-scaling advice, but I do want to know
about anything quadratic, anything unbounded, and anything that breaks on the second run.

Backend tests: 414. Frontend: 43 vitest + 12 Playwright specs.

---

## 2. Found and fixed in this round — please verify the fixes, don't re-find the bugs

I ran the CI pipeline locally before this review and found five real defects. All are fixed;
**check the fixes are actually correct and complete**, since a wrong fix is worse than none:

1. **`X-Forwarded-For` was trusted unconditionally** (`core/utils.py`). nginx uses
   `$proxy_add_x_forwarded_for`, which *appends* the real peer address — so the leftmost entry
   is attacker-written. The old code read the leftmost entry, making audit-log IPs forgeable.
   Worse, DRF's `NUM_PROXIES` was unset, so `get_ident()` returned the *whole* header and a
   client rotating it got a fresh throttle bucket per request — silently defeating the login
   brute-force guard and all verification throttles. Now both derive from
   `settings.TRUSTED_PROXY_COUNT` (default 0). **Check:** is counting from the right correct
   for this topology? Is 0 the right default? Anywhere else reading the header directly?
2. **CSV formula injection** (`reports/views.py::_sanitize_cell`). Exports carry student names
   and follow-up notes and are opened in Excel by staff. **Check:** is the prefix list
   complete, is quote-prefixing the right neutralisation, and are there other export paths
   (openpyxl in `enrollments/`?) with the same exposure?
3. **Suspension did not end an existing session** (`core/authentication.py`). Auth is
   session-based and `UserStatus` was only ever checked at login; no permission class looks at
   it. A suspended account kept full privileges until its cookie expired. **Check:** does
   putting this in the authentication class cover every entry point (admin site, schema
   endpoints, the health check, django-q2 tasks acting on a user)? Any request path that
   bypasses DRF authentication entirely?
4. **9 dependency CVEs** — Django 5.2.15 → 5.2.16 and `cryptography` 45.0.7 → 49.0.0. The
   `cryptography>=43,<46` ceiling was itself the bug: it locked out the fixes. **Check:** any
   other pin whose upper bound will block a future security patch?
5. **A Playwright spec passing by accident.** `enrol-setup-login.spec.ts` asserted a
   just-imported student was visible, but the list is server-paginated (25/page) ordered
   `(batch__code, registration_number)` ascending — so the new row is only on page 1 while the
   batch is small. **Check:** do other specs make the same assumption? And separately — **is
   ascending registration_number the right default order for a human using this screen?**

---

## 3. Priority 1 — Concurrency, transactions and consistency

The stated rule is that every "at most once" guarantee is backed by a DB constraint *and* a
race-safe write. Round 1 closed the known cases. Now check the *transactional* layer:

1. **`transaction.atomic` appears 6 times**: `assessments/serializers.py:64`,
   `assessments/views/tests.py:148`, `batches/views.py:190`, `enrollments/importer.py:162`,
   `forum/views.py:112` and `:133`. **`ATOMIC_REQUESTS` is not set.** For every *other*
   multi-write operation, identify what partial state survives a mid-operation failure. I
   specifically want to know about: batch state transitions, enrolment + user creation,
   test submission + attendance marking, and device approval + binding update.
2. **`transaction.on_commit` is used zero times, but notifications are sent inside atomic
   blocks.** I chased this one down already, so treat it as a claim to check rather than an
   open question: the broker is the **ORM** broker (`get_broker()` tests `Conf.ORM` before
   `Conf.REDIS`), so enqueueing writes a row on the same connection and a task queued inside
   `atomic()` rolls back with it — production is correct without `on_commit`. **Dev is the
   wrong one:** `Q_CLUSTER["sync"]` runs the deliverer inline, so a rollback cannot unsend.
   **Check:** is that reasoning right, does the dev/prod divergence matter for test fidelity,
   and are there send sites where even the ORM broker's rollback is insufficient (e.g. a send
   after the atomic block closes but before the request finishes)?
3. **`select_for_update` is used zero times.** Find every read-modify-write on a row that two
   requests can hit at once and say whether the surrounding constraint actually saves it.
   Look hard at: `TestAttempt` scoring/grading, `AbsenceFollowUp` status updates,
   `Enrollment` mutation during import, and `IntegrationSetting` saves.
4. **django-q2 retry semantics.** `retry: 90` > `timeout: 60`, so a running task is not
   re-queued underneath itself — pinned by `tests/test_queue_broker.py`. The open question is
   the one that matters: **is every queued task idempotent?** django-q2 retries on failure, so
   what happens if `deliver_external` runs twice — duplicate email, a second SMS charge, a
   duplicate provider call? There is no dedup key on the task payload.
5. **Cron/scheduled jobs.** `escalations/services.py`, `attendance/services.py`,
   `certification/services.py`, `liveclasses/services.py`. For each: is it safe to run twice
   concurrently, safe to run twice sequentially, and safe to run after missing a day? What
   happens on a run that fails halfway?
6. **Cache-based locking** (`core/` cron lock). Is it correct under a Redis restart, a
   worker killed mid-hold, and clock skew? Is there a TTL that could expire mid-job?

## 4. Priority 2 — Data model and query behaviour

1. **`on_delete`: 48 CASCADE, 18 SET_NULL, 1 PROTECT.** Walk the CASCADE graph from `User`,
   `Batch` and `Course`. What does deleting a batch actually destroy? Is any of it something
   an institute is legally or operationally required to keep (attendance history, audit rows,
   certification records, submitted work)? Flag every CASCADE that should be PROTECT or
   SET_NULL. This is the single area where a wrong default is unrecoverable.
2. **Denormalised snapshots.** `Feedback` stores `registration_number`, `batch_code` and
   `course_name` at submission time; `TestAttempt` stores `total`. Are these deliberate
   point-in-time snapshots or accidental staleness? Is that distinction documented anywhere a
   future developer would find it?
3. **Indexes.** Check every field used in a `filter`, `order_by` or `distinct` on a list
   endpoint against the declared `Meta.indexes`. Call out missing composite indexes,
   *and* any declared index that no query uses. UUID primary keys are used throughout —
   comment on index bloat and insert locality on Postgres at this scale.
4. **N+1.** Round 1's fixes covered the known ones. Re-check every list/detail endpoint,
   every serializer `SerializerMethodField` that touches a relation, and every aggregation
   loop in `dashboard/`, `performance/`, `reports/` and `upsell/`. `notifications/views.py`
   has no `select_related` — I believe that is fine because the serializer uses only local
   fields; confirm or refute.
5. **Aggregate correctness.** Verify the maths, not just the SQL: attendance percentage,
   the 50%-attendance escalation rule, `performance/services.py::batch_performance` weighting
   and **rank ties**, and video 80%-completion. Off-by-one on a boundary here changes who gets
   escalated.
6. **Unbounded growth.** Which tables grow forever with no retention or archival path —
   `Notification`, `AuditLog`, `AttendanceEvent`, the new `AbsenceReminderLog`? What is the
   plan, and does any query over them lack a bound?

## 5. Priority 3 — Time, dates and scheduling

`TIME_ZONE = "Asia/Kolkata"`, `USE_TZ = True`. There are 13 uses of `localdate()` /
`now().date()`.

1. Is "today" computed consistently? Mixing `timezone.localdate()` with `created_at__date=`
   (which converts in the database) can disagree near midnight IST. Check `attendance/`
   especially — a student logging in at 00:05 must land on the right day.
2. Attendance excludes weekends (`is_rest_day`). Check the boundary conditions: a batch
   starting or ending on a weekend, a holiday list (is there one?), and whether
   `ATTENDANCE_COUNT_WEEKENDS` is honoured consistently everywhere.
3. Cron jobs assume a daily cadence. What happens across a DST-style shift, a server in a
   different timezone, or a job that runs at 23:59 and finishes at 00:01?
4. Are any date fields naive where they should be aware, or compared across types?

## 6. Priority 4 — Failure modes and error handling

1. **External adapter failure.** SMTP down, MSG91 returning 500, WhatsApp rate-limiting. Trace
   `notifications/dispatch.py` and `core/adapters/*`: does one failing channel abort the fan-out
   for the rest? Is a failure visible to an operator or silently swallowed? `core/adapters/smtp.py:50`
   catches bare `Exception` — is that right, and is it logged with enough context to diagnose?
2. **Storage failure.** Disk full or permission denied mid-upload: is the DB row created
   anyway, leaving a record pointing at a file that does not exist? Check the ordering of the
   save and the model write at all 7 storage-key sites.
3. **`core/exceptions.py::exception_handler`.** Does it leak internals in production? Is the
   error envelope consistent across DRF validation errors, permission denials, throttles, 404s
   and unhandled 500s? The frontend has one global error toast reading `detail` — does every
   error path actually produce that shape?
4. **Health endpoint** (`config/urls.py::health`) returns a static `{"status": "ok"}` without
   touching the database or Redis. A load balancer would keep routing to a container whose DB
   is gone. Is that the intent? What should it check, and what should it deliberately not?
5. **Frontend failure states.** For every feature page: is there a distinct rendering for
   loading, empty, and *error*? Where a query fails, does the user see anything at all, or an
   indefinite skeleton? Are there React error boundaries?

## 7. Priority 5 — Input validation and remaining injection sinks

1. **The CSV/XLSX import path** (`enrollments/importer.py`, openpyxl). This is the largest
   untrusted-input surface in the app. Check: file size limits, zip-bomb resistance,
   formula cells on *read*, malformed/absent headers, duplicate rows within one file, row
   count limits, and memory behaviour on a large file. Is the all-or-nothing transaction
   guarantee actually airtight?
2. Are `max_length`, numeric ranges, and date ordering enforced at the **serializer** layer,
   or only by the database? A `DataError` reaching the user as a 500 is a finding.
3. Any raw SQL, `.extra()`, `RawSQL`, or f-string-built `Q` objects?
4. `content/delivery.py` — can a user request a key they should not, or a path outside the
   media root, via the X-Accel header? Is the internal location correctly protected in
   `deploy/nginx.conf`?
5. Frontend: no `dangerouslySetInnerHTML` and no `localStorage` token storage — I checked.
   Confirm, and check for other sinks (URL construction, `window.open`, redirects).

## 8. Priority 6 — AuthN/AuthZ lifecycle

Round 1 verified the matrix itself. This is about the *lifecycle* around it:

1. **Session invalidation on state change.** Suspension is now handled (§2.3). What about a
   **role change** — does an in-flight session pick up the new role immediately, and is that
   safe in both directions (privilege gain *and* loss)? What about a password change, a
   password reset, a rejected device change, or a TOTP disable? Should any of those invalidate
   other sessions?
2. **Session settings.** `SESSION_COOKIE_AGE`, expiry-at-browser-close, rotation on login
   (`cycle_key`), `SESSION_COOKIE_SAMESITE`, `Secure`, `HttpOnly`. Is CSRF correctly enforced
   given SPA + cookie auth, and is the CSRF-priming endpoint safe?
3. **Device binding.** Now that a pending device request is unique per `(user, device_id)`,
   walk the full lifecycle: bind → new device → request → approve/reject → re-request →
   course end. Any state where a student is locked out with no path forward, or where two
   devices are simultaneously valid?
4. **Password reset tokens** (`accounts/models.py::PasswordResetToken`). Single-use? Expiry
   enforced server-side? Constant-time comparison? Invalidated on successful reset *and* on
   password change? Is the enumeration-safety claim actually true, including via timing and
   via the resend-count field?
5. **TOTP.** The new `failed_attempts` cap — is there a lockout-recovery path that itself
   bypasses the cap? Is the secret exposed anywhere after enrollment? Replay of a used code
   within its window?

## 9. Priority 7 — Secrets, logging and PII

1. `core/crypto.py` derives a Fernet key from `SECRET_KEY`. **What happens on `SECRET_KEY`
   rotation?** Every stored provider secret becomes undecryptable. Is that documented, is
   there a re-encryption path, and does it fail loudly or silently?
2. Trace what reaches the logs. `core/request_id.py` puts a request id on every line — do OTP
   codes, reset tokens, passwords, Fernet-decrypted secrets, or full PII rows ever get logged?
   Check `LOGGING` config, the DRF exception handler, and adapter debug paths.
3. `dev_code` is exposed in DEBUG for the setup flow. Prove it cannot appear in production.
4. Sentry: is PII scrubbing configured (`send_default_pii`)? Request bodies on a 500 from a
   login or reset endpoint would contain credentials.
5. `IntegrationSetting` exposes `secret_set` (a boolean) rather than the secret. Verify no
   serializer, admin page, log line, or OpenAPI example leaks the value.
6. **Data lifecycle / DPDP.** PII held: name, email, phone, employment company, performance.
   Is there any retention policy, export-on-request, or erasure path? What does erasing a
   student actually do given the CASCADE graph in §4.1?

## 10. Priority 8 — Frontend quality

1. **Accessibility.** Keyboard navigation through every interactive control; focus trapping
   and restoration in `Modal`; `aria-*` on custom controls; colour contrast in the light-blue
   theme; screen-reader labels on icon-only buttons; skip links. Flag anything that is
   keyboard-inoperable.
2. **react-query correctness.** Stale closures in mutation callbacks; cache keys that collide
   or fail to invalidate; optimistic updates without rollback; `enabled` guards that leave a
   query permanently idle. `NotificationBell` polls with exponential backoff — verify the
   interval logic and that it cannot leak timers on unmount.
3. **Memory and lifecycle.** Every `setInterval` / `setTimeout` / `addEventListener` /
   `AbortController` — is each cleaned up? Any state update after unmount?
4. **Bundle.** Recharts is lazy-chunked. What else is large and eagerly loaded? Are routes
   code-split? Is framer-motion pulled into the initial chunk?
5. **Form UX.** Double-submit protection on every mutating button; disabled state during
   flight; validation messages tied to inputs via `aria-describedby`; unsaved-changes warnings.
6. **Consistency.** After the design-system pass, is anything still bypassing it? Are loading
   skeletons, empty states, date formats and number formats consistent across pages?

## 11. Priority 9 — Testing quality

Do not measure coverage. Measure whether the tests would **catch a regression**:

1. Find tests that would still pass if the feature under test were deleted or stubbed —
   assertions on status codes only, on truthiness, or on data the test itself just wrote.
2. Find missing **negative** tests: the permission-denied case, the concurrent case, the
   empty case, the boundary case. Every matrix action should have a "wrong role is refused"
   test — is that actually true?
3. Flag order-dependence and shared-state leakage between tests. The Playwright suite runs
   `workers: 1` against a shared dev database and **accumulates data across runs** — §2.5 was
   one consequence. What else depends on that database being nearly empty?
4. `tests/test_concurrency.py` uses real threads for the cron lock but simulates elsewhere.
   Are the simulations faithful, or do they assert something weaker than the real race?
5. Is there any test asserting the *absence* of a behaviour that has since been added
   (a stale test pinning old behaviour)?

## 12. Priority 10 — Operational readiness

1. **Migrations against a live database.** Do any of the 40+ migrations take a long lock,
   rewrite a table, or add a non-null column without a default? The two newest
   (`accounts/0010`, `attendance/0004`) contain data migrations — `attendance/0004` loads
   *every* `absence_reminder` notification into a Python set. What is the memory profile on a
   database with a year of history, and should it be batched or bounded by date?
2. Is every migration genuinely reversible, and does reversing lose data silently?
3. **Backups.** `docs/DEPLOYMENT.md` describes them — is there a *tested restore*, and does
   the media volume get backed up alongside the database? A backup of one without the other
   restores to a broken state.
4. **Observability gaps.** With only Sentry and stdout logs, what production incident would be
   *invisible*? Specifically: qcluster stopped, Redis evicting keys, disk filling with media,
   a cron job silently no-oping.
5. `deploy/nginx.conf` and `docker-compose.prod.yml`: security headers, TLS config, body-size
   limits, timeouts matched to gunicorn's, X-Accel internal location, and whether any port is
   exposed that should not be.

---

## 13. Accepted limitations — do NOT report these

Documented in `docs/PROJECT_OVERVIEW.md` §13. Reporting them is noise:

1. A web app cannot read a device MAC address. Device identity is a FingerprintJS visitorId
   plus client IP on audit rows — a deterrent against casual account sharing, not a hardware
   lock. Do not suggest MAC capture.
2. "View-only" notes and the video watermark are deterrents, not DRM. Do not propose DRM.
3. Client-side route/nav gating is cosmetic by design; the server matrix is authoritative. Do
   *not* report the frontend role `Set`s as a hole — but **do** report any case where the
   server fails to enforce what the UI hides.
4. Email is intentionally non-unique (one account per course per person); ambiguous email
   logins fall back to Registration ID.
5. ~40 plain `APIView`s return hand-built dicts, so their OpenAPI entries are untyped. Known
   cosmetic gap; the schema generates cleanly.
6. Nothing has run on a production VPS yet. Postgres, Redis, nginx, X-Accel, gunicorn,
   qcluster, Sentry and backup restore are configured and documented but unexercised. Report
   *config* errors you can see; do not report "this is untested in production" as a finding.
7. react-router 6.30.4 carries two moderate advisories. The SSR one does not apply (Vite SPA,
   no SSR), and the open-redirect one is mitigated by `isSafeInAppLink` in
   `NotificationBell.tsx` since `Notification.link` is the only server-supplied value reaching
   `navigate()`. Do challenge that reasoning if it is wrong — but do not simply restate the
   advisory.

## 14. Invariants — flag any violation

1. Permissions come only from `core/permissions_matrix.py`; no hardcoded role checks.
2. Any change to `MATRIX` updates `tests/test_permissions.py` in the same commit.
3. Object-level scoping is required *in addition to* the matrix.
4. Every "at most once" rule is backed by a DB constraint **and** a race-safe write.
5. All file serving goes through `content/delivery.py::deliver()`.
6. Lists that can grow paginate server-side; the frontend never fetches a large page and
   slices it.
7. Model changes ship reversible migrations with safe defaults.
8. Deterrents are never described, in code or UI copy, as guarantees.
9. Storage keys are server-generated; a client filename never appears in a path.
10. No user-facing string begins with a lowercase letter (backend `detail` messages included —
    they surface directly in a toast).

---

Start with §3 (concurrency and transactions) and §4.1 (the CASCADE graph) — those are where I
think the remaining real damage is. Then work down. **Where you cannot verify something with
confidence, say so explicitly rather than guessing.**
