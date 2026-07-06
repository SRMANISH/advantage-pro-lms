"""Upload validation: size, extension, declared type, and magic-byte content sniffing."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers

from core.uploads import validate_upload

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
