"""Management command to import geopark data from an XLSX or CSV file.

Usage:
    python manage.py import_geoparks --file /path/to/file.xlsx
    python manage.py import_geoparks --file /path/to/file.xlsx --force   # overwrites existing records
"""

import csv
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from app.models import Geopark


def _parse_coords(raw) -> tuple[float, float] | None:
    """Parse 'lat, lon' string into (lat, lon) floats."""
    if not raw:
        return None
    try:
        parts = str(raw).split(",")
        return float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, IndexError):
        return None


def _parse_date(raw) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    try:
        from datetime import datetime
        return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _safe_float(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> int | None:
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _load_xlsx(path: Path):
    try:
        import openpyxl
    except ImportError as exc:
        raise CommandError("openpyxl is required: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h else "" for h in next(rows)]
    return headers, rows


def _load_csv(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        headers = [h.strip() for h in next(reader)]
        rows = list(reader)
    return headers, iter(rows)


# Map flexible header spellings → canonical field names.
HEADER_MAP = {
    "nome": "name",
    "title": "name_en",
    "coordinates": "coords",
    "data / date": "date_added",
    "date": "date_added",
    "introdução pt": "description_pt",
    "introduction en": "description_en",
    "frase pt": "quote_pt",
    "quote en": "quote_en",
    "área / area km2": "area_km2",
    "area km2": "area_km2",
    "população / population": "population",
    "population": "population",
}


class Command(BaseCommand):
    help = "Import geopark records from an XLSX or CSV file."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the XLSX or CSV source file.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing records that match by name (case-insensitive).",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix in (".xlsx", ".xlsm", ".xls"):
            headers, rows = _load_xlsx(path)
        elif suffix == ".csv":
            headers, rows = _load_csv(path)
        else:
            raise CommandError(f"Unsupported file type: {suffix}. Use .xlsx or .csv.")

        # Normalise headers
        col_map = {}
        for idx, h in enumerate(headers):
            key = HEADER_MAP.get(h.lower())
            if key:
                col_map[key] = idx

        required = {"name", "coords"}
        missing = required - col_map.keys()
        if missing:
            raise CommandError(f"Required columns not found: {missing}. Got headers: {headers}")

        created = updated = skipped = 0
        force = options["force"]

        for row in rows:
            name = str(row[col_map["name"]]).strip() if row[col_map["name"]] else ""
            if not name:
                continue

            coords = _parse_coords(row[col_map["coords"]] if "coords" in col_map else None)
            if not coords:
                self.stderr.write(f"  Skipping '{name}': invalid coordinates.")
                skipped += 1
                continue

            lat, lon = coords

            defaults = {
                "latitude": lat,
                "longitude": lon,
                "name_en": str(row[col_map["name_en"]]).strip() if "name_en" in col_map and row[col_map["name_en"]] else "",
                "date_added": _parse_date(row[col_map["date_added"]]) if "date_added" in col_map else None,
                "description_pt": str(row[col_map["description_pt"]]).strip() if "description_pt" in col_map and row[col_map["description_pt"]] else "",
                "description_en": str(row[col_map["description_en"]]).strip() if "description_en" in col_map and row[col_map["description_en"]] else "",
                "quote_pt": str(row[col_map["quote_pt"]]).strip() if "quote_pt" in col_map and row[col_map["quote_pt"]] else "",
                "quote_en": str(row[col_map["quote_en"]]).strip() if "quote_en" in col_map and row[col_map["quote_en"]] else "",
                "area_km2": _safe_float(row[col_map["area_km2"]] if "area_km2" in col_map else None),
                "population": _safe_int(row[col_map["population"]] if "population" in col_map else None),
            }

            existing = Geopark.objects.filter(name__iexact=name).first()
            if existing:
                if force:
                    for field, value in defaults.items():
                        setattr(existing, field, value)
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                Geopark.objects.create(name=name, **defaults)
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created}  Updated: {updated}  Skipped: {skipped}"
            )
        )
