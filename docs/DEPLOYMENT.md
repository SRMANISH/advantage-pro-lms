# Deployment & Go-Live (Hostinger)

How to take Advantage Pro LMS from local dev to production. Most of this is
configuration — the adapter design means no code changes to switch providers.

## 1. Prerequisites
- Hostinger **VPS or Cloud** plan (Python + PostgreSQL; basic shared hosting won't run this).
- PostgreSQL 16, Python 3.12, Node 20 (for building the frontend), Nginx.

## 2. Environment (`backend/.env`)
```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<a long random secret>          # prod refuses to boot without this
DJANGO_ALLOWED_HOSTS=lms.yourdomain.com           # prod refuses the dev default
DATABASE_URL=postgres://USER:PASS@HOST:5432/advantage_pro_lms
FRONTEND_URL=https://lms.yourdomain.com
CORS_ALLOWED_ORIGINS=https://lms.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://lms.yourdomain.com
# Throttles (defaults shown)
THROTTLE_ANON=60/min
THROTTLE_USER=240/min
THROTTLE_LOGIN=10/min
# Real provider adapters (replace the console/local dev stubs)
LMS_EMAIL_ADAPTER=...        # Hostinger SMTP adapter
LMS_SMS_ADAPTER=...          # SMS gateway adapter
LMS_WHATSAPP_ADAPTER=...     # WhatsApp gateway adapter
LMS_STORAGE_ADAPTER=...      # object/video storage adapter
```

## 3. App server
```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements/prod.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000   # behind a systemd unit
```
Put **Nginx** in front for TLS (HTTPS) and to serve the built frontend.

## 4. Frontend
```bash
cd frontend && npm ci && npm run build   # outputs dist/, served by Nginx
```
Serve `dist/` and reverse-proxy `/api` to gunicorn (same origin keeps cookies/CSRF simple).

## 5. Scheduler — cron (no Celery/Redis required)
The time-based features are **idempotent management commands**; point cron at them:
```cron
*/5 * * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_due_reminders          # live-class 1h/15m
0   * * * *  cd /srv/lms/backend && .venv/bin/python manage.py run_escalations              # incomplete tests + 50% attendance
0   8 * * *  cd /srv/lms/backend && .venv/bin/python manage.py send_certificate_reminders   # daily certificate nudges
```
(If you later prefer a worker, swap cron for django-q2/Celery — the commands stay the same.)

## 6. Providers (the adapter swap)
Implement a class per channel against the interfaces in `core/adapters/base.py`
(`EmailAdapter`, `SmsAdapter`, `WhatsAppAdapter`, `StorageAdapter`) and point the
`LMS_*_ADAPTER` env vars at them. No call sites change.

## 7. Pre-launch security checklist
- [ ] Strong `DJANGO_SECRET_KEY`, real `ALLOWED_HOSTS`/CSRF origins (prod settings enforce both).
- [ ] PostgreSQL with backups; run `migrate` + `seed_demo` is **dev only** (don't seed prod).
- [ ] HTTPS/HSTS (prod settings already set these), WAF if available.
- [ ] Real email/SMS/WhatsApp/storage adapters wired and tested via Super Admin → Channels.
- [ ] Throttles tuned; consider error monitoring (Sentry) and structured logging.
- [ ] Create the real Super Admin account; remove demo accounts.
