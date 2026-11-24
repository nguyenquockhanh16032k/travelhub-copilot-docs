"""Safe, bounded Admin-only tour import/export in CSV and XLSX.

Import is create-only and always creates drafts; it never changes existing tours,
departures, bookings or payments. Preview and commit use the same validation.
"""
import csv
import io
import re
from collections import Counter
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.models.tour import Tour
from app.schemas.catalog import TourCreate

HEADERS = ("title", "slug", "description", "duration_days", "destination")
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 500
MAX_EXPORT_ROWS = 10000


class BulkTourError(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _safe_cell(value: Any) -> str:
    """Prevent formula execution in Excel/CSV exports."""
    result = "" if value is None else str(value)
    if result.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + result
    return result


def _parse_file(raw: bytes, filename: str) -> list[dict[str, str]]:
    if not raw or len(raw) > MAX_BYTES:
        raise BulkTourError("File must be between 1 byte and 2 MiB")
    filename = filename.lower()
    try:
        if filename.endswith(".csv"):
            text = raw.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text, newline=""), strict=True)
            rows = list(reader)
        elif filename.endswith(".xlsx"):
            book = load_workbook(io.BytesIO(raw), read_only=True, data_only=False)
            try:
                if len(book.sheetnames) != 1:
                    raise BulkTourError("Use a workbook with exactly one sheet")
                rows = list(book.active.iter_rows(max_row=MAX_ROWS + 2, values_only=True))
            finally:
                book.close()
        else:
            raise BulkTourError("Only .csv and .xlsx files are supported")
    except (UnicodeError, csv.Error, ValueError, InvalidFileException, OSError, KeyError) as exc:
        raise BulkTourError("Invalid or unreadable CSV/XLSX file") from exc

    if not rows:
        raise BulkTourError("File is empty")
    header = tuple(str(c or "").strip().lower() for c in rows[0])
    if header != HEADERS:
        raise BulkTourError("Expected column order: " + ", ".join(HEADERS))
    contents = rows[1:]
    while contents and not any(value not in (None, "") for value in contents[-1]):
        contents.pop()
    if not contents:
        raise BulkTourError("The file contains no data rows")
    if len(contents) > MAX_ROWS:
        raise BulkTourError(f"Import is limited to {MAX_ROWS} data rows")
    result: list[dict[str, str]] = []
    for index, values in enumerate(contents, start=2):
        if len(values) != len(HEADERS):
            raise BulkTourError(f"Row {index} has an invalid number of columns")
        result.append({
            key: "" if value is None else str(value).strip()
            for key, value in zip(HEADERS, values)
        })
    return result


def inspect_tour_import(db: Session, raw: bytes, filename: str) -> tuple[list[TourCreate], list[dict[str, Any]]]:
    rows = _parse_file(raw, filename)
    slugs = [row["slug"] for row in rows if row["slug"]]
    existing = set(db.scalars(select(Tour.slug).where(Tour.slug.in_(slugs)))) if slugs else set()
    duplicates = {slug for slug, count in Counter(slugs).items() if count > 1}
    valid: list[TourCreate] = []
    errors: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        if row["slug"] in existing:
            row_errors.append("Slug already exists in database")
        if row["slug"] in duplicates:
            row_errors.append("Duplicate slug within uploaded file")
        try:
            payload = TourCreate.model_validate({
                **row,
                "description": row["description"] or None,
                "status": "draft",
            })
        except ValidationError as exc:
            payload = None
            row_errors.extend(
                f"{'.'.join(str(s) for s in issue['loc'])}: {issue['msg']}"
                for issue in exc.errors()
            )
        if row_errors:
            errors.append({"row": number, "slug": row["slug"], "errors": row_errors})
        elif payload is not None:
            valid.append(payload)
    return valid, errors


def import_tours(db: Session, raw: bytes, filename: str, actor_user_id: Any, preview: bool) -> dict[str, Any]:
    valid, errors = inspect_tour_import(db, raw, filename)
    result = {
        "preview": preview,
        "valid_rows": len(valid),
        "error_rows": len(errors),
        "errors": errors,
        "created": 0,
    }
    if preview or errors:
        return result
    try:
        for payload in valid:
            tour = Tour(**payload.model_dump())
            db.add(tour)
            db.flush()
            record_audit_event(
                db, actor_user_id=actor_user_id, action="tour.bulk_imported",
                resource_type="tour", resource_id=tour.id,
                details={"slug": tour.slug, "import_format": filename.rsplit(".", 1)[-1].lower()},
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BulkTourError("Import rejected: a slug already exists. No rows were imported.", 409) from exc
    except Exception:
        db.rollback()
        raise
    result["created"] = len(valid)
    return result


def export_tours(db: Session, extension: str, template: bool = False) -> tuple[bytes, str]:
    if extension not in {"csv", "xlsx"}:
        raise BulkTourError("Format must be csv or xlsx")
    if template:
        data_rows: list[tuple[Any, ...]] = []
    else:
        count = len(list(db.scalars(select(Tour.id).limit(MAX_EXPORT_ROWS + 1))))
        if count > MAX_EXPORT_ROWS:
            raise BulkTourError("Export exceeds 10000 tours. Contact an administrator.", 413)
        tours = db.scalars(select(Tour).order_by(Tour.slug.asc())).all()
        data_rows = [
            (t.title, t.slug, t.description or "", t.duration_days, t.destination)
            for t in tours
        ]
    if extension == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(HEADERS)
        for row in data_rows:
            writer.writerow([_safe_cell(value) for value in row])
        return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8"), "text/csv; charset=utf-8"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tours"
    sheet.append(list(HEADERS))
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:E{max(1, len(data_rows) + 1)}"
    for row in data_rows:
        sheet.append([_safe_cell(value) for value in row])
    for letter, width in {"A": 35, "B": 30, "C": 55, "D": 18, "E": 30}.items():
        sheet.column_dimensions[letter].width = width
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True)
    binary = io.BytesIO()
    workbook.save(binary)
    return binary.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
