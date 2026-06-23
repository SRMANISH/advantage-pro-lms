"""Seed a rich, realistic demo dataset so every screen is populated (idempotent)."""

import datetime
import io
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserStatus
from assessments.models import Choice, Question, Task, TaskSubmission, Test, TestAttempt
from attendance.models import AttendanceEvent
from batches.models import Batch, BatchState, Course
from content.models import Material, Video, VideoProgress
from core.adapters.registry import get_storage
from core.roles import Role
from enrollments.models import Enrollment
from forum.models import Reply, Thread
from liveclasses.models import CheckIn, LiveClass

PASSWORD = "Demo!passLMS1"  # local development only

STAFF = [
    ("student1", Role.STUDENT, "Demo Student"),
    ("faculty1", Role.FACULTY, "Anita Sharma"),
    ("admin1", Role.ADMIN, "Demo Admin"),
    ("mis1", Role.MIS, "Demo MIS"),
    ("counselor1", Role.COUNSELOR, "Demo Counselor"),
    ("techsupport1", Role.TECH_SUPPORT, "Demo Tech Support"),
    ("superadmin1", Role.SUPER_ADMIN, "Demo Super Admin"),
]

DEMO_STUDENTS = [
    ("S101", "Asha Rao", "Infosys"),
    ("S102", "Ravi Kumar", "TCS"),
    ("S103", "Meena Iyer", "Wipro"),
    ("S104", "Karthik Nair", ""),
    ("S105", "Sneha Patel", "Accenture"),
    ("S106", "Arjun Menon", "Infosys"),
    ("S107", "Divya Suresh", ""),
    ("S108", "Rahul Verma", "Cognizant"),
]

VIDEOS = [
    ("Course intro & setup", "videos/seed/intro.mp4"),
    ("State management deep dive", "videos/seed/state.mp4"),
    ("Routing & navigation", "videos/seed/routing.mp4"),
]


class Command(BaseCommand):
    help = "Seed demo accounts, a populated batch, content, assessments, forum and attendance."

    def handle(self, *args, **options):
        random.seed(42)
        users = self._seed_accounts()
        faculty = users["faculty1"]

        course, _ = Course.objects.get_or_create(
            code="FS", defaults={"name": "Full Stack Development"}
        )
        Course.objects.get_or_create(code="DS", defaults={"name": "Data Science Foundations"})

        batch, _ = Batch.objects.get_or_create(
            code="FS-DEMO",
            defaults={
                "name": "Full Stack — Demo Batch",
                "course": course,
                "start_date": datetime.date(2026, 1, 1),
                "end_date": datetime.date(2026, 4, 1),
                "state": BatchState.ACTIVE,
            },
        )
        batch.faculty.add(faculty)

        students = self._seed_students(batch, users["student1"])

        if not Video.objects.filter(batch=batch).exists():
            self._seed_content(batch, faculty, students)
            self._seed_tests(batch, faculty, students)
            self._seed_tasks(batch, faculty, students)
            self._seed_forum(batch, faculty, students)
            self._seed_live(batch, faculty, students)
            self.stdout.write("seeded content, tests, tasks, forum, live classes, attendance")
        else:
            self.stdout.write("rich content already seeded — skipped")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Password for all demo accounts: {PASSWORD}"))

    # --- accounts ---
    def _seed_accounts(self):
        users = {}
        for username, role, full_name in STAFF:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "full_name": full_name,
                    "email": f"{username}@example.com",
                    "phone": "9876500000",
                    "status": UserStatus.ACTIVE,
                    "is_staff": role == Role.SUPER_ADMIN,
                    "is_superuser": role == Role.SUPER_ADMIN,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
            users[username] = user
        return users

    def _seed_students(self, batch, demo_student):
        Enrollment.objects.get_or_create(
            student=demo_student,
            batch=batch,
            defaults={"registration_number": "student1", "employment_company": "Infosys"},
        )
        students = [demo_student]
        for idx, (reg, name, company) in enumerate(DEMO_STUDENTS):
            student, created = User.objects.get_or_create(
                username=reg,
                defaults={
                    "role": Role.STUDENT,
                    "full_name": name,
                    "email": f"{reg.lower()}@example.com",
                    "phone": f"98765{idx:05d}",
                    "status": UserStatus.ACTIVE,
                },
            )
            if created:
                student.set_password(PASSWORD)
                student.save()
            Enrollment.objects.get_or_create(
                student=student,
                batch=batch,
                defaults={"registration_number": reg, "employment_company": company},
            )
            students.append(student)
        return students

    # --- content ---
    def _seed_content(self, batch, faculty, students):
        storage = get_storage()
        videos = []
        for order, (title, key) in enumerate(VIDEOS):
            storage.save(key, io.BytesIO(b"\x00\x00\x00\x18ftypmp42seed-placeholder"))
            videos.append(
                Video.objects.create(
                    batch=batch, title=title, storage_key=key, order=order, uploaded_by=faculty
                )
            )
        for title, key in [
            ("Hooks cheat-sheet", "materials/seed/hooks.pdf"),
            ("Setup guide", "materials/seed/setup.pdf"),
        ]:
            storage.save(key, io.BytesIO(b"%PDF-1.4 seed placeholder"))
            Material.objects.create(batch=batch, title=title, storage_key=key, uploaded_by=faculty)

        # ~70% of students complete the first two videos.
        for video in videos[:2]:
            for student in students:
                if random.random() < 0.7:
                    VideoProgress.objects.create(
                        video=video,
                        student=student,
                        percent=100,
                        watched_seconds=600,
                        last_position=600,
                        completed=True,
                    )
                    self._present(student, batch, "video", video.id)

    # --- tests ---
    def _seed_tests(self, batch, faculty, students):
        test = Test.objects.create(batch=batch, title="Quiz 1 — Fundamentals", created_by=faculty)
        specs = [
            ("2 + 2 = ?", ["3", "4", "5"], 1),
            ("Capital of France?", ["Rome", "Paris", "Berlin"], 1),
            (
                "HTML stands for?",
                ["Hyper Text Markup Language", "Hot Mail", "How To Make Lunch"],
                0,
            ),
        ]
        questions = []
        for text, choices, correct in specs:
            q = Question.objects.create(test=test, text=text)
            for i, c in enumerate(choices):
                Choice.objects.create(question=q, text=c, is_correct=(i == correct))
            questions.append(q)
        Test.objects.create(batch=batch, title="Quiz 2 — Components", created_by=faculty)

        for student in students:
            if random.random() < 0.75:
                score = random.randint(1, 3)
                TestAttempt.objects.create(test=test, student=student, score=score, total=3)
                self._present(student, batch, "test", test.id)

    # --- tasks ---
    def _seed_tasks(self, batch, faculty, students):
        past = timezone.now() - datetime.timedelta(days=2)
        task = Task.objects.create(
            batch=batch,
            title="Build a TODO app",
            description="Submit your repo link.",
            deadline=past,
            created_by=faculty,
        )
        Task.objects.create(
            batch=batch,
            title="Portfolio page",
            description="Build a personal page.",
            deadline=timezone.now() + datetime.timedelta(days=5),
            created_by=faculty,
        )
        for i, student in enumerate(students):
            if random.random() < 0.6:
                graded = i % 2 == 0
                TaskSubmission.objects.create(
                    task=task,
                    student=student,
                    text="Here is my submission.",
                    is_late=random.random() < 0.3,
                    score=random.randint(6, 10) if graded else None,
                    feedback="Well done." if graded else "",
                )
                self._present(student, batch, "task", task.id)

    # --- forum ---
    def _seed_forum(self, batch, faculty, students):
        threads = [
            ("How does useState batch updates?", "I'm confused about re-renders.", True),
            ("Deadline extension for TODO app?", "Can we get two more days?", False),
            ("Recommended VS Code extensions?", "What do you all use?", False),
        ]
        for (title, body, resolved), student in zip(threads, students[1:4], strict=False):
            thread = Thread.objects.create(
                batch=batch, author=student, title=title, body=body, resolved=resolved
            )
            if resolved:
                Reply.objects.create(
                    thread=thread,
                    author=faculty,
                    body="Great question — see the docs section we covered.",
                )

    # --- live classes ---
    def _seed_live(self, batch, faculty, students):
        past = LiveClass.objects.create(
            batch=batch,
            title="Hooks deep dive (recording soon)",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            platform="Google Meet",
            meeting_link="https://meet.example.com/hooks",
            created_by=faculty,
        )
        LiveClass.objects.create(
            batch=batch,
            title="Routing workshop",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            platform="Google Meet",
            meeting_link="https://meet.example.com/routing",
            created_by=faculty,
        )
        for student in students:
            if random.random() < 0.65:
                CheckIn.objects.get_or_create(live_class=past, student=student)
                self._present(student, batch, "live", past.id)

    @staticmethod
    def _present(student, batch, source, ref):
        AttendanceEvent.objects.get_or_create(
            student=student,
            source=source,
            reference_id=str(ref),
            defaults={"batch": batch, "date": timezone.now().date()},
        )
