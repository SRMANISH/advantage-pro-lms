"""The single content-delivery seam for every file the app serves.

Course videos, view-only notes, task-submission files and forum attachments all go
through :func:`deliver`. It authorizes in Django (the caller does that first), then hands
the actual byte-serving to the reverse proxy: in production (``MEDIA_XACCEL_PREFIX`` set,
behind nginx) it returns an ``X-Accel-Redirect`` so the gunicorn worker is freed
immediately instead of being pinned by a slow viewer; in dev / CI (no prefix) it streams
from the app with Range support so ``<video>`` can seek. An object-storage adapter that
returns real signed URLs can slot in here the same way (redirect to the signed URL).

`disposition="inline"` (the default) serves the bytes in place and is what keeps notes
*view-only* — there is no attachment header and the frontend renders them in an embedded
viewer with no download control. `disposition="attachment"` is for genuinely
downloadable artefacts (a student's own task file).
"""

import ntpath

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import HttpResponse, StreamingHttpResponse

from core.adapters.registry import get_storage

CHUNK = 8192


def _reject_unsafe_key(storage_key: str) -> None:
    """Refuse a storage key that could escape the media root or forge a response header.

    This matters most on the path that looks safest. In dev the key goes to
    ``LocalStorageAdapter.open()``, which resolves it and refuses anything outside
    ``MEDIA_ROOT``. In **production it does not**: the key is interpolated into an
    ``X-Accel-Redirect`` header and nginx resolves it, so the adapter's containment check is
    never reached. The one deployment with a real filesystem to walk is the one without the
    guard.

    Keys are server-generated UUIDs now (``core.uploads.storage_name``), so nothing should
    ever reach here that fails these tests — that is the point of a defence-in-depth check
    rather than a reason to skip it.

    Newlines are rejected for a different reason than the rest: a key containing CR or LF
    would split the header and let a caller inject arbitrary response headers.
    """
    key = storage_key or ""
    if not key:
        raise SuspiciousFileOperation("Empty storage key.")
    if any(ch in key for ch in ("\r", "\n", "\x00")):
        raise SuspiciousFileOperation("Storage key contains a control character.")
    if key.startswith("/") or key.startswith("\\") or ntpath.splitdrive(key)[0]:
        raise SuspiciousFileOperation(f"Storage key must be relative: {key!r}")
    if "\\" in key:
        raise SuspiciousFileOperation(f"Storage key must not contain backslashes: {key!r}")
    if ".." in key.split("/"):
        raise SuspiciousFileOperation(f"Storage key escapes the media root: {key!r}")
    # Percent-encoded separators, in case a proxy or client decodes them later.
    lowered = key.lower()
    if any(token in lowered for token in ("%2f", "%5c", "%2e%2e", "%00")):
        raise SuspiciousFileOperation(f"Storage key contains an encoded separator: {key!r}")


def _disposition_header(disposition: str, filename: str | None) -> str:
    if disposition == "attachment" and filename:
        # Quote the filename so spaces/commas don't break the header.
        return f'attachment; filename="{filename}"'
    return disposition


def stream_file(
    fileobj,
    content_type: str,
    range_header: str | None,
    *,
    disposition: str = "inline",
    filename: str | None = None,
) -> StreamingHttpResponse:
    """Stream a seekable file, honouring a Range request so ``<video>`` can seek."""
    fileobj.seek(0, 2)
    size = fileobj.tell()
    fileobj.seek(0)

    start, end = 0, size - 1
    partial = False
    if range_header and range_header.startswith("bytes="):
        raw = range_header.split("=", 1)[1].split("-")
        start = int(raw[0]) if raw[0] else 0
        end = int(raw[1]) if len(raw) > 1 and raw[1] else size - 1
        end = min(end, size - 1)
        partial = True

    length = end - start + 1
    fileobj.seek(start)

    def chunks():
        remaining = length
        while remaining > 0:
            data = fileobj.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data

    resp = StreamingHttpResponse(
        chunks(), status=206 if partial else 200, content_type=content_type
    )
    resp["Accept-Ranges"] = "bytes"
    resp["Content-Length"] = str(length)
    resp["Content-Disposition"] = _disposition_header(disposition, filename)
    if partial:
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    return resp


def deliver(
    request,
    storage_key: str,
    content_type: str,
    *,
    disposition: str = "inline",
    filename: str | None = None,
):
    """Authorize in Django, then hand the actual byte-serving to the reverse proxy."""
    _reject_unsafe_key(storage_key)
    prefix = getattr(settings, "MEDIA_XACCEL_PREFIX", "")
    if prefix:
        resp = HttpResponse(content_type=content_type)
        # nginx: `location <prefix> { internal; alias /path/to/media/; }`
        resp["X-Accel-Redirect"] = f"{prefix.rstrip('/')}/{storage_key}"
        resp["X-Accel-Buffering"] = "no"
        resp["Content-Disposition"] = _disposition_header(disposition, filename)
        resp["Accept-Ranges"] = "bytes"
        return resp
    fileobj = get_storage().open(storage_key)
    return stream_file(
        fileobj,
        content_type,
        request.headers.get("Range"),
        disposition=disposition,
        filename=filename,
    )
