# Load test — first real run

The Locust harness (`backend/loadtest/locustfile.py`) had never been executed; this
records an actual run so "handles a batch of N" stops being a guess. **These are indicative
local numbers, not a staging benchmark** — read the caveats before quoting them.

## How it was run
```bash
# one dev server process, throttles relaxed so the load test measures the endpoints, not the limiter
THROTTLE_LOGIN=100000/min THROTTLE_USER=1000000/min THROTTLE_ANON=1000000/min \
  python manage.py runserver 8000 --noreload
LMS_STUDENT_USER=S101 LMS_STUDENT_PASS=Demo!passLMS1 LMS_FACULTY_PASS=Demo!passLMS1 \
  locust -f loadtest/locustfile.py --host http://localhost:8000 --headless -u 30 -r 6 -t 30s
```

## Results (30 users, 30s)
Authenticated read endpoints — the hot student-browsing paths — are single- to low-double-digit
milliseconds at the median; the Phase-4 prefetch/aggregate work holds up:

| Endpoint | median | p95 | p99 |
|---|---|---|---|
| GET `/videos/` | 16 ms | 180 ms | 230 ms |
| GET `/notifications/unread-count/` | 12 ms | 97 ms | 260 ms |
| GET `/notifications/` | 15 ms | 90 ms | 150 ms |
| GET `/threads/` | 20 ms | 350 ms | 350 ms |
| GET `/dashboard/` | 29 ms | 380 ms | 510 ms |
| POST `/auth/login/` | 830 ms | 1300 ms | 1300 ms |
| POST `/liveclasses/` (schedule) | 530 ms | — | — |
| POST `/liveclasses/{id}/cancel/` | 990 ms | — | — |

- **Login is deliberately ~0.8 s** — argon2 password hashing is intentionally slow; it is not a
  throughput path.
- **Live-class schedule/cancel is slow because the notification fan-out runs synchronously in dev.**
  In production `Q_CLUSTER` queues the email/SMS/WhatsApp sends (django-q2), so the request returns
  after the in-app write and these numbers drop sharply.

## What the run surfaced (and we fixed)
A concurrency bug: the first-login device bind used `filter(...).first()` then `create()`, so two
simultaneous first logins for the same student raced and the loser hit
`IntegrityError: UNIQUE constraint failed: accounts_devicebinding.user_id` (HTTP 500). Fixed to
`get_or_create` (`accounts/device.py`) — same fix class as the escalation/attempt races. (The 3%
failure rate in this run was this contention, amplified by 30 virtual users sharing one student
account — an artifact of the test setup, not a production pattern.)

## Caveats (why this is not a staging benchmark)
1. **SQLite**, not PostgreSQL 16 — no connection pool, single-writer; prod numbers will differ.
2. **One `runserver` process**, not gunicorn `2×CPU+1` workers — no real parallelism.
3. **One shared student account** inflated device-bind contention; real load = distinct students.
4. Throttles were relaxed to measure the endpoints; production keeps `login=10/min`, `user=240/min`.

Re-run against the actual VPS (Postgres + gunicorn + Redis + qcluster) before quoting SLAs.
