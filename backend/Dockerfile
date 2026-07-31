FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# requirements.txt is the single source of truth, and it is the file CI audits with
# pip-audit. There used to be a second, looser requirements/{base,prod,dev}.txt tree that this
# image installed instead — it had drifted badly: unpinned ranges, and missing django-q2,
# cryptography, pyotp, requests, redis and sentry-sdk. Since django_q is in INSTALLED_APPS the
# built image could not even start, and no CVE fix applied to requirements.txt ever reached
# it. Adding a second dependency list is how that happens again.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Default (production) command. docker-compose overrides this for local dev.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
