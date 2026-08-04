"""Seed a rich, realistic demo dataset so every screen is populated (idempotent)."""

import datetime
import io
import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
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

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Seed even when DEBUG is off. Required outside development — this command "
            "creates accounts with a well-known password.",
        )

    def handle(self, *args, **options):
        # These accounts all share a hardcoded, publicly-known password. Running this against
        # a real deployment would hand out working logins for every role, so refuse unless
        # DEBUG is on (development) or the operator explicitly forces it.
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed demo data with DEBUG=False — this creates accounts with a "
                "publicly-known password. Re-run with --force if you are certain this is a "
                "development or demo environment, never on production."
            )
        random.seed(42)
        users = self._seed_accounts()
        faculty = users["faculty1"]

        course, _ = Course.objects.get_or_create(
            code="FS", defaults={"name": "Full Stack Development"}
        )
        Course.objects.get_or_create(code="DS", defaults={"name": "Data Science Foundations"})

        today = timezone.now().date()
        batch, _ = Batch.objects.get_or_create(
            code="FS-DEMO",
            defaults={
                "name": "Full Stack — Demo Batch",
                "course": course,
                "start_date": today - datetime.timedelta(days=45),
                "end_date": today + datetime.timedelta(days=45),
                "state": BatchState.ACTIVE,
                "class_days": ["mon", "wed", "fri"],
                "class_start_time": datetime.time(18, 0),
                "class_end_time": datetime.time(20, 0),
            },
        )
        # Keep the demo batch current even on re-seed so dashboards stay populated.
        batch.start_date = today - datetime.timedelta(days=45)
        batch.end_date = today + datetime.timedelta(days=45)
        batch.state = BatchState.ACTIVE
        batch.class_days = ["mon", "wed", "fri"]
        batch.class_start_time = datetime.time(18, 0)
        batch.class_end_time = datetime.time(20, 0)
        batch.primary_faculty = faculty
        batch.save(
            update_fields=[
                "start_date",
                "end_date",
                "state",
                "class_days",
                "class_start_time",
                "class_end_time",
                "primary_faculty",
            ]
        )
        batch.faculty.add(faculty)

        students = self._seed_students(batch, users["student1"])
        self._seed_login_attendance(batch, students)
        self._seed_utility_links(users["mis1"])

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
            user, _ = User.objects.get_or_create(
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
            # Repair drift on every run, not just on create. get_or_create never touches an
            # existing row, so a demo account whose role, status *or password* was changed
            # during testing kept the changed value forever while every document still said
            # Demo!passLMS1 — which is exactly what happened to `student1`. Re-seeding is how
            # you get a known-good environment back, so it has to actually restore one.
            user.set_password(PASSWORD)
            user.role = role
            user.status = UserStatus.ACTIVE
            user.save(update_fields=["password", "role", "status"])
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
            student, _ = User.objects.get_or_create(
                username=reg,
                defaults={
                    "role": Role.STUDENT,
                    "full_name": name,
                    "email": f"{reg.lower()}@example.com",
                    "phone": f"98765{idx:05d}",
                    "status": UserStatus.ACTIVE,
                },
            )
            # Same reset as the staff accounts above — a student whose password was changed
            # mid-test must come back to the documented one on re-seed.
            student.set_password(PASSWORD)
            student.status = UserStatus.ACTIVE
            student.save(update_fields=["password", "status"])
            Enrollment.objects.get_or_create(
                student=student,
                batch=batch,
                defaults={"registration_number": reg, "employment_company": company},
            )
            students.append(student)
        return students

    # --- login attendance (login-based, last ~40 days) ---
    def _seed_login_attendance(self, batch, students):
        from attendance.models import AttendanceEvent, AttendanceSource

        today = timezone.now().date()
        for student in students:
            for d in range(40):
                day = today - datetime.timedelta(days=d)
                if random.random() < 0.78:  # ~78% daily login -> realistic attendance %
                    AttendanceEvent.objects.get_or_create(
                        student=student,
                        source=AttendanceSource.LOGIN,
                        reference_id=f"{batch.id}:{day.isoformat()}",
                        defaults={"batch": batch, "date": day},
                    )

    # --- utility links (public notice board, curated by MIS) ---
    def _seed_utility_links(self, mis):
        from engagement.models import UtilityLink

        links = [
            (
                "Full Stack crash course — session recording",
                "https://www.youtube.com/watch?v=nu_pCVPKzTk",
                True,
            ),
            ("React in 100 seconds", "https://www.youtube.com/watch?v=Tn6-PIqc4UM", False),
            ("How the internet works", "https://www.youtube.com/watch?v=x3c1ih2NJEg", False),
        ]
        for title, url, pinned in links:
            UtilityLink.objects.get_or_create(
                title=title, defaults={"url": url, "pinned": pinned, "created_by": mis}
            )

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
