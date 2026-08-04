# Temporary hosting on Render + Vercel (for testing only)

A throwaway environment so other people can click around the real app. **Not production** —
see `docs/DEPLOYMENT.md` and `docs/PRODUCTION_PUSH_REPORT.md` for that.

Total cost on free tiers: **₹0**. Total time: about 40 minutes.

---

## Read this first — the one thing that will break it

The frontend and backend are on **different domains** (`your-app.vercel.app` vs
`your-api.onrender.com`). This app authenticates with a **session cookie**, and the cookie is
set with `SameSite=Lax`, which browsers refuse to send on cross-site requests.

If you deploy them as two independent origins, **login will appear to succeed and then every
subsequent request will be unauthenticated.** You will see the login page accept your password
and immediately bounce you back to it. Nothing in the logs will look wrong.

There are two ways around this. **Take Route A.**

| | Route A — Vercel proxy *(recommended)* | Route B — true cross-origin |
|---|---|---|
| How | Vercel rewrites `/api/*` to Render, so the browser only ever sees one origin | Frontend calls the Render URL directly |
| Cookies | First-party, `SameSite=Lax` works unchanged | Needs `SameSite=None; Secure` |
| CORS | Not needed at all | Must be configured exactly right |
| Code change | **None** | Requires making `SESSION_COOKIE_SAMESITE` env-driven (currently hardcoded in `config/settings/prod.py`) |
| Cost | One extra network hop (~50ms) | Direct |

Route A is written out below. Route B is in the appendix if you specifically need it.

---

## Part 1 — Backend on Render

### 1.1 Create the database

Render dashboard → **New → Postgres**.

- Name: `lms-db`
- Plan: **Free**
- Region: pick the one closest to you (Singapore for India)

Copy the **Internal Database URL** once it finishes provisioning.

> **Free Postgres on Render expires after 30 days** and is then deleted. This is a test
> environment — that is fine, but do not put anything you care about in it.

### 1.2 Create Redis

Render dashboard → **New → Key Value**.

- Name: `lms-redis`
- Plan: **Free**
- **Maxmemory policy: `noeviction`**

Copy the **Internal Key Value URL**.

> `noeviction` matters. The default `allkeys-lru` lets Redis silently drop keys under memory
> pressure, and this app keeps rate-limit counters and the cron lock there. Eviction would
> quietly disable throttling.

Production requires Redis (`prod.py` refuses to boot without `REDIS_URL`) because it backs the
shared cache and rate limiting across workers.

### 1.3 Create the web service

Render dashboard → **New → Web Service** → connect your GitHub repo.

| Field | Value |
|---|---|
| Name | `lms-api` |
| Region | Same as the database |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | **Docker** |
| Plan | Free |

Docker is the right choice here — `backend/Dockerfile` already installs from the pinned,
CI-audited `requirements.txt`, so you get exactly what CI tested.

**Docker Command** (overrides the Dockerfile `CMD`):

```
sh -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --access-logfile -"
```

### 1.4 Environment variables

Add these under **Environment**. Values in `<angle brackets>` are yours to fill in.

```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<paste a 50+ character random string>
DJANGO_ALLOWED_HOSTS=lms-api.onrender.com
DATABASE_URL=<Internal Database URL from step 1.1>
REDIS_URL=<Internal Key Value URL from step 1.2>

CORS_ALLOWED_ORIGINS=https://<your-app>.vercel.app
CSRF_TRUSTED_ORIGINS=https://<your-app>.vercel.app

TRUSTED_PROXY_COUNT=1
Q_CLUSTER_SYNC=true
LMS_ALLOW_CONSOLE_ADAPTERS=1
```

Generate the secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**What each of the last four does, because they are the non-obvious ones:**

- **`TRUSTED_PROXY_COUNT=1`** — Render puts a load balancer in front of your app, so
  `X-Forwarded-For` has exactly one hop you can trust. This is a security setting, not a
  tuning knob: it controls how far the app trusts that header for rate limiting and audit
  logs. Setting it too high starts trusting values the *client* wrote.

- **`Q_CLUSTER_SYNC=true`** — forces background tasks to run inline. Normally, setting
  `REDIS_URL` makes the app queue notifications for a `qcluster` worker process. **Render's
  free tier has no background workers**, so without this flag every email and SMS would sit in
  the queue forever and nobody would receive anything, with no error anywhere. This flag trades
  that for slower requests, which is the right trade for a test box.

- **`LMS_ALLOW_CONSOLE_ADAPTERS=1`** — lets the app boot without real SMTP/SMS/WhatsApp
  credentials. Production refuses to start with the console stubs precisely because they log
  messages instead of sending them. See §1.6 for what this means for testing.

- **Do not set `MEDIA_XACCEL_PREFIX`.** That hands file serving to nginx, which does not exist
  on Render. Leaving it unset makes Django stream files itself.

### 1.5 Deploy and seed

Deploy. When it goes live, open **Shell** on the service:

```bash
python manage.py seed_demo --force
```

`--force` is required: the seeder deliberately refuses to run outside `DEBUG` because it
creates accounts with a publicly known password. That guard is doing its job here — you are
overriding it knowingly, on a throwaway box.

This gives you the full demo dataset — see `docs/TESTING_GUIDE.md` for every account and
password.

Check it is alive:

```
https://lms-api.onrender.com/api/v1/health/    -> {"status":"ok"}
https://lms-api.onrender.com/api/v1/ready/     -> {"status":"ready"}
```

If `/ready/` returns 503, it names the failing dependency (`database` or `cache`) — that tells
you which of the two URLs above is wrong.

### 1.6 What will not work, and why

Be clear about this before you demo to anyone.

| Limitation | Effect | Cause |
|---|---|---|
| **Uploaded files vanish on redeploy** | Videos and materials 404 after any deploy | Render's free filesystem is ephemeral. Rows survive, bytes do not |
| **No email / SMS / WhatsApp** | Setup links and OTPs are printed to the Render log, not delivered | `LMS_ALLOW_CONSOLE_ADAPTERS=1` |
| **First request is slow** | ~50 second cold start | Free services sleep after 15 minutes idle |
| **Cron jobs do not run** | Reminders and escalations only fire if you run them by hand | Free tier has no scheduler |
| **Database expires in 30 days** | Everything is deleted | Render free Postgres policy |

**To complete a student setup flow without email:** the setup link is written to the Render
log. Open **Logs**, trigger the invite, and copy the `/setup/<token>` URL. Or use the
already-activated demo accounts, which is simpler.

**To run a cron job by hand,** from the Shell:

```bash
python manage.py send_absence_reminders
python manage.py run_escalations
python manage.py send_certificate_reminders
python manage.py send_due_reminders
python manage.py send_engagement_reminders
python manage.py purge_old_data
```

---

## Part 2 — Frontend on Vercel

### 2.1 Import the project

Vercel dashboard → **Add New → Project** → import the same repo.

| Field | Value |
|---|---|
| Framework Preset | **Vite** |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

### 2.2 Add the proxy — this is the step that makes cookies work

Create `frontend/vercel.json`:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://lms-api.onrender.com/api/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

Two rewrites, both load-bearing:

1. **The API proxy.** The browser sends every API call to the Vercel domain; Vercel forwards it
   to Render. Because the browser only ever sees one origin, the session cookie is first-party
   and `SameSite=Lax` behaves normally. This is what avoids the whole problem in the box at the
   top of this document.

2. **The SPA fallback.** React Router owns the routes. Without this, refreshing on
   `/admin/batches` asks Vercel for a file at that path and gets a 404.

**Do not set `VITE_API_URL`.** The client defaults to the relative `/api/v1`, which is exactly
what the proxy expects. Setting it to the Render URL would bypass the proxy and reintroduce the
cross-origin cookie problem.

### 2.3 Deploy, then close the loop

Deploy. Note your URL (e.g. `https://advantage-pro-lms.vercel.app`).

Now go **back to Render** and correct the two origin variables to the real Vercel URL:

```
CORS_ALLOWED_ORIGINS=https://advantage-pro-lms.vercel.app
CSRF_TRUSTED_ORIGINS=https://advantage-pro-lms.vercel.app
```

`CSRF_TRUSTED_ORIGINS` is the one that matters through the proxy: Django validates the `Origin`
header on writes, and through the rewrite that header is the Vercel domain. Get this wrong and
every login POST fails with `CSRF verification failed` while reads work fine.

Render redeploys automatically. Then open your Vercel URL and sign in as
`superadmin1` / `Demo!passLMS1`.

---

## Part 3 — Verify the deployment

Five checks, in order. Each one fails differently, so the order tells you where the problem is.

1. **`GET /api/v1/health/` on the Render URL** → `{"status":"ok"}`
   Fails ⇒ the service did not boot. Check Render logs for `ImproperlyConfigured` — `prod.py`
   fails fast and names the missing variable.

2. **`GET /api/v1/ready/` on the Render URL** → `{"status":"ready"}`
   Returns 503 ⇒ read `failed`: `database` or `cache` tells you which URL is wrong.

3. **Vercel URL loads the landing page.**
   Fails ⇒ build problem, check the Vercel build log.

4. **Open `https://<vercel-url>/api/v1/health/` in the browser** → same JSON as step 1.
   Fails ⇒ the rewrite in `vercel.json` is wrong or the file is in the wrong directory.

5. **Log in as `superadmin1` / `Demo!passLMS1`, then refresh the page.**
   Login works but the refresh bounces you to login ⇒ **the cookie is not sticking.** Confirm
   you did not set `VITE_API_URL`, and that `vercel.json` is at `frontend/vercel.json`.

---

## Appendix — Route B (true cross-origin)

Only if you specifically need the frontend calling Render directly.

**This requires a code change.** `config/settings/prod.py` hardcodes:

```python
SESSION_COOKIE_SAMESITE = "Lax"
```

It has to become environment-driven:

```python
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
```

Then set on Render:

```
SESSION_COOKIE_SAMESITE=None
CSRF_COOKIE_SAMESITE=None
```

and on Vercel:

```
VITE_API_URL=https://lms-api.onrender.com/api/v1
```

`SameSite=None` requires `Secure`, which `prod.py` already sets, and both platforms serve
HTTPS — so this does work. But you are weakening a cookie protection to solve a problem the
proxy solves for free, and you now have to keep CORS and CSRF origins exactly in step. **I do
not recommend it.**

Ask me and I will make that settings change if you want it.

---

## Tearing it down

Free Postgres self-destructs at 30 days. Everything else you should delete by hand:
Render → each service → Settings → Delete; Vercel → Project → Settings → Delete.

Nothing in this environment should be reused for production. The production path starts fresh
in `docs/PRODUCTION_PUSH_REPORT.md`.
