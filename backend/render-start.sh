#!/usr/bin/env sh
# Start script for the Render test environment.
#
# This exists because Render's `dockerCommand` is tokenised rather than run through a shell,
# so an inline `sh -c "a && b && c"` gets handed to sh as a single program name and dies with
# `not found` (exit 127). A script file sidesteps the quoting entirely.
#
# TEST ENVIRONMENT. docs/DEPLOYMENT.md is the production path, where migrate is a deliberate
# step and gunicorn runs under systemd.

set -e

echo "==> Applying migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

# Opt-in demo data. Set SEED_DEMO=true in the Render dashboard, redeploy once, then set it
# back to false — otherwise every restart re-seeds (harmless, since the seeder is idempotent,
# but it also resets the demo passwords, which would undo any you changed while testing).
#
# --force is required because seed_demo refuses to run outside DEBUG: it creates accounts with
# a publicly known password. That guard is doing its job; this overrides it knowingly, on a
# throwaway box. Never set this in production.
if [ "$SEED_DEMO" = "true" ]; then
  echo "==> Seeding demo data (SEED_DEMO=true)"
  python manage.py seed_demo --force
fi

echo "==> Starting gunicorn"
# WEB_CONCURRENCY is set by Render from the instance size — respect it rather than hardcoding
# a worker count that could exhaust a free instance's memory.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 60 \
  --access-logfile -
