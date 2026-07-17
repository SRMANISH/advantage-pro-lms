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

## 5. Scheduler — cron (no Celery/Redis required)
The time-based features are **idempotent management commands**; point cron at them:
```cron
*/5 * * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_due_reminders          # live-class 1h/15m (skips cancelled)
0   * * * *  cd /srv/lms/backend && .venv/bin/python manage.py run_escalations              # incomplete tests + 50% attendance
0   8 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_certificate_reminders   # weekly certificate nudges (MIS follow-up)
30  8 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_absence_reminders        # login-attendance absentees (today)
0   9 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_engagement_reminders     # LinkedIn / Google review / next-plan
0   3 * * 0  cd /srv/lms/backend && .venv/bin/python manage.py purge_old_data                 # retention: old audit logs + read notifications
```
(If you later prefer a worker, swap cron for django-q2/Celery — the commands stay the same.)
`purge_old_data` only removes activity data (audit logs, read notifications) past the retention
window; it never touches enrolments, attendance, submissions, or certificates. Use `--dry-run`
to preview.

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
