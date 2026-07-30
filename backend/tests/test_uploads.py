"""Upload validation: size, extension, declared type, magic-byte sniffing, and the
filename sanitisation that keeps a storage key inside MEDIA_ROOT."""

import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers

from core.uploads import _reject_unsafe_name, safe_filename, storage_name, validate_upload

# Minimal but genuine file headers.
MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _f(name, data, content_type):
    return SimpleUploadedFile(name, data, content_type=content_type)


@pytest.mark.django_db
def test_genuine_video_passes():
    validate_upload(_f("lesson.mp4", MP4, "video/mp4"), "video")


@pytest.mark.django_db
def test_spoofed_video_is_rejected():
    # An executable renamed to .mp4 with a spoofed content-type must not pass.
    with pytest.raises(serializers.ValidationError):
        validate_upload(_f("evil.mp4", b"MZ\x90\x00 not a video at all", "video/mp4"), "video")


@pytest.mark.django_db
def test_genuine_documents_pass():
    validate_upload(_f("notes.pdf", PDF, "application/pdf"), "document")
    validate_upload(_f("chart.png", PNG, "image/png"), "document")


@pytest.mark.django_db
def test_spoofed_pdf_is_rejected():
    with pytest.raises(serializers.ValidationError):
        validate_upload(_f("evil.pdf", b"<html>not a pdf</html>", "application/pdf"), "document")


@pytest.mark.django_db
def test_plain_text_has_no_signature_and_passes():
    # .txt/.csv/.md have no reliable magic — extension + declared type carry them.
    validate_upload(_f("list.csv", b"reg,name\nS1,Asha\n", "text/csv"), "document")


# --------------------------- filename sanitisation ---------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("../../etc/passwd", "passwd"),
        ("../../../evil.pdf", "evil.pdf"),
        ("/absolute/path/notes.pdf", "notes.pdf"),
        (r"..\..\windows\system32\evil.pdf", "evil.pdf"),  # backslashes too
        ("nested/dir/report.xlsx", "report.xlsx"),
        ("safe.pdf", "safe.pdf"),
        ("...", "upload"),  # collapses to nothing -> neutral fallback
        ("", "upload"),
        ("with\x00null.pdf", "withnull.pdf"),
    ],
)
def test_safe_filename_reduces_to_a_harmless_basename(raw, expected):
    assert safe_filename(raw) == expected


def test_safe_filename_is_idempotent():
    once = safe_filename("../../evil.pdf")
    assert safe_filename(once) == once


@pytest.mark.parametrize(
    "hostile",
    [
        "../../../evil.pdf",  # relative traversal
        "..\\..\\windows\\evil.pdf",  # backslash traversal
        "/etc/cron.d/evil.pdf",  # absolute path
        "subdir/evil.pdf",  # any separator at all
        "%2e%2e%2fevil.pdf",  # URL-encoded ../
        "%2Fetc%2Fevil.pdf",  # URL-encoded absolute
        "..%5Cevil.pdf",  # URL-encoded backslash
        "evil\x00.pdf",  # null byte
    ],
)
def test_reject_unsafe_name_refuses_path_like_input(hostile):
    """The backstop, tested directly against raw strings.

    It has to be exercised at this level because Django's own ``UploadedFile`` basenames the
    filename on assignment (see the test below), so a hostile name never survives far enough
    to reach the validator through a normal request. This guard exists for the paths Django
    does not cover — a name arriving from somewhere other than an UploadedFile.
    """
    with pytest.raises(serializers.ValidationError):
        _reject_unsafe_name(hostile)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("../../../evil.pdf", "evil.pdf"),
        ("..\\..\\windows\\evil.pdf", "evil.pdf"),
        ("/etc/cron.d/evil.pdf", "evil.pdf"),
        ("subdir/evil.pdf", "evil.pdf"),
    ],
)
def test_django_basenames_uploads_before_validation_sees_them(raw, expected):
    """Documents the layer we were previously relying on implicitly.

    Django strips directory components when ``UploadedFile.name`` is set, so traversal via a
    normal multipart upload was already contained before any of our code ran. That is worth
    pinning: it is the reason the historical raw-``upload.name`` storage keys were not the
    exploitable hole they appeared to be, and a future Django change here would be a silent
    regression in an assumption the rest of this module is built on.
    """
    upload = _f(raw, PDF, "application/pdf")
    assert upload.name == expected
    validate_upload(upload, "document")  # passes: the name is already a bare basename
    assert "/" not in upload.name and "\\" not in upload.name


@pytest.mark.django_db
def test_storage_name_never_contains_the_client_filename():
    """Primary defence: the key's final segment is server-generated, so even a caller that
    ignores validation cannot place an attacker-chosen string into the path."""
    upload = _f("quarterly report.pdf", PDF, "application/pdf")
    validate_upload(upload, "document")
    generated = storage_name(upload)

    assert "quarterly" not in generated
    assert generated.endswith(".pdf")  # extension preserved for content sniffing/serving
    uuid.UUID(generated.removesuffix(".pdf"))  # the stem is a real UUID
    # Two uploads of the same file never collide.
    assert storage_name(upload) != generated


@pytest.mark.django_db
def test_local_storage_refuses_a_key_that_escapes_media_root(settings):
    """Defence in depth: even if a bad key reached the adapter, it must not write out."""
    import io
    import shutil
    from pathlib import Path

    from django.core.exceptions import SuspiciousFileOperation

    from core.adapters.local import LocalStorageAdapter

    # MEDIA_ROOT under BASE_DIR (the pattern test_adapters.py uses) — the pytest tmp dir is
    # not reliably writable on this Windows environment.
    media = Path(settings.BASE_DIR) / ".pytest_media_traversal"
    settings.MEDIA_ROOT = media
    try:
        storage = LocalStorageAdapter()
        escaping = "forum/abc/../../../escaped.pdf"

        # The guard lives in _path(), so it must hold for every operation that composes a
        # path — not just writes. A read or delete escaping MEDIA_ROOT is equally bad.
        with pytest.raises(SuspiciousFileOperation):
            storage.save(escaping, io.BytesIO(b"x"))
        with pytest.raises(SuspiciousFileOperation):
            storage.open(escaping)
        with pytest.raises(SuspiciousFileOperation):
            storage.delete(escaping)
        assert not (media.parent / "escaped.pdf").exists()

        # Absolute-style and backslash keys are contained too.
        for key in ("/etc/passwd", "..\\..\\escaped.pdf"):
            with pytest.raises(SuspiciousFileOperation):
                storage.save(key, io.BytesIO(b"x"))

        # A normal key still round-trips.
        storage.save("forum/abc/fine.pdf", io.BytesIO(b"ok"))
        with storage.open("forum/abc/fine.pdf") as fh:
            assert fh.read() == b"ok"
        storage.delete("forum/abc/fine.pdf")
    finally:
        shutil.rmtree(media, ignore_errors=True)
