# Deploy handoff — Render + Vercel test environment

Self-contained state of the in-progress test deployment. Written so someone with no prior
context — an agent or a person — can continue from exactly here.

**This is a throwaway TEST environment, not production.** Production is `docs/DEPLOYMENT.md`
and `docs/PRODUCTION_PUSH_REPORT.md`. Do not reuse anything from here for it.

---

## 1. Repo and layout

- **GitHub:** `https://github.com/SRMANISH/advantage-pro-lms` — branch `main` is the source of
  truth; `full-codebase-review` is kept byte-identical for a review PR.
- **Backend:** `backend/` — Django 5.2.16 + DRF. `backend/Dockerfile` installs from the pinned,
  CI-audited `backend/requirements.txt`.
- **Frontend:** `frontend/` — React 18 + Vite SPA.
- **Deploy files:** `render.yaml` (Blueprint, repo root), `backend/render-start.sh` (start
  script), `frontend/vercel.json` (API proxy + SPA fallback).
- **Reference docs:** `docs/TEMP_HOSTING_RENDER_VERCEL.md` (full walkthrough),
  `docs/TESTING_GUIDE.md` (accounts and passwords).

## 2. What has happened so far

1. **Blueprint imported successfully.** Render created three services in region `singapore`:
   - `lms-db` — free Postgres (auto-deletes after 30 days)
   - `lms-redis` — free Key Value, `maxmemoryPolicy: noeviction`
   - `advantage-pro-lms-api` — Docker web service from `backend/Dockerfile`

   `DATABASE_URL` / `REDIS_URL` are wired by reference in the blueprint;
   `DJANGO_ALLOWED_HOSTS` is set to the public `advantage-pro-lms-api.onrender.com` host;
   `DJANGO_SECRET_KEY` is Render-generated.

2. **First deploy: build succeeded, start failed.**
   - Build proof: `Successfully installed Django-5.2.16 ... django-q2 ... cryptography-49.0.0`.
   - Failure: `sh: 1: python manage.py migrate ... : not found`, **exit 127**.
   - Root cause: `render.yaml` used an inline `dockerCommand: sh -c "a && b && c"`. Render
     **tokenises** that field instead of running it through a shell, so `sh` received the whole
     quoted pipeline as one program name.

3. **Fix — committed and pushed (`37b23e9`).**
   - `backend/render-start.sh` — migrate → collectstatic → optional seed → `exec gunicorn`,
     honouring Render's `$PORT` and `$WEB_CONCURRENCY`. Verified LF endings, passes `sh -n`.
   - `render.yaml` → `dockerCommand: sh ./render-start.sh`.
   - New env var `SEED_DEMO` (default `"false"`) — the free tier has no Shell tab, so seeding
     is done by flipping this flag for one deploy. The script passes `--force` because
     `seed_demo` refuses to run outside DEBUG (it creates accounts with a public password).
   - `.gitattributes` forces `*.sh` to `eol=lf`, so a CRLF shebang can never reach Linux and
     fail as `/usr/bin/env sh\r: not found`.

4. **Second deploy: service started, health check failed with `DisallowedHost`.**
   - Failure: `Invalid HTTP_HOST header: 'advantage-pro-lms-api.onrender.com'`.
   - Root cause: the blueprint used `fromService.property: host` for `DJANGO_ALLOWED_HOSTS`.
     Render documents that value as the private-network hostname, not the public
     `*.onrender.com` hostname.
   - Fix: `render.yaml` now sets `DJANGO_ALLOWED_HOSTS=advantage-pro-lms-api.onrender.com`,
     and `prod.py` also adds Render's runtime `RENDER_EXTERNAL_HOSTNAME` as a safety net.

## 3. What to do next — resume here

### Step A — redeploy the backend with the host fix

If the Render service auto-deploys on push it may already be rebuilding; otherwise
**Manual Deploy → Deploy latest commit** on `advantage-pro-lms-api`. If the Blueprint does not
auto-sync the environment variable, set this manually on the Render service before deploying:

```
DJANGO_ALLOWED_HOSTS=advantage-pro-lms-api.onrender.com
```

Expected in the logs: `==> Applying migrations`, `==> Collecting static files`, `==> Starting
gunicorn`. Then the service goes **Live**.

### Step B — seed the demo data

1. Service → **Environment** → set `SEED_DEMO=true` → **Save** (triggers a redeploy).
2. Watch the logs for `==> Seeding demo data`.
3. Set `SEED_DEMO=false` again (leaving it on re-seeds every restart, which resets the demo
   passwords).

### Step C — confirm the backend is alive

Free services cold-start (~50s on first hit).

- `https://advantage-pro-lms-api.onrender.com/api/v1/health/` → `{"status":"ok"}`
- `https://advantage-pro-lms-api.onrender.com/api/v1/ready/` → `{"status":"ready"}`
  A 503 names the failing dependency (`database` or `cache`).

### Step D — deploy the frontend on Vercel

1. [vercel.com/new](https://vercel.com/new) → import the same repo.
2. **Root Directory: `frontend`** (the one setting to change; it auto-detects Vite).
3. Deploy. No environment variables — `frontend/vercel.json` already proxies `/api` to the
   Render host and provides the SPA fallback.

### Step E — close the CORS/CSRF loop *(this is the step people miss)*

Two env vars on the Render service are intentionally **blank** (`sync: false` in the blueprint)
because the Vercel URL did not exist at import time. Set both to the real Vercel URL now:

```
CORS_ALLOWED_ORIGINS=https://<your-app>.vercel.app
CSRF_TRUSTED_ORIGINS=https://<your-app>.vercel.app
```

`CSRF_TRUSTED_ORIGINS` is the one that bites: without it, reads work but every login POST fails
`CSRF verification failed`. Render redeploys automatically after the save.

### Step F — log in

Open the Vercel URL, sign in as `superadmin1` / `Demo!passLMS1`, then **refresh**. If login
works but the refresh bounces to login, the cookie is not sticking — confirm `VITE_API_URL` is
**not** set on Vercel and `frontend/vercel.json` is present. Full account list in
`docs/TESTING_GUIDE.md`.

## 4. Known limitations of this environment

| Limitation | Cause |
|---|---|
| Uploaded files vanish on redeploy | Render free filesystem is ephemeral |
| No email / SMS / WhatsApp | `LMS_ALLOW_CONSOLE_ADAPTERS=1`; messages print to the log |
| ~50s cold start | Free services sleep after 15 min idle |
| Cron jobs do not run | No scheduler; run by hand if needed (`send_absence_reminders`, etc.) |
| Database deleted after 30 days | Render free Postgres policy |

## 5. If the service name is taken

`advantage-pro-lms-api.onrender.com` must be globally unique. If the blueprint import fails on
the name, change `name:` in **`render.yaml`** *and* the proxy `destination` in
**`frontend/vercel.json`** to the same new value, then push — they must match, or the proxy
points at the wrong backend.

## 6. Why the cross-origin proxy matters (do not "simplify" it away)

`SESSION_COOKIE_SAMESITE` is hardcoded to `"Lax"` in `config/settings/prod.py`. The Vercel
`rewrites` in `vercel.json` make the browser see a single origin, so the session cookie stays
first-party and works. If someone sets `VITE_API_URL` to call Render directly, login succeeds
and then every following request is silently unauthenticated. The appendix in
`docs/TEMP_HOSTING_RENDER_VERCEL.md` covers the true cross-origin route and the settings change
it needs — but the proxy is the intended path.
