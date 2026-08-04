# Production push report — Hostinger

What it takes to move this from a laptop to a live deployment: what to buy, in what order, what
each thing costs, and the decisions only you can make.

`docs/DEPLOYMENT.md` is the *command reference* — the exact shell commands, systemd units and
nginx config. This document is the **plan**: procurement, sequencing, and the choices that come
before you type anything.

Read `docs/PRE_PRODUCTION_CHECKLIST.md` alongside this. It lists what is still unverified.

---

## 1. Where this stands

**The code is ready. The infrastructure has never existed.**

| | Status |
|---|---|
| Backend | 506 tests passing, ruff/black/mypy clean |
| Frontend | 50 unit tests, 12 end-to-end specs |
| Security review | 21 findings raised, 18 closed, 3 open by choice |
| External review | 6 rounds acted on |
| **Run on a real server** | **Never** |

That last row is the honest summary of the risk. Everything below exists to close it.

**One caveat carried forward:** `deploy/nginx.conf` has never been through `nginx -t`. Validate
it before you rely on it — it is one command, in §7.

---

## 2. What you need to buy

### 2.1 Hosting — a VPS, not shared hosting

**Shared hosting will not work.** This needs Python processes, PostgreSQL, Redis, cron and a
background worker. Hostinger shared plans give you PHP and a database, and none of the rest.

**Hostinger KVM 2** — 2 vCPU, 8 GB RAM, 100 GB NVMe. Roughly **₹500–700/month** on a longer
term.

KVM 1 (1 vCPU, 4 GB) technically runs it, but you are hosting Postgres, Redis, gunicorn, a
worker and nginx on one core. KVM 2 is the sensible floor.

Choose **Ubuntu 22.04 or 24.04**, and the **Mumbai** region.

### 2.2 Domain and TLS

A domain (~₹800–1,200/year). TLS is **free** via Let's Encrypt — do not buy a certificate.

### 2.3 Email — Hostinger Business Email

Roughly **₹100–200/user/month**.

**This is the one hard blocker.** Every account starts `PENDING` and activates through an
emailed setup link. Without working SMTP you cannot onboard a single user — including your own
first Super Admin. Nothing else on this list blocks you the way email does.

### 2.4 SMS — third party (not Hostinger)

Hostinger does not sell SMS. The app ships an **MSG91** adapter.

Indian transactional SMS is roughly **₹0.15–0.25 per message**, plus DLT registration with TRAI
(a one-time ~₹5,000 and a few days of paperwork — start early, it is the slowest item here).

Used for the phone-verification step of setup and for absence reminders.

### 2.5 WhatsApp — Meta WhatsApp Cloud API

Also not Hostinger. Free tier covers a starting volume; beyond that it is per-conversation.
Requires a Meta Business account and template approval.

Used for student→management feedback and reminders. **Optional** — the app runs without it, you
just lose that channel.

### 2.6 Video storage — read §3, it is the decision that matters

### 2.7 Error monitoring — Sentry

**Free tier is enough.** Without it, you find out about errors when a student tells you.

### 2.8 Rough monthly total

| Item | Cost |
|---|---|
| VPS (KVM 2) | ₹500–700 |
| Domain | ~₹100 (amortised) |
| Email (2 users) | ₹200–400 |
| SMS | ₹150–500 (volume) |
| WhatsApp | ₹0 to start |
| Sentry | ₹0 |
| **Total** | **~₹1,000–1,700/month** |

Plus one-time: DLT registration ~₹5,000.

---

## 3. Video storage — the one architectural decision

This is the choice with real consequences, so here is the actual trade-off.

### How it works today

Files are stored via a **storage adapter** (`core/adapters/`) selected by an environment
variable. Serving goes through a single seam, `content/delivery.py::deliver()`, which in
production returns an **`X-Accel-Redirect`** header — nginx sends the bytes and the Python
worker is freed immediately instead of being tied up for the length of the video.

Swapping storage is an env var, not a code change. That was designed in deliberately.

### Option A — VPS disk (start here)

Videos on the VPS's own NVMe, served by nginx.

**For:** Zero extra cost. Fastest. Already implemented and tested. 100 GB is a lot of course
video.

**Against:** Storage is capped by the disk. Backups must include the media volume (see §6).
Every stream competes with the app for the same network link.

**Recommended for launch.** At institute scale — low hundreds of students — a single VPS
serves video comfortably.

### Option B — S3-compatible object storage

Move media to S3/R2/Spaces when you outgrow the disk.

**For:** Effectively unlimited. Survives losing the VPS. CDN-friendly.

**Against:** Costs more, adds egress charges, and **requires writing an adapter** (the seam
exists; the S3 implementation does not).

**When to switch:** when media exceeds ~60 GB, or students complain about playback while the
app is busy.

### What I would do

**Launch on Option A.** Watch disk usage monthly. Migrating later is an adapter plus a file
copy, not a rewrite — that is exactly what the seam is for. Building S3 now is solving a
problem you do not have yet.

---

## 4. The four processes that must run

The most common way to get this wrong is to start three of them.

| Process | What it does | If it is not running |
|---|---|---|
| **gunicorn** | The API | Site is down — obvious |
| **PostgreSQL** | Database | Site is down — obvious |
| **Redis** | Shared cache, rate limits | Throttles go per-process; `prod.py` refuses to boot without it |
| **qcluster** | Background sends | **Silent failure — read below** |

**On qcluster.** In development the task queue runs inline, so everything appears to work
without a worker. In production, external sends are *queued*. If `qcluster` is not running,
every email, SMS and WhatsApp sits in the queue and **nobody ever receives anything, with no
error raised anywhere.** The application looks completely healthy. Students never get their
setup links.

Both `qcluster` and gunicorn run under systemd (units in `DEPLOYMENT.md` §5.1).

**A related fact worth knowing:** the queue broker is **PostgreSQL, not Redis** — django-q2
resolves the ORM broker first. That is deliberate: a task queued inside a transaction rolls
back with it, so a failed operation cannot leave an email queued for work that never happened.
Redis is still required, for the cache and rate limiting. Do not size Redis for queue
throughput; that is not what it is doing.

---

## 5. The sequence

Each phase depends on the one before it.

### Phase 0 — Verify (before buying anything)

Two commands, no infrastructure needed:

```bash
# 1. Does CI actually pass? It has never run on GitHub.
gh pr create --base review-baseline --head full-codebase-review \
  --title "Full codebase review" --body "CI verification run"

# 2. Is the nginx config even valid? It has never been parsed.
docker run --rm -v "$(pwd)/deploy:/etc/nginx/conf.d:ro" nginx:1.27-alpine nginx -t
```

### Phase 1 — Procure (about a week, mostly waiting)

**Start DLT registration first** — it is the long pole. Then VPS, domain, email, Sentry, Meta
Business.

### Phase 2 — Provision the server (a day)

Ubuntu, Postgres, Redis, nginx, certbot, Docker if you are using compose. `DEPLOYMENT.md` §1–3.

**Two settings that are easy to get wrong:**

**`TRUSTED_PROXY_COUNT=1`** — nginx sits in front, so exactly one hop of `X-Forwarded-For` is
trustworthy. This is a security setting: it governs how far the app trusts that header for rate
limiting and audit logs. **Setting it too high is the dangerous direction** — it starts trusting
entries the client wrote, which would defeat the login brute-force guard.

**`/admin/` fails closed.** `deploy/nginx.conf` ships with `deny all` and only localhost
allowed. **Add your office or VPN range before deploying or you will lock yourself out.** That
is the intended direction of failure — a commented-out allow-list protects nothing.

### Phase 3 — Deploy (a day)

Build, migrate, collect static, start all four processes.

```bash
python manage.py migrate
python manage.py createsuperuser    # NOT seed_demo
```

**Never run `seed_demo` in production.** It creates accounts with a publicly known password.
It refuses to run outside `DEBUG` without `--force` — do not override that here.

Then verify:

```bash
python manage.py check --deploy --fail-level WARNING   # expect: 0 issues, 0 silenced
curl https://yourdomain.com/api/v1/health/             # {"status":"ok"}
curl https://yourdomain.com/api/v1/ready/              # {"status":"ready"}
```

**Wire the probes correctly:** `/health/` (static) to restarts, `/ready/` (checks DB + cache) to
the load balancer. Pointing restarts at `/ready/` means a thirty-second Postgres failover takes
every container unhealthy at once and restarts the lot — turning a recoverable blip into a cold
start of the whole application.

### Phase 4 — Providers (half a day)

Swap the adapters from console stubs to real ones:

```bash
LMS_EMAIL_ADAPTER=core.adapters.smtp.SmtpEmailAdapter
LMS_SMS_ADAPTER=core.adapters.msg91.Msg91SmsAdapter
LMS_WHATSAPP_ADAPTER=core.adapters.whatsapp_cloud.WhatsAppCloudAdapter
```

with credentials: `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`, `MSG91_AUTH_KEY` /
`MSG91_SENDER_ID`, `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` /
`WHATSAPP_TEMPLATE_NAME`.

**Do not set `LMS_ALLOW_CONSOLE_ADAPTERS`.** Production refuses to boot on console stubs
precisely so this cannot ship silently.

Then **send one real message per channel** (Super Admin → Channels → Test). It is the only way
to find a wrong credential before a student does.

### Phase 5 — Prove recovery works (half a day)

The phase everyone skips.

**Restore drill — required.** An untested backup is an assumption, and every failure here is
quiet: a `pg_dump` writing a zero-byte file since a credential change, a media volume never in
the backup set.

**The specific trap:** database and media must be restored **from the same timestamp**. The
database holds storage keys; the volume holds the bytes they point at. Restore Tuesday's
database against Monday's media and every file uploaded on Tuesday becomes a row pointing at
nothing — nginx 404s and *nothing in the application notices*.

Procedure in `DEPLOYMENT.md` § Backups and restore. Restore into a scratch environment, sign in,
open a video and a forum attachment, confirm the bytes are there. **Write down the date.**
Repeat quarterly.

**Also test:** stop qcluster, trigger a notification, confirm it queues rather than vanishing,
restart, confirm delivery. And trigger a deliberate 500 to confirm Sentry receives it — that
path depends on an `ERROR` log record being picked up, and if the wiring is wrong your errors
are silent while *looking* fine to the user.

### Phase 6 — Cron and go live

Six scheduled commands (`DEPLOYMENT.md` §5). Then create real accounts, import the first batch,
and watch Sentry for a week.

---

## 6. Ongoing operations

| Task | Frequency |
|---|---|
| Check Sentry | Daily at first |
| Verify backups ran | Weekly |
| **Restore drill** | **Quarterly** |
| `pip-audit` / `npm audit` | Monthly (CI does it per PR) |
| Disk usage (§3) | Monthly |
| Django patch releases | As released |

**On rotating `SECRET_KEY`:** it is not only Django's signing key — it derives the encryption
key for every stored provider secret. **Rotating it makes those secrets undecryptable**, and the
failure is quiet by design: the app stays up and simply stops delivering on every channel. If
channels go silent after a deploy, grep the logs for `SECRET_KEY`. Procedure in `DEPLOYMENT.md`
§ Rotating SECRET_KEY — re-enter each provider secret immediately after.

---

## 7. Pre-launch checklist

**Before the server exists**

- [ ] PR opened, CI green on GitHub
- [ ] `nginx -t` passes
- [ ] Docker image builds and imports cleanly

**Procurement**

- [ ] VPS, domain, TLS
- [ ] Email account (the blocker)
- [ ] MSG91 + DLT registration
- [ ] WhatsApp Business (optional)
- [ ] Sentry project

**Configuration**

- [ ] `DJANGO_SECRET_KEY` — 50+ random chars, stored somewhere safe
- [ ] `DJANGO_ALLOWED_HOSTS` = real domain
- [ ] `TRUSTED_PROXY_COUNT=1`
- [ ] `/admin/` allow-list edited with your IP range
- [ ] `LMS_ALLOW_CONSOLE_ADAPTERS` **not** set
- [ ] All three adapters pointed at real providers

**Verification**

- [ ] `check --deploy --fail-level WARNING` → 0 issues, 0 silenced
- [ ] `/health/` and `/ready/` both 200
- [ ] All four processes running
- [ ] One real message sent per channel
- [ ] **Restore drill completed, date recorded**
- [ ] Sentry received a test error
- [ ] Real Super Admin created; `seed_demo` never run

---

## 8. Known limitations to set expectations around

Deliberate, documented, and not going to change:

1. **Device binding is a deterrent, not a hardware lock.** A browser cannot read a MAC address.
   Identity is a browser fingerprint plus IP on audit rows — strong against casual account
   sharing, not against someone determined.
2. **"View-only" notes and the video watermark are deterrents, not DRM.** The browser
   necessarily receives the bytes.
3. **Email is intentionally not unique** — one account per course per person.
4. **Certificates are ID-entry and follow-up tracking.** There is no PDF generation.
5. **There is no payments module.** `Course.fees` is a stored field only.

---

## 9. Recommendation

**Go, with the sequence above.** The code is in better shape than most systems at first
deployment — the security review is closed, the test suite is real, and the failure modes are
documented.

The remaining risk is not in the code. It is that **none of the infrastructure has ever run**,
and that risk is only retired by running it.

If you want the single highest-value hour: **open the PR and run `nginx -t`** (Phase 0). Both
are free, neither needs a server, and together they tell you whether the two things that have
never been executed actually work.
