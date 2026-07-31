# Pre-production checklist

Everything still standing between this codebase and a live deployment, in the order it should
be done, with what each item needs **from you** rather than from code.

The code side is largely finished: 21 review findings raised, 18 closed, plus six phases of
external review acted on. What remains is dominated by one fact — **nothing here has ever run
on real infrastructure.** Most of the items below exist to convert assumptions into
observations.

**Status at time of writing:** 497 backend tests, 50 frontend, 12/12 Playwright.
ruff / black / mypy / eslint / tsc / prettier all clean. Latest commit `f351290`.

---

## How to read the phases

| Phase | Theme | Blocked on you? | Rough effort |
|---|---|---|---|
| **0** | Verify what has never been executed | No — 1 command | 20 min |
| **1** | Things only you can supply | **Yes** | Half a day |
| **2** | First deploy to a real server | **Yes** — needs a VPS | 1 day |
| **3** | Prove the recovery paths work | **Yes** — needs Phase 2 | Half a day |
| **4** | Measure instead of guess | **Yes** — needs Phase 2 | Half a day |
| **5** | Close the known-unexamined areas | No | 1–2 days |
| **6** | Decisions I could not make for you | **Yes** — judgement | 1 hour |

Phases 0–4 are sequential. Phase 5 can run in parallel with any of them. Phase 6 should
happen before Phase 2, because two items change product behaviour.

---

## Phase 0 — Verify what has never been executed

Cheapest information available, and it is genuinely one command.

### 0.1 Open the pull request

**Why.** Every CI job passes on this Windows machine. The GitHub runner is Ubuntu, with a
fresh Postgres, `npm ci` installing strictly from the lockfile, and the *gitleaks action*
rather than the binary I downloaded. Four things differ that routinely break builds:
case-sensitive filesystem, line endings, a phantom dependency that exists locally but is not
in `package-lock.json`, and a migration chain that has never run end-to-end on Postgres —
including the partial unique index and two data migrations.

**What you do.**

```bash
gh pr create --base review-baseline --head full-codebase-review --title "Full codebase review" --body "CI verification run"
```

`main` and `full-codebase-review` are byte-identical, so this runs all five jobs against the
real thing without changing anything.

**Consequence of skipping.** You find out CI is broken on the day you actually need it —
during a hotfix, with a production incident running.

### 0.2 Validate the nginx config

**Why.** `deploy/nginx.conf` has **never been parsed by nginx**. I have edited it three times
in this session — security headers, two probe `location` blocks in phase 4, and the `/admin/`
block changed to fail closed in phase 6. It is the single largest piece of shipped work with
no verification behind it at all. A syntax error means nginx refuses to start, which on a
first deploy looks like a total outage.

**What you do.** Start Docker Desktop, then:

```bash
docker run --rm -v "$(pwd)/deploy:/etc/nginx/conf.d:ro" nginx:1.27-alpine nginx -t
```

**Consequence of skipping.** The first deploy fails at the last step, and you debug nginx
syntax while everything else is already running.

### 0.3 Build the Docker image

**Why.** The image previously installed a dependency list missing `django-q2`, `cryptography`,
`pyotp`, `requests`, `redis` and `sentry-sdk` — it could not have started, since `django_q` is
in `INSTALLED_APPS`. That is fixed, but the fixed image has never been built.

**What you do.**

```bash
docker build -t advantage-pro-lms:test ./backend
docker run --rm advantage-pro-lms:test python -c "import django_q, cryptography, pyotp, requests, redis, sentry_sdk; print('imports OK')"
```

---

## Phase 1 — Things only you can supply

Nothing in this phase can be done from the codebase. Each is a credential, an account, or a
purchase.

| # | What | Where it goes | Consequence if missing |
|---|---|---|---|
| 1.1 | **A VPS** (KVM, not shared hosting) | — | Nothing below is possible |
| 1.2 | **Domain + TLS cert** | nginx, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Cookies marked `Secure` never arrive; nobody can log in |
| 1.3 | **`DJANGO_SECRET_KEY`** — 50+ random chars | `prod.env` | `check --deploy` fails the build; also see 1.8 |
| 1.4 | **SMTP credentials** (Hostinger email) | `prod.env` | Setup links, OTPs and password resets are never delivered — **no new user can ever activate** |
| 1.5 | **SMS provider** (MSG91 or similar) | `prod.env` | Phone OTP step of setup cannot complete |
| 1.6 | **WhatsApp Cloud API** credentials | `prod.env` | Feedback-to-management and reminders lose their WhatsApp channel |
| 1.7 | **Sentry DSN** | `prod.env` | Errors are invisible; you learn about them from users |
| 1.8 | **Decide `TRUSTED_PROXY_COUNT`** | `prod.env` | See below — this one is a security setting, not a preference |

**On 1.8 specifically.** Set it to `1` for the documented nginx topology, `2` if a CDN sits in
front. Getting it **too high** is the dangerous direction: it starts trusting `X-Forwarded-For`
entries the client wrote, which re-opens the throttle bypass fixed earlier in this work — a
caller rotating the header would land in a fresh rate-limit bucket on every request. Too low
just means every request appears to come from the proxy, so per-IP throttles become global.
The default is `0` for that reason.

**On 1.4 — email is the one true blocker.** Every account starts as `PENDING` and activates
through an emailed link. Without working SMTP you cannot onboard a single real user, including
the first Super Admin.

---

## Phase 2 — First deploy

**Prerequisite:** Phases 0 and 1.

### 2.1 Stand it up

`docs/DEPLOYMENT.md` is the procedure. Four processes must run: gunicorn, **qcluster**,
Postgres, Redis.

**The qcluster one is worth repeating.** In dev the task queue runs inline, so everything
appears to work without a worker. In production external sends are *queued*. If `qcluster` is
not running, every email, SMS and WhatsApp sits in the queue and **nobody ever receives them,
with no error raised anywhere**. The application looks completely healthy.

### 2.2 Confirm the topology is what you think it is

| Check | Expected | Why it matters |
|---|---|---|
| `/api/v1/health/` | 200, static | Liveness — wire this to restarts |
| `/api/v1/ready/` | 200, checks DB + cache | Readiness — wire this to the load balancer |
| Queue broker | **Postgres, not Redis** | django-q2 resolves the ORM broker first; Redis backs the cache only. Sizing Redis for queue throughput would be sizing the wrong thing |
| `python manage.py check --deploy --fail-level WARNING` | 0 issues, **0 silenced** | Any `security.W*` regression fails it |

**Do not wire restarts to `/ready/`.** A thirty-second Postgres failover would take every
container unhealthy simultaneously and restart the lot, turning a recoverable blip into a cold
start of the whole application.

### 2.3 Migrate and seed

```bash
python manage.py migrate
python manage.py createsuperuser   # NOT seed_demo
```

`seed_demo` refuses to run unless `DEBUG` or `--force`, deliberately — it creates accounts with
a publicly known password.

### 2.4 Send one real message per channel

Super Admin → Channels → Test, for email, SMS and WhatsApp. This is the only way to discover a
wrong credential before a student does.

---

## Phase 3 — Prove the recovery paths

**Prerequisite:** Phase 2. This is the phase people skip and regret.

### 3.1 Restore drill *(required)*

**Why.** An untested backup is an assumption, and every failure mode here is quiet: a
`pg_dump` writing a zero-byte file since a credential change, a media volume that was never in
the backup set, a dump that restores with the wrong owner.

**The specific trap.** Database and media must be restored **from the same timestamp**. The
database holds storage keys; the volume holds the bytes they point at. Restore Tuesday's
database against Monday's media and every file uploaded on Tuesday becomes a row pointing at
nothing — the API returns a key, nginx 404s, and *nothing in the application notices*.

Procedure is in `docs/DEPLOYMENT.md` § Backups and restore. Restore into a scratch environment,
sign in, open a video and a forum attachment, confirm the bytes are there. **Write down the
date.** Repeat quarterly.

### 3.2 Kill qcluster deliberately

Stop the worker, trigger a notification, confirm it queues rather than vanishing, restart the
worker, confirm it delivers. You want to have seen this failure once, on purpose.

### 3.3 Confirm Sentry receives a real error

Trigger a deliberate 500. **This is load-bearing:** unhandled exceptions now return a clean
`{detail, errors}` envelope, which means DRF no longer re-raises them, which means Django never
fires `got_request_exception`. Reporting depends entirely on an `ERROR` log record being picked
up by Sentry's logging integration. If that wiring is wrong, production errors are silent — and
they will *look* fine, because the user gets a tidy message.

### 3.4 Verify the `/admin/` allow-list

It now **fails closed** — `deny all` with only `127.0.0.1` allowed. Add your office or VPN
range in `deploy/nginx.conf` before deploying, or you will lock yourself out. That is the
intended direction of failure.

---

## Phase 4 — Measure instead of guess

**Prerequisite:** Phase 2. Closes **P-12**.

Re-run `docs/LOADTEST.md` against the real stack. The existing numbers were measured on local
SQLite, single-process, on Windows — `POST /auth/login/` shows 830 ms median, which is Argon2id
on one core and will look completely different with Postgres, five gunicorn workers and Redis.

**Consequence of skipping.** You quote those numbers in a proposal, or size the VPS from them.

Also worth watching once real data exists: the two indexes added in phase 3 were reasoned from
query shape, not from `EXPLAIN` on production data. Confirm they are actually used.

---

## Phase 5 — Close the known-unexamined areas

Not blocked on you. I can do any of these on request.

### 5.1 Time and timezones — *highest value*

13 uses of `localdate()` / `now().date()` mixed with `created_at__date` lookups that convert in
the database. Those can disagree near midnight IST, and **attendance is day-boundary
sensitive**: a student logging in at 00:05 must land on the right day, or their attendance
percentage is wrong and the 50% escalation fires against the wrong people. Also unexamined:
batches starting or ending on a weekend, and whether there is a holiday calendar at all.

### 5.2 Frontend accessibility

I have never opened this app with a keyboard. Modal focus management is now implemented and
tested, but nothing else is: keyboard traps elsewhere, colour contrast in the light-blue theme,
screen-reader labels on icon-only buttons, skip links.

### 5.3 Testing quality

497 tests pass. Nobody has asked whether they would **catch a regression** — how many would
still pass if the feature under test were deleted. The two I found by accident in this session
were both real (a Playwright spec passing because a dataset was small, a focus test passing
because it raced a `requestAnimationFrame` into the right answer), which suggests looking
properly would find more.

### 5.4 Frontend unit coverage — **P-10**, paused at your request

85 components, 50 tests. Currently a deliberate trade-off: Playwright covers the flows where
failure costs money. My recommendation is to keep it paused — "write more tests" without a
target produces assertions that pass whether or not the code works.

### 5.5 Register hygiene

The six CodeRabbit phases produced real findings — the 49.5% escalation bug, the TOTP lockout
with no recovery, the `X-Forwarded-For` throttle bypass, the broken Docker image — and **none
are in the P-xx register**, which currently under-reports the work by roughly a dozen findings.

---

## Phase 6 — Decisions I could not make for you

Two of these changed documented behaviour. If the operating procedure meant what it said, I was
wrong to change it, and reverting is cheap.

| # | Decision | What I did | Revert cost |
|---|---|---|---|
| 6.1 | **Post-course device changes** | Procedure said "closed for good". That locked a graduate who lost their phone out of their own certificate, with no recourse. Now raises a request routed to Tech Support | Low — one function in `accounts/device.py` |
| 6.2 | **TOTP replay window** | A code is now accepted once. Confirming 2FA and signing in within the same 30 s needs the next code | Low, but this is RFC 6238 §5.2 — I would not revert it |
| 6.3 | **Session lifetime** | 12 h, was Django's 2 weeks. `SESSION_SAVE_EVERY_REQUEST` refreshes on activity | Trivial — one setting |
| 6.4 | **`AttendanceEvent` retention** | Deliberately never purged. Growth is bounded by enrolment, not traffic | Needs a policy decision, not a code change |
| 6.5 | **Admin deletion of User/Batch/Course** | Blocked entirely. Since there is no user-deletion API, deletion now requires a shell | Consider whether DPDP erasure needs a proper path |

**6.5 is the one I would think hardest about.** `PRODUCTION_READINESS.md` names DPDP-style
erasure as an obligation, and there is currently no supported way to erase a student. A
management command with the cascade written down is probably the right answer.

---

## Errors and defects found during this work

Recorded because the pattern matters more than the list: **almost every one was invisible until
something was actually executed.** Nine were found by running CI locally for the first time or
by writing a test, not by reading code.

### Would have broken production

| Defect | How it surfaced | Fixed in |
|---|---|---|
| **Docker image missing 6 packages** incl. `django-q2` — could not start | Reading the Dockerfile against the audited requirements | `f351290` |
| **`X-Forwarded-For` trusted unconditionally** — defeated every IP throttle including the login brute-force guard | Auditing for the round-2 prompt | `c96902a` |
| **Suspension did not end a live session** — a suspended account kept full access until its cookie expired (2 weeks) | Auditing the auth lifecycle | `c96902a` |
| **9 dependency CVEs**; the `cryptography<46` pin was itself blocking its own fix | `pip-audit`, first run | `c96902a` |
| **TOTP lockout with no recovery path** — 5 mistypes locked an account out permanently | CodeRabbit phase 5 | `92f76b5` |
| **50%-attendance rule never fired between 49.5% and 50%** — `round(49.5)` is 50 | CodeRabbit phase 3 | `001f78e` |
| **Zero of 27 pages handled `isError`** — a server outage rendered as "no data" | CodeRabbit phase 6 | `f351290` |

### Silent-failure class

| Defect | Consequence | Fixed in |
|---|---|---|
| Notifications inside `atomic()` with no `on_commit` | Investigated: the ORM broker rolls back with the transaction, so production is correct. **Dev is the wrong one** | `ad8a4d2` |
| Dead `Q_CLUSTER["redis"]` config | Docs described a Redis-backed queue that never existed | `ad8a4d2` |
| Unhandled 500s returned Django's HTML page | Frontend error handling reads JSON `detail`; users saw nothing | `9823782` |
| `SECRET_KEY` rotation silently broke all channels | Now warns | `92f76b5` |
| CSV exports had no formula-injection escaping | Staff open these in Excel | `c96902a` |

### My own errors, and what they cost

Listed because they show where I was least reliable.

| Error | How it was caught | Lesson |
|---|---|---|
| **Claimed an "exploitable path traversal"** — Django already basenames uploads | Writing the regression test | Do not assert exploitability without exercising the path |
| **Guessed throttling caused an E2E failure** — it was pagination and accumulated dev data | Reading the actual error after the "fix" changed nothing | Read the failure before proposing a cause |
| **`ActiveSessionAuthentication` added 85 schema warnings** | Counting them during P-09 | A fix in one layer can regress another |
| **Modal focus trap filtered on `offsetParent`** — a layout property, so no-layout environments got "Tab does nothing" | The test failed | Do not gate behaviour on layout |
| **Two tests passed for the wrong reason** | Deliberately reverting the fix to check | Always verify a test fails without its fix |
| **`format:check` gate failing since I added it** | Running the exact CI glob | Verify a gate against the command CI runs |

---

## The shortest path

If you do only three things:

1. **Open the PR** (Phase 0.1) — 1 command, tells you whether CI works.
2. **`nginx -t`** (Phase 0.2) — 1 command, the only unverified shipped change.
3. **The restore drill** (Phase 3.1) — the difference between having backups and believing you
   have backups.

Everything else is either supplying credentials or measuring what you now have.
