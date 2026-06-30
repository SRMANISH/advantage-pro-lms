"""Centralised upload validation: per-kind size caps + extension/content-type allowlists.

Defence in depth — we check both the file extension and the declared content type, and
enforce a hard byte cap (Django's FILE_UPLOAD_MAX_MEMORY_SIZE only controls disk spooling,
not a maximum). Limits are config-driven via settings so ops can tune them per deploy.
"""

from __future__ import annotations

import os

from django.conf import settings
from rest_framework import serializers

# A neutral content type many clients send for legitimate uploads — allowed alongside the
# specific types (the extension allowlist still constrains what is actually accepted).
_NEUTRAL = "application/octet-stream"

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".mkv", ".ogg"}
VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-matroska", "video/ogg"}

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".zip",
}
DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/plain",
    "text/markdown",
    "image/png",
    "image/jpeg",
    "image/gif",
    "application/zip",
}

# kind -> (allowed extensions, allowed content types, settings attr for the MB cap, default MB)
_KINDS = {
    "video": (VIDEO_EXTENSIONS, VIDEO_TYPES, "MAX_VIDEO_UPLOAD_MB", 512),
    "document": (DOCUMENT_EXTENSIONS, DOCUMENT_TYPES, "MAX_DOCUMENT_UPLOAD_MB", 25),
}


def validate_upload(upload, kind: str):
    """Validate an uploaded file by size, extension, and content type. Returns it on success."""
    exts, types, setting_name, default_mb = _KINDS[kind]
    max_mb = int(getattr(settings, setting_name, default_mb))
    max_bytes = max_mb * 1024 * 1024

    size = getattr(upload, "size", 0) or 0
    if size > max_bytes:
        raise serializers.ValidationError(f"File is too large (maximum {max_mb} MB).")

    name = getattr(upload, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext not in exts:
        raise serializers.ValidationError(
            f"Unsupported file type '{ext or name}'. Allowed: {', '.join(sorted(exts))}."
        )

    content_type = (getattr(upload, "content_type", "") or "").lower()
    if content_type and content_type != _NEUTRAL and content_type not in types:
        raise serializers.ValidationError(f"Unsupported content type '{content_type}'.")

    return upload
