"""Centralised upload validation: per-kind size caps + extension/content-type allowlists.

Defence in depth — we check both the file extension and the declared content type, and
enforce a hard byte cap (Django's FILE_UPLOAD_MAX_MEMORY_SIZE only controls disk spooling,
not a maximum). Limits are config-driven via settings so ops can tune them per deploy.
"""

from __future__ import annotations

import os
import uuid

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

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif"}

# kind -> (allowed extensions, allowed content types, settings attr for the MB cap, default MB)
_KINDS = {
    "video": (VIDEO_EXTENSIONS, VIDEO_TYPES, "MAX_VIDEO_UPLOAD_MB", 512),
    "document": (DOCUMENT_EXTENSIONS, DOCUMENT_TYPES, "MAX_DOCUMENT_UPLOAD_MB", 25),
    "image": (IMAGE_EXTENSIONS, IMAGE_TYPES, "MAX_IMAGE_UPLOAD_MB", 5),
}

# Magic-byte signatures per extension: (offset, expected bytes). We don't trust the
# client-declared content-type alone (spoofable), so we peek at the file's actual header.
# Extensions with no reliable signature (plain text, csv, md) are intentionally omitted and
# fall back to the extension + declared-type checks. A pure-Python check keeps us off the
# native libmagic dependency (which is painful on Windows).
_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    ".pdf": [(0, b"%PDF")],
    ".png": [(0, b"\x89PNG\r\n\x1a\n")],
    ".jpg": [(0, b"\xff\xd8\xff")],
    ".jpeg": [(0, b"\xff\xd8\xff")],
    ".gif": [(0, b"GIF87a"), (0, b"GIF89a")],
    ".zip": [(0, b"PK\x03\x04"), (0, b"PK\x05\x06")],
    # OOXML office files are ZIP containers.
    ".docx": [(0, b"PK\x03\x04")],
    ".pptx": [(0, b"PK\x03\x04")],
    ".xlsx": [(0, b"PK\x03\x04")],
    # Legacy OLE2 office files.
    ".doc": [(0, b"\xd0\xcf\x11\xe0")],
    ".ppt": [(0, b"\xd0\xcf\x11\xe0")],
    ".xls": [(0, b"\xd0\xcf\x11\xe0")],
    # ISO-BMFF (MP4 family): a box type at offset 4.
    ".mp4": [(4, b"ftyp")],
    ".m4v": [(4, b"ftyp")],
    ".mov": [(4, b"ftyp"), (4, b"moov"), (4, b"mdat"), (4, b"free"), (4, b"wide"), (4, b"skip")],
    # Matroska / WebM (EBML) and Ogg.
    ".mkv": [(0, b"\x1a\x45\xdf\xa3")],
    ".webm": [(0, b"\x1a\x45\xdf\xa3")],
    ".ogg": [(0, b"OggS")],
}


def _content_matches_extension(upload, ext: str) -> bool:
    """True if the file's leading bytes match a known signature for ``ext`` (or none is known)."""
    signatures = _SIGNATURES.get(ext)
    if not signatures:
        return True
    try:
        head = upload.read(32)
    finally:
        try:
            upload.seek(0)
        except (AttributeError, OSError):
            pass
    if not head:
        return False
    return any(head[offset : offset + len(sig)] == sig for offset, sig in signatures)


def safe_filename(name: str) -> str:
    """Reduce a client-supplied filename to a harmless basename, for **display only**.

    Storage keys no longer contain the client's filename at all (see ``storage_name``), so
    this exists for the places that show or re-serve the original name — e.g.
    ``ThreadAttachment.filename`` and the Content-Disposition of a downloadable resource.
    Strips directory components (both separators, since a Windows-style ``..\\`` must not
    survive on a POSIX host either), leftover dot-segments, null bytes and control
    characters. Idempotent.
    """
    name = (name or "").replace("\x00", "")
    # Normalise both separators before taking the basename: os.path.basename on POSIX does
    # not treat a backslash as a separator, so do it explicitly.
    name = name.replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ch.isprintable())
    name = name.strip().strip(".")
    # Anything that reduces to nothing (or to a pure dot-segment) gets a neutral fallback.
    return name or "upload"


def storage_name(upload) -> str:
    """The final path segment for a storage key: a server-generated UUID plus the validated
    extension — never the client's filename.

    This is the primary defence against path traversal. Sanitising an attacker-controlled
    name is a backstop that has to be right every time; not using the name at all cannot be
    walked out of MEDIA_ROOT by construction. Call **after** ``validate_upload``, which is
    what constrains the extension to the per-kind allowlist.
    """
    ext = os.path.splitext(safe_filename(getattr(upload, "name", "")))[1].lower()
    return f"{uuid.uuid4()}{ext}"


def _reject_unsafe_name(name: str) -> None:
    """Refuse a filename that is trying to be a path.

    A legitimate upload never contains a separator or a dot-segment, so rather than quietly
    rewriting one we reject it — a caller that ignores ``storage_name`` and interpolates the
    raw name still cannot escape, and the attempt is visible instead of silently normalised.
    """
    raw = name or ""
    lowered = raw.lower()
    if "\x00" in raw:
        raise serializers.ValidationError("File name contains a null byte.")
    # Decoded separators, plus the percent-encodings a proxy or client might not have decoded.
    for token in ("/", "\\", "..", "%2f", "%5c", "%2e%2e", "%00"):
        if token in lowered:
            raise serializers.ValidationError(
                "File name must not contain path separators or parent-directory segments."
            )


def validate_upload(upload, kind: str):
    """Validate an uploaded file by size, extension, and content type. Returns it on success.

    Rejects filenames that look like paths (separators, ``..``, null bytes, or their
    percent-encodings). Note this is a backstop only: storage keys are built from
    ``storage_name`` and never contain the client's filename.
    """
    exts, types, setting_name, default_mb = _KINDS[kind]
    max_mb = int(getattr(settings, setting_name, default_mb))
    max_bytes = max_mb * 1024 * 1024

    size = getattr(upload, "size", 0) or 0
    if size > max_bytes:
        raise serializers.ValidationError(f"File is too large (maximum {max_mb} MB).")

    # Reject path-like names outright, then normalise what remains so anything that reads
    # upload.name afterwards (display fields, Content-Disposition) is safe.
    _reject_unsafe_name(getattr(upload, "name", ""))
    name = safe_filename(getattr(upload, "name", ""))
    try:
        upload.name = name
    except AttributeError:  # pragma: no cover - some file-likes expose a read-only name
        pass
    ext = os.path.splitext(name)[1].lower()
    if ext not in exts:
        raise serializers.ValidationError(
            f"Unsupported file type '{ext or name}'. Allowed: {', '.join(sorted(exts))}."
        )

    content_type = (getattr(upload, "content_type", "") or "").lower()
    if content_type and content_type != _NEUTRAL and content_type not in types:
        raise serializers.ValidationError(f"Unsupported content type '{content_type}'.")

    if not _content_matches_extension(upload, ext):
        raise serializers.ValidationError(
            "The file's contents do not match its extension. Please upload a genuine "
            f"'{ext}' file."
        )

    return upload
