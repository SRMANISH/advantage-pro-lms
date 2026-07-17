"""Locust load scenarios for the audit's §18 targets.

Run against a staging/dev instance (NEVER production seed data you care about):

    pip install locust
    locust -f backend/loadtest/locustfile.py --host http://localhost:8000 \
        -u 200 -r 20   # 200 users, 20 spawned/s

Env knobs:
    LMS_STUDENT_USER / LMS_STUDENT_PASS   (default student1 / Adv123*)
    LMS_FACULTY_USER / LMS_FACULTY_PASS   (default faculty1 / Demo!passLMS1)
    LMS_STREAM_VIDEO_ID                   (optional: a video UUID to hammer /play/)

Scenarios (weights approximate the audit's mix):
  * StudentBrowsing — the "200 browsing users" case: login once, then poll the
    dashboard, video list, notifications and unread count like the SPA does.
  * FacultyScheduleBurst — the "500-student class schedule" case: schedule + cancel a
    live class, exercising the notification fan-out path end to end.
  * VideoStreaming — the "8 concurrent streams" case: ranged GETs against /play/
    (or the X-Accel redirect, wherever delivery is configured).
"""

from __future__ import annotations

import datetime
import os
import uuid

from locust import HttpUser, between, tag, task

STUDENT_USER = os.environ.get("LMS_STUDENT_USER", "student1")
STUDENT_PASS = os.environ.get("LMS_STUDENT_PASS", "Adv123*")
FACULTY_USER = os.environ.get("LMS_FACULTY_USER", "faculty1")
FACULTY_PASS = os.environ.get("LMS_FACULTY_PASS", "Demo!passLMS1")
STREAM_VIDEO_ID = os.environ.get("LMS_STREAM_VIDEO_ID", "")


class _SessionUser(HttpUser):
    """Shared session-cookie + CSRF login helper (mirrors the SPA's auth)."""

    abstract = True
    username = ""
    password = ""
    role: str | None = None

    def on_start(self) -> None:
        self.client.get("/api/v1/auth/csrf/", name="/auth/csrf/")
        self._refresh_csrf()
        body = {"username": self.username, "password": self.password}
        if self.role:
            body["role"] = self.role
        # Students are device-bound (accounts.device): the login is rejected without a
        # device id, exactly like the SPA sends. One stable id per simulated user so the
        # first login binds it and the rest match.
        body["device_id"] = f"loadtest-{self.username}"
        with self.client.post(
            "/api/v1/auth/login/", json=body, name="/auth/login/", catch_response=True
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"login failed ({resp.status_code}): {resp.text[:200]}")
        self._refresh_csrf()

    def _refresh_csrf(self) -> None:
        token = self.client.cookies.get("csrftoken", "")
        if token:
            self.client.headers["X-CSRFToken"] = token
            self.client.headers["Referer"] = self.host or "http://localhost:8000"


class StudentBrowsing(_SessionUser):
    """A student clicking around: dashboard, videos, notifications polling."""

    weight = 20
    wait_time = between(2, 6)
    username = STUDENT_USER
    password = STUDENT_PASS
    role = "student"

    @task(4)
    def dashboard(self) -> None:
        self.client.get("/api/v1/dashboard/", name="/dashboard/")

    @task(3)
    def videos(self) -> None:
        self.client.get("/api/v1/videos/", name="/videos/")

    @task(2)
    def notifications(self) -> None:
        self.client.get("/api/v1/notifications/", name="/notifications/")
        self.client.get("/api/v1/notifications/unread-count/", name="/notifications/unread-count/")

    @task(1)
    def forum(self) -> None:
        self.client.get("/api/v1/threads/?page_size=25", name="/threads/")


class FacultyScheduleBurst(_SessionUser):
    """Schedules (then cancels) live classes — the notification fan-out hot path."""

    weight = 1
    wait_time = between(10, 20)
    username = FACULTY_USER
    password = FACULTY_PASS
    role = "faculty"

    def on_start(self) -> None:
        super().on_start()
        batches = self.client.get("/api/v1/forum/batches/", name="/forum/batches/").json()
        self.batch_id = batches[0]["id"] if batches else ""

    @task
    @tag("burst")
    def schedule_and_cancel(self) -> None:
        if not self.batch_id:
            return
        starts = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3)).isoformat()
        resp = self.client.post(
            "/api/v1/liveclasses/",
            json={
                "batch": self.batch_id,
                "title": f"Load test {uuid.uuid4().hex[:6]}",
                "scheduled_at": starts,
                "platform": "Google Meet",
                "meeting_link": "https://meet.example/load",
            },
            name="/liveclasses/ [create]",
        )
        if resp.status_code in (200, 201):
            live_id = resp.json().get("id")
            self.client.post(
                f"/api/v1/liveclasses/{live_id}/cancel/",
                json={"reason": "load test cleanup"},
                name="/liveclasses/{id}/cancel/",
            )


class VideoStreaming(_SessionUser):
    """Ranged requests against video delivery (set LMS_STREAM_VIDEO_ID)."""

    weight = 2 if STREAM_VIDEO_ID else 0
    wait_time = between(1, 3)
    username = STUDENT_USER
    password = STUDENT_PASS
    role = "student"

    @task
    @tag("stream")
    def stream_chunk(self) -> None:
        if not STREAM_VIDEO_ID:
            return
        self.client.get(
            f"/api/v1/videos/{STREAM_VIDEO_ID}/play/",
            headers={"Range": "bytes=0-1048575"},
            name="/videos/{id}/play/ [1MB range]",
        )
