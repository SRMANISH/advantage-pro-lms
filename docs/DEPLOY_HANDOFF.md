# Deploy handoff — Render + Vercel test environment

Self-contained state of the in-progress test deployment. Written so someone with no prior
context — an agent or a person — can continue from exactly here.

**Last updated at commit:** see `git log --oneline -1` (this file ships with the fix for the
first deploy failure).

---

## 1. Repo and layout

- **GitHub:** `https://github.com/SRMANISH/advantage-pro-lms` — branch `main` is the source of
  truth; `full-codebase-review` is kept byte-identical to it for a review PR.
- **Backend:** `backend/` — Django 5.2.16 + DRF, Dockerfile installs from the pinned,
  CI-audited `backend/requirements.txt`.
- **Frontend:** `frontend/` — React 18 + Vite SPA.
- **Deploy files:** `render.yaml` (Blueprint, repo root), `backend/render-start.sh` (start
  script), `frontend/vercel.json` (proxy + SPA fallback).
- **Reference docs:** `docs/TEMP_HOSTING_RENDER_VERCEL.md` (full walkthrough),
  `docs/TESTING_GUIDE.md` (accounts/passwords), `docs/DEPLOYMENT.md` (real production — do not
  confuse with this test setup).

## 2. What has happened so far

1. **Blueprint imported successfully.** Render created three services in region `singapore`:
   - `lms-db` — free Postgres (auto-deletes after 30 days)
   - `lms-redis` — free Key Value, `maxmemoryPolicy: noeviction`
   - `advantage-pro-lms-api` — Docker web service from `backend/Dockerfile`
   `DATABASE_URL` / `REDIS_URL` / `DJANGO_ALLOWED_HOSTS` are wired by reference in the
   blueprint; `DJANGO_SECRET_KEY` is Render-generated.

2. **First deploy: build succeeded, start failed.**
   - Build proof: `Successfully installed Django-5.2.16 ... django-q2 ... cryptography-49.0.0`
     — confirms the earlier Dockerfile fix (it used to install a stale requirements tree
     missing six packages).
   - Failure: `sh: 1: python manage.py migrate ... : not found`, **exit 127**.
   - **Root cause:** `render.yaml` used an inline
     `dockerCommand: sh -c "a && b && c"`. Render **tokenises** that field instead of running
     it through a shell, so `sh` received the entire quoted pipeline as a single program name.

3. **Fix (in this commit):**
   - `backend/render-start.sh` — migrate → collectstatic → optional seed → `exec gunicorn`,
     honouring Render's `$PORT` and `$WEB_CONCURRENCY`. Verified: `sh -n` passes, LF endings,
     and `.gitattributes` now forces `eol=lf` for `*.sh` so no git config can mangle it.
   - `render.yaml` → `dockerCommand: sh ./render-start.sh` (relative to `dockerContext:
     ./backend`).
   - New env var `SEED_DEMO` (default `"false"`) — **the free tier has no Shell tab**, so
     seeding is done by flipping this to `true` for one deploy. The script passes `--force`
     because `seed_demo` refuses to run outside DEBUG (it creates acc