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
    """Reduce a client-supplied filename to a harmless basename.

    Upload names are attacker-controlled and are interpolated into storage keys, so a name
    like ``../../evil.pdf`` would otherwise escape MEDIA_ROOT when the key is joined to a
    path. Strips directory components (both separators, since a Windows-style ``..\\`` must
    not survive on a POSIX host either), drops any leftover dot-segments, and removes null
    bytes and control characters. Idempotent, so it is safe to apply more than once.
    """
    name = (name or "").replace("\x00", "")
    # Normalise both separators before taking the basename: os.path.basename on POSIX does
    # not treat a backslash as a separator, so do it explicitly.
    name = name.replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ch.isprintable())
    name = name.strip().strip(".")
    # Anything that reduces to nothing (or to a pure dot-segment) gets a neutral fallback.
    return name or "upload"


def validate_upload(upload, kind: str):
    """Validate an uploaded file by size, extension, and content type. Returns it on success.

    Also normalises ``upload.name`` to a safe basename so callers that build a storage key
    from it cannot be walked out of MEDIA_ROOT.
    """
    exts, types, setting_name, default_mb = _KINDS[kind]
    max_mb = int(getattr(settings, setting_name, default_mb))
    max_bytes = max_mb * 1024 * 1024

    size = getattr(upload, "size", 0) or 0
    if size > max_bytes:
        raise serializers.ValidationError(f"File is too large (maximum {max_mb} MB).")

    # Sanitise before the extension check so a traversal attempt can't smuggle a valid
    # extension past it, and so every caller that reads upload.name afterwards is safe.
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
