"""Upload validation: size, extension, declared type, magic-byte sniffing, and the
filename sanitisation that keeps a storage key inside MEDIA_ROOT."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers

from core.uploads import safe_filename, validate_upload

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


@pytest.mark.django_db
def test_validate_upload_strips_traversal_from_the_stored_name():
    """The key attack: a valid extension smuggled in behind ../ must not survive, because
    call sites interpolate upload.name straight into a storage key."""
    upload = _f("../../../evil.pdf", PDF, "application/pdf")
    validate_upload(upload, "document")

    assert upload.name == "evil.pdf"
    assert ".." not in upload.name and "/" not in upload.name


@pytest.mark.django_db
def test_traversal_name_without_a_valid_extension_is_still_rejected():
    with pytest.raises(serializers.ValidationError):
        validate_upload(_f("../../etc/passwd", PDF, "application/pdf"), "document")


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

        with pytest.raises(SuspiciousFileOperation):
            storage.save("forum/abc/../../../escaped.pdf", io.BytesIO(b"x"))
        assert not (media.parent / "escaped.pdf").exists()

        # A normal key still round-trips.
        storage.save("forum/abc/fine.pdf", io.BytesIO(b"ok"))
        with storage.open("forum/abc/fine.pdf") as fh:
            assert fh.read() == b"ok"
    finally:
        shutil.rmtree(media, ignore_errors=True)
