"""Student-list import: parse a CSV/XLSX, validate every row, all-or-nothing.

If a single row is invalid the whole upload is rejected with a row-by-row error
report and nothing is written. A clean list imports inside one atomic transaction.
"""

from __future__ import annotations

import csv
import io
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction

from accounts.models import User, UserStatus
from batches.models import Batch
from core.roles import Role

from .models import Enrollment

REQUIRED = ["registration_number", "name", "email", "phone", "batch", "course", "faculty"]
OPTIONAL = ["address", "guardian", "employment_company"]

_PHONE_RE = re.compile(r"^\+?\d[\d\s-]{6,18}$")

# "Registration ID" is the student recognition term. Accept friendly spellings for that
# column (and tolerate case/spacing on every column) so admins can use "Registration ID"
# in the sheet while we still store it as the canonical ``registration_number``.
_HEADER_ALIASES = {
    "registration_id": "registration_number",
    "registration_no": "registration_number",
    "registration_number": "registration_number",
    "reg_id": "registration_number",
    "reg_no": "registration_number",
}


def _canonical_header(key: str) -> str:
    norm = re.sub(r"\s+", "_", (key or "").strip().lower())
    return _HEADER_ALIASES.get(norm, norm)


def parse_rows(uploaded) -> list[dict]:
    """Return a list of dict rows from a CSV or XLSX upload. Raises ValueError on bad files."""
    name = (uploaded.name or "").lower()
    raw = uploaded.read()
    if name.endswith(".xlsx"):
        return _parse_xlsx(raw)
    if name.endswith(".csv") or not name:
        return _parse_csv(raw)
    raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")


def _parse_csv(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("The file is empty.")
    return [{_canonical_header(k): (v or "").strip() for k, v in row.items()} for row in reader]


def _parse_xlsx(raw: bytes) -> list[dict]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = [_canonical_header(str(h)) if h is not None else "" for h in next(rows)]
    except StopIteration as exc:
        raise ValueError("The file is empty.") from exc
    out = []
    for values in rows:
        if values is None or all(v is None for v in values):
            continue
        cells = ["" if v is None else str(v).strip() for v in values]
        out.append(dict(zip(header, cells, strict=False)))
    return out


def validate_and_build(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (errors, prepared). Errors is a row-by-row list; prepared is build specs."""
    errors: list[dict] = []
    if not rows:
        return [{"row": 0, "field": "file", "message": "No data rows found."}], []

    missing_cols = [c for c in REQUIRED if c not in rows[0]]
    if missing_cols:
        return [
            {"row": 1, "field": ", ".join(missing_cols), "message": "Missing required column(s)."}
        ], []

    existing_regs = set(
        User.objects.filter(
            username__in=[r.get("registration_number", "") for r in rows]
        ).values_list("username", flat=True)
    )
    batches = {b.code: b for b in Batch.objects.select_related("course").all()}
    faculty = {u.username: u for u in User.objects.filter(role=Role.FACULTY)}

    seen_regs: set[str] = set()
    prepared: list[dict] = []

    for index, row in enumerate(rows, start=2):  # row 1 is the header

        def err(field, message, _row=index):
            errors.append({"row": _row, "field": field, "message": message})

        reg = row.get("registration_number", "").strip()
        name = row.get("name", "").strip()
        email = row.get("email", "").strip()
        phone = row.get("phone", "").strip()
        batch_code = row.get("batch", "").strip()
        course_code = row.get("course", "").strip()
        faculty_name = row.get("faculty", "").strip()

        for field in REQUIRED:
            if not row.get(field, "").strip():
                err(field, "This field is required.")

        if reg:
            if reg in existing_regs:
                err("registration_number", "A student with this Registration ID already exists.")
            if reg in seen_regs:
                err("registration_number", "Duplicate Registration ID within the file.")
            seen_regs.add(reg)

        if email:
            try:
                validate_email(email)
            except DjangoValidationError:
                err("email", "Invalid email address.")

        if phone and not _PHONE_RE.match(phone):
            err("phone", "Invalid phone number.")

        batch = batches.get(batch_code)
        if batch_code and batch is None:
            err("batch", f"Unknown batch '{batch_code}'.")
        if batch and course_code and batch.course.code != course_code:
            err("course", f"Course '{course_code}' does not match batch's course.")

        fac = faculty.get(faculty_name)
        if faculty_name and fac is None:
            err("faculty", f"Unknown faculty '{faculty_name}'.")

        prepared.append(
            {
                "registration_number": reg,
                "name": name,
                "email": email,
                "phone": phone,
                "batch": batch,
                "address": row.get("address", "").strip(),
                "guardian": row.get("guardian", "").strip(),
                "employment_company": row.get("employment_company", "").strip(),
            }
        )

    if errors:
        return errors, []
    return [], prepared


@transaction.atomic
def do_import(prepared: list[dict]) -> list[User]:
    """Create student accounts + enrolments atomically. Students start as 'pending'."""
    created: list[User] = []
    for spec in prepared:
        student = User.objects.create_user(
            username=spec["registration_number"],
            password=None,  # set during two-step account setup
            role=Role.STUDENT,
            status=UserStatus.PENDING,
            full_name=spec["name"],
            email=spec["email"],
            phone=spec["phone"],
        )
        Enrollment.objects.create(
            student=student,
            batch=spec["batch"],
            registration_number=spec["registration_number"],
            address=spec["address"],
            guardian=spec["guardian"],
            employment_company=spec["employment_company"],
        )
        created.append(student)
    return created
