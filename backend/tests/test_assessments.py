"""MCQ tests: build, auto-grade, one attempt, role rules, hidden answers."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from assessments.models import Choice, Question, Test, TestAttempt
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment

TESTS_URL = "/api/v1/tests/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "student": student}


def build_payload(batch):
    return {
        "batch": str(batch.id),
        "title": "Quiz 1",
        "questions": [
            {
                "text": "2 + 2 = ?",
                "choices": [
                    {"text": "3", "is_correct": False},
                    {"text": "4", "is_correct": True},
                ],
            },
            {
                "text": "Capital of France?",
                "choices": [
                    {"text": "Paris", "is_correct": True},
                    {"text": "Rome", "is_correct": False},
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_faculty_creates_test(world):
    resp = client_for(world["fac"]).post(TESTS_URL, build_payload(world["batch"]), format="json")
    assert resp.status_code == 201
    assert Test.objects.filter(title="Quiz 1").count() == 1
    assert Question.objects.count() == 2
    assert Choice.objects.filter(is_correct=True).count() == 2


@pytest.mark.django_db
def test_student_cannot_create_test(world):
    resp = client_for(world["student"]).post(
        TESTS_URL, build_payload(world["batch"]), format="json"
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_mis_can_create_test_but_admin_cannot(world):
    # MCQ test creation is MIS + Faculty only under the updated procedure.
    mis = user("mis", Role.MIS)
    admin = user("adm", Role.ADMIN)
    assert (
        client_for(mis).post(TESTS_URL, build_payload(world["batch"]), format="json").status_code
        == 201
    )
    assert (
        client_for(admin).post(TESTS_URL, build_payload(world["batch"]), format="json").status_code
        == 403
    )


@pytest.mark.django_db
def test_student_take_view_hides_correct_answers(world):
    client_for(world["fac"]).post(TESTS_URL, build_payload(world["batch"]), format="json")
    test = Test.objects.get(title="Quiz 1")
    resp = client_for(world["student"]).get(f"{TESTS_URL}{test.id}/")
    assert resp.status_code == 200
    first_choice = resp.json()["questions"][0]["choices"][0]
    assert "is_correct" not in first_choice


@pytest.mark.django_db
def test_auto_grade_and_single_attempt(world):
    client_for(world["fac"]).post(TESTS_URL, build_payload(world["batch"]), format="json")
    test = Test.objects.prefetch_related("questions__choices").get(title="Quiz 1")
    q1, q2 = list(test.questions.all())
    correct_q1 = q1.choices.get(is_correct=True)
    wrong_q2 = q2.choices.get(is_correct=False)

    sc = client_for(world["student"])
    resp = sc.post(
        f"{TESTS_URL}{test.id}/submit/",
        {
            "answers": [
                {"question": str(q1.id), "choice": str(correct_q1.id)},
                {"question": str(q2.id), "choice": str(wrong_q2.id)},
            ]
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json() == {"score": 1, "total": 2}
    assert TestAttempt.objects.filter(test=test, student=world["student"]).count() == 1

    # Second attempt rejected.
    again = sc.post(
        f"{TESTS_URL}{test.id}/submit/",
        {"answers": [{"question": str(q1.id), "choice": str(correct_q1.id)}]},
        format="json",
    )
    assert again.status_code == 400


@pytest.mark.django_db
def test_closed_test_cannot_be_submitted(world):
    test = Test.objects.create(
        batch=world["batch"],
        title="Closed",
        close_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    q = Question.objects.create(test=test, text="q")
    Choice.objects.create(question=q, text="a", is_correct=True)
    resp = client_for(world["student"]).post(
        f"{TESTS_URL}{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(q.choices.first().id)}]},
        format="json",
    )
    assert resp.status_code == 400


# ---------- Phase 5: file (Excel) + Colab test kinds, hand-graded ----------


@pytest.mark.django_db
def test_mcq_test_requires_questions(world):
    resp = client_for(world["fac"]).post(
        TESTS_URL,
        {"batch": str(world["batch"].id), "title": "Empty", "kind": "mcq", "questions": []},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_file_test_upload_then_faculty_grades(world):
    from django.core.files.uploadedfile import SimpleUploadedFile

    created = client_for(world["fac"]).post(
        TESTS_URL,
        {"batch": str(world["batch"].id), "title": "Excel task", "kind": "file", "max_score": 50},
        format="json",
    )
    assert created.status_code == 201
    test = Test.objects.get(title="Excel task")
    assert test.kind == "file"

    # Student uploads an Excel workbook; attempt lands ungraded.
    xlsx = SimpleUploadedFile(
        "answers.xlsx",
        b"PK\x03\x04 fake workbook",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    sub = client_for(world["student"]).post(
        f"{TESTS_URL}{test.id}/submit/", {"file": xlsx}, format="multipart"
    )
    assert sub.status_code == 201
    attempt = TestAttempt.objects.get(test=test, student=world["student"])
    assert attempt.graded is False and attempt.file_key

    # Faculty sees the attempt and grades it out of max_score.
    rows = client_for(world["fac"]).get(f"{TESTS_URL}{test.id}/attempts/").json()
    assert len(rows) == 1 and rows[0]["file_url"]
    graded = client_for(world["fac"]).post(
        f"/api/v1/test-attempts/{rows[0]['id']}/grade/",
        {"score": 40, "feedback": "Neat work"},
        format="json",
    )
    assert graded.status_code == 200
    attempt.refresh_from_db()
    assert attempt.graded is True and attempt.score == 40


@pytest.mark.django_db
def test_file_test_starter_sheet_is_downloadable_by_student(world):
    from django.core.files.uploadedfile import SimpleUploadedFile

    sheet = SimpleUploadedFile(
        "template.xlsx",
        b"PK\x03\x04 template",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    created = client_for(world["fac"]).post(
        TESTS_URL,
        {
            "batch": str(world["batch"].id),
            "title": "Sheet task",
            "kind": "file",
            "resource": sheet,
            "resource_url": "https://ref.example/x",
        },
        format="multipart",
    )
    assert created.status_code == 201
    test = Test.objects.get(title="Sheet task")
    assert test.resource_key and test.resource_url == "https://ref.example/x"

    # Student sees the starter-sheet download URL on the take view and can fetch the bytes.
    take = client_for(world["student"]).get(f"{TESTS_URL}{test.id}/").json()
    assert take["resource_download_url"].endswith(f"/tests/{test.id}/resource/")
    assert take["resource_url"] == "https://ref.example/x"
    dl = client_for(world["student"]).get(f"{TESTS_URL}{test.id}/resource/")
    assert dl.status_code == 200


@pytest.mark.django_db
def test_batchmate_cannot_read_another_students_attempt_file(world):
    """Owner + grading faculty may fetch a submission file; a batchmate may not."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    client_for(world["fac"]).post(
        TESTS_URL,
        {"batch": str(world["batch"].id), "title": "Sheet", "kind": "file"},
        format="json",
    )
    test = Test.objects.get(title="Sheet")
    xlsx = SimpleUploadedFile(
        "a.xlsx",
        b"PK\x03\x04 x",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    client_for(world["student"]).post(
        f"{TESTS_URL}{test.id}/submit/", {"file": xlsx}, format="multipart"
    )
    attempt = TestAttempt.objects.get(test=test, student=world["student"])
    file_url = f"/api/v1/test-attempts/{attempt.id}/file/"

    assert client_for(world["student"]).get(file_url).status_code == 200  # owner
    assert client_for(world["fac"]).get(file_url).status_code == 200  # grading faculty

    mate = user("mate", Role.STUDENT)
    Enrollment.objects.create(student=mate, batch=world["batch"], registration_number="mate")
    assert client_for(mate).get(file_url).status_code == 403  # batchmate blocked


@pytest.mark.django_db
def test_colab_test_requires_link(world):
    created = client_for(world["fac"]).post(
        TESTS_URL,
        {"batch": str(world["batch"].id), "title": "Colab", "kind": "colab"},
        format="json",
    )
    assert created.status_code == 201
    test = Test.objects.get(title="Colab")

    sc = client_for(world["student"])
    assert sc.post(f"{TESTS_URL}{test.id}/submit/", {}, format="json").status_code == 400
    ok = sc.post(
        f"{TESTS_URL}{test.id}/submit/",
        {"link": "https://colab.research.google.com/drive/abc"},
        format="json",
    )
    assert ok.status_code == 201
    attempt = TestAttempt.objects.get(test=test, student=world["student"])
    assert attempt.link.endswith("abc") and attempt.graded is False


@pytest.mark.django_db
def test_grading_someone_elses_batch_is_blocked(world):
    """A faculty from an unrelated batch cannot grade this attempt."""
    test = Test.objects.create(batch=world["batch"], title="F", kind="colab", max_score=10)
    attempt = TestAttempt.objects.create(
        test=test, student=world["student"], total=10, graded=False, link="https://x/y"
    )
    outsider = user("fac2", Role.FACULTY)
    resp = client_for(outsider).post(
        f"/api/v1/test-attempts/{attempt.id}/grade/", {"score": 5}, format="json"
    )
    assert resp.status_code == 403
