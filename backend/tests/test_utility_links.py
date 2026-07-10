"""Utility-links notice board: public read, MIS-only manage."""

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from core.roles import Role
from engagement.models import UtilityLink

URL = "/api/v1/utility-links/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_public_can_read_links(db):
    UtilityLink.objects.create(title="Intro session", url="https://youtu.be/abc123def")
    resp = APIClient().get(URL)  # unauthenticated
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Intro session"


@pytest.mark.django_db
def test_mis_creates_and_deletes_links(db):
    mis = user("mis", Role.MIS)
    created = client_for(mis).post(
        URL,
        {
            "title": "React basics",
            "url": "https://www.youtube.com/watch?v=xyz789abc",
            "pinned": True,
        },
        format="json",
    )
    assert created.status_code == 201
    link_id = created.json()["id"]
    assert client_for(mis).delete(f"{URL}{link_id}/").status_code == 204


@pytest.mark.django_db
def test_only_mis_manages_links(db):
    for role in (Role.STUDENT, Role.ADMIN, Role.FACULTY, Role.SUPER_ADMIN):
        resp = client_for(user(f"u_{role}", role)).post(
            URL, {"title": "x", "url": "https://example.com"}, format="json"
        )
        assert resp.status_code == 403


@pytest.mark.django_db
def test_pinned_links_come_first(db):
    UtilityLink.objects.create(title="Old", url="https://example.com/a")
    UtilityLink.objects.create(title="Pinned", url="https://example.com/b", pinned=True)
    titles = [r["title"] for r in APIClient().get(URL).json()]
    assert titles[0] == "Pinned"


@pytest.mark.django_db
def test_mis_uploads_thumbnail_and_public_can_view_it(db):
    from django.core.files.uploadedfile import SimpleUploadedFile

    png = SimpleUploadedFile(
        "thumb.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, content_type="image/png"
    )
    created = client_for(user("mis", Role.MIS)).post(
        URL,
        {"title": "With thumb", "url": "https://example.com/x", "thumbnail": png},
        format="multipart",
    )
    assert created.status_code == 201
    thumb_url = created.json()["thumbnail_url"]
    assert thumb_url is not None

    # Public (unauthenticated) fetches the served image bytes.
    served = APIClient().get(thumb_url)
    assert served.status_code == 200
    assert served["Content-Type"].startswith("image/")


@pytest.mark.django_db
def test_non_image_thumbnail_is_rejected(db):
    from django.core.files.uploadedfile import SimpleUploadedFile

    bad = SimpleUploadedFile("notes.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    resp = client_for(user("mis", Role.MIS)).post(
        URL,
        {"title": "Bad", "url": "https://example.com/y", "thumbnail": bad},
        format="multipart",
    )
    assert resp.status_code == 400
