# Deployment & Go-Live (Hostinger)

How to take Advantage Pro LMS from local dev to production. Most of this is
configuration — the adapter design means no code changes to switch providers.

## 1. Prerequisites
- Hostinger **VPS or Cloud** plan (Python + PostgreSQL; basic shared hosting won't run this).
- PostgreSQL 16, Python 3.12, Node 20 (for building the frontend), Nginx.
- **Redis** (recommended) — shared cache so DRF throttling / login rate-limits are consistent
  across gunicorn workers. Without `REDIS_URL` the app falls back to per-process in-memory cache
  (fine for a single worker; rate limits won't be shared across workers).

## 2. Environment (`backend/.env`)
```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<a long random secret>          # prod refuses to boot without this
DJANGO_ALLOWED_HOSTS=lms.yourdomain.com           # prod refuses the dev default
DATABASE_URL=postgres://USER:PASS@HOST:5432/advantage_pro_lms
REDIS_URL=redis://localhost:6379/0                # shared cache/throttle (omit to use locmem)
FRONTEND_URL=https://lms.yourdomain.com
CORS_ALLOWED_ORIGINS=https://lms.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://lms.yourdomain.com
# Throttles (defaults shown)
THROTTLE_ANON=60/min
THROTTLE_USER=240/min
THROTTLE_LOGIN=10/min
# Observability
LOG_LEVEL=INFO
SENTRY_DSN=                  # set to enable error monitoring (prod only)
SENTRY_TRACES_SAMPLE_RATE=0.0
# Upload caps (MB) and data retention (days)
MAX_VIDEO_UPLOAD_MB=512
MAX_DOCUMENT_UPLOAD_MB=25
RETENTION_AUDIT_DAYS=365
RETENTION_NOTIFICATION_DAYS=180
# Real provider adapters (replace the console/local dev stubs)
LMS_EMAIL_ADAPTER=...        # Hostinger SMTP adapter
LMS_SMS_ADAPTER=...          # SMS gateway adapter
LMS_WHATSAPP_ADAPTER=...     # WhatsApp gateway adapter
LMS_STORAGE_ADAPTER=...      # object/video storage adapter (return signed URLs from .url())
```

## 3. App server
```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # incl. psycopg, redis, sentry-sdk, whitenoise, gunicorn
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
# Create the real Super Admin (non-interactive): role defaults to super_admin in the manager.
DJANGO_SUPERUSER_PASSWORD='<strong-password>' \
  .venv/bin/python manage.py createsuperuser --noinput --username admin --role super_admin --email you@domain.com
.venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000   # behind a systemd unit
```
Put **Nginx** in front for TLS (HTTPS) and to serve the built frontend.
(`requirements-dev.txt` adds the test/lint tooling — install it in CI / dev only.)

## 4. Frontend
```bash
cd frontend && npm ci && npm run build   # outputs dist/, served by Nginx
```
Serve `dist/` and reverse-proxy `/api` to gunicorn (same origin keeps cookies/CSRF simple).

**Nginx security headers (set at the edge — the SPA is served by Nginx, not Django).**
Add these to the `server {}` block so every response carries them. The CSP is tuned for
this app: the SPA bundle is same-origin; styles need `'unsafe-inline'` (framer-motion and
Tailwind inject inline styles); YouTube thumbnails and provider images load over https; the
API is same-origin. Django itself also sets HSTS/nosniff/secure-cookies via `prod.py`.
```nginx
add_header X-Frame-Options "DENY" always;                     # no clickjacking (also frame-ancestors below)
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Content-Security-Policy "default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
```
(If you later add a strict `script-src` nonce pipeline you can drop `'unsafe-inline'` from
`style-src` via hashed styles; not worth it for this internal tool today.)

## 5. Background work — cron **and** a django-q2 worker (both required in production)

There are two distinct kinds of background work, and production needs both. An earlier
version of this document said "no Celery/Redis required" — that was wrong for production and
is corrected here, because following it silently breaks outbound messaging.

| | What it runs | How it runs |
|---|---|---|
| **Scheduled jobs** | The six idempotent management commands below (reminders, escalations, retention) | `cron` — each command is overlap-locked, so a slow run cannot double-fire |
| **Async fan-out** | Every outbound email / SMS / WhatsApp queued by `notifications.dispatch` | **`manage.py qcluster`** (django-q2), backed by **PostgreSQL** — see below |

**Why the worker is not optional in prod.** `notifications/dispatch.py` sends in-app
notifications synchronously but hands external channels to django-q2. In `dev` the queue runs
inline (`Q_CLUSTER` sync), so everything appears to work without a worker. In production the
task is *queued* — if no `qcluster` process is running, those messages sit in the queue and
**nobody ever receives them**, with no error surfaced to the request.

**The queue broker is the database, not Redis.** `django_q.brokers.get_broker()` checks
`Conf.ORM` before `Conf.REDIS`, so `Q_CLUSTER["orm"] = "default"` wins and any `redis` key
beside it is never read. That is deliberate: enqueueing writes a row through the same
connection, so a task queued inside `transaction.atomic()` rolls back with it. Notifications
are sent from inside atomic blocks and none of those sites use `transaction.on_commit`, so a
Redis broker would leave an email or SMS queued for work that was rolled back. Moving to a
Redis broker therefore requires adding `on_commit` at every send site first.

`prod.py` still fails fast without `REDIS_URL` — Redis backs the **shared throttle/rate-limit
cache**, which genuinely does need to be shared across gunicorn workers. It is just not the
queue broker. Sizing Redis for queue throughput would be sizing the wrong thing.

Point cron at the scheduled commands:
```cron
*/5 * * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_due_reminders          # live-class 1h/15m (skips cancelled)
0   * * * *  cd /srv/lms/backend && .venv/bin/python manage.py run_escalations              # incomplete tests + 50% attendance
0   8 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_certificate_reminders   # weekly certificate nudges (MIS follow-up)
30  8 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_absence_reminders        # login-attendance absentees (today)
0   9 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_engagement_reminders     # LinkedIn / Google review / next-plan
0   3 * * 0  cd /srv/lms/backend && .venv/bin/python manage.py purge_old_data                 # retention: old audit logs + read notifications
```
Every cron line must set `DJANGO_SETTINGS_MODULE=config.settings.prod` (see the systemd units
in §5.1 — the cleanest way is to run them as systemd timers that inherit an `EnvironmentFile`).

`purge_old_data` only removes activity data (audit logs, read notifications) past the retention
window; it never touches enrolments, attendance, submissions, or certificates. Use `--dry-run`
to preview.

### 5.1 systemd units

`/etc/lms.env` holds the environment for every unit (mode `0600`, owned by root):
```ini
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<long-random>
DJANGO_ALLOWED_HOSTS=lms.example.com
DATABASE_URL=postgres://lms:<pw>@localhost:5432/advantage_pro_lms
REDIS_URL=redis://localhost:6379/0
MEDIA_XACCEL_PREFIX=/protected
LMS_EMAIL_ADAPTER=core.adapters.smtp.SmtpEmailAdapter
LMS_SMS_ADAPTER=core.adapters.msg91.Msg91SmsAdapter
LMS_WHATSAPP_ADAPTER=core.adapters.whatsapp_cloud.WhatsAppCloudAdapter
```
(Boot fails fast if `SECRET_KEY`, `ALLOWED_HOSTS` or `REDIS_URL` are missing, or if any
notification adapter is still the console stub — see §9.)

**`/etc/systemd/system/lms-web.service`** — the API:
```ini
[Unit]
Description=Advantage Pro LMS (gunicorn)
After=network.target postgresql.service redis.service

[Service]
User=lms
WorkingDirectory=/srv/lms/backend
EnvironmentFile=/etc/lms.env
ExecStart=/srv/lms/backend/.venv/bin/gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 --workers 5 --timeout 60 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/lms-qcluster.service`** — the async worker. **Without this, queued
email/SMS/WhatsApp are never delivered:**
```ini
[Unit]
Description=Advantage Pro LMS background worker (django-q2)
After=network.target postgresql.service redis.service

[Service]
User=lms
WorkingDirectory=/srv/lms/backend
EnvironmentFile=/etc/lms.env
ExecStart=/srv/lms/backend/.venv/bin/python manage.py qcluster
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now lms-web lms-qcluster
systemctl status lms-qcluster        # confirm the worker is actually up
```

A scheduled command as a timer (repeat per command, or keep them in cron):
```ini
# lms-escalations.service
[Service]
Type=oneshot
User=lms
WorkingDirectory=/srv/lms/backend
EnvironmentFile=/etc/lms.env
ExecStart=/srv/lms/backend/.venv/bin/python manage.py run_escalations

# lms-escalations.timer
[Timer]
OnCalendar=hourly
Persistent=true
[Install]
WantedBy=timers.target
```

### 5.2 Compose reference
- **`docker-compose.yml`** is **development only** — dev settings, `DEBUG=true`, a throwaway
  secret, no Redis and no worker. Never deploy it.
- **`docker-compose.prod.yml`** is the production-shaped reference: Postgres, Redis, gunicorn,
  a `qcluster` worker, and nginx with the X-Accel media alias. Supply real secrets via an
  env file; it is a topology reference, not a turnkey stack.

## 6. Providers (the adapter swap)
Implement a class per channel against the interfaces in `core/adapters/base.py`
(`EmailAdapter`, `SmsAdapter`, `WhatsAppAdapter`, `StorageAdapter`) and point the
`LMS_*_ADAPTER` env vars at them. No call sites change.

For media, the `StorageAdapter.url(key, expires_in)` method is the **signed-URL** contract:
the local adapter returns the on-disk media URL, while an object-storage adapter (S3/Hostinger)
should return a short-lived signed URL so videos/notes aren't served from app disk long-term.
The streaming endpoints stay permission-gated either way.

## 7. Pre-launch security checklist
- [ ] Strong `DJANGO_SECRET_KEY`, real `ALLOWED_HOSTS`/CSRF origins (prod settings enforce both).
- [ ] PostgreSQL with backups; run `migrate` + `seed_demo` is **dev only** (don't seed prod).
- [ ] HTTPS/HSTS (prod settings already set these), WAF if available.
- [ ] Real email/SMS/WhatsApp/storage adapters wired and tested via Super Admin → Channels.
- [ ] Throttles tuned; **Redis** wired (`REDIS_URL`) so limits are shared across workers.
- [ ] **Sentry** DSN set (error monitoring); structured logs collected (`LOG_LEVEL`).
- [ ] Upload caps (`MAX_*_UPLOAD_MB`) and retention windows (`RETENTION_*`) reviewed.
- [ ] Create the real Super Admin account; **never run `seed_demo` in prod** — delete demo accounts if any.
- [ ] CI green (`.github/workflows/ci.yml` runs ruff/black/mypy/pytest on PostgreSQL + frontend gates).
