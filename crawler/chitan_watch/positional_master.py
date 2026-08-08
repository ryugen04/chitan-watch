from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable

from .csv_analysis import decode_csv_bytes, read_bytes

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "master" / "2026-03-30.positional.json"
ALLOWED_PRODUCTION_MAPPING_STATUSES = frozenset({"approved", "production_approved"})
IDENTITY_ITEM_NUMBERS = ("3", "4", "8", "9")


class MappingReviewRequired(RuntimeError):
    def __init__(self, mapping_status: str, blocker: str) -> None:
        super().__init__(f"mapping status {mapping_status!r} requires review: {blocker}")
        self.mapping_status = mapping_status
        self.blocker = blocker


class MasterSchemaBreak(RuntimeError):
    def __init__(self, message: str, row_number: int | None = None, expected_columns: int | None = None, actual_columns: int | None = None) -> None:
        super().__init__(message)
        self.row_number = row_number
        self.expected_columns = expected_columns
        self.actual_columns = actual_columns


@dataclass(frozen=True)
class PositionalField:
    csv_position: int
    new_item_number: str
    item_name: str
    data_type: str

    @property
    def field_key(self) -> str:
        normalized = self.new_item_number.replace("_", "_")
        return f"item_{normalized}"


@dataclass(frozen=True)
class PositionalSchema:
    version: str
    mapping_status: str
    mapping_blocker: str
    csv_column_count: int
    csv_fields: tuple[PositionalField, ...]

    @property
    def is_production_approved(self) -> bool:
        return self.mapping_status in ALLOWED_PRODUCTION_MAPPING_STATUSES


@dataclass(frozen=True)
class PositionalMasterRecord:
    row_number: int
    values_by_item: dict[str, str]
    values_by_position: dict[int, str]
    fields: dict[str, str]

    def value_for_item(self, new_item_number: str) -> str:
        return self.values_by_item.get(new_item_number, "")

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return tuple(self.value_for_item(item_number) for item_number in IDENTITY_ITEM_NUMBERS)  # type: ignore[return-value]


@dataclass(frozen=True)
class ParseSummary:
    source: str
    schema_version: str
    mapping_status: str
    record_count: int
    column_count: int
    identity_item_numbers: tuple[str, ...]
    first_identity: tuple[str, str, str, str] | None


def load_positional_schema(path: str | Path = DEFAULT_SCHEMA_PATH) -> PositionalSchema:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    csv_fields = tuple(
        PositionalField(
            csv_position=int(field["csv_position"]),
            new_item_number=str(field["new_item_number"]),
            item_name=str(field["item_name"]),
            data_type=str(field["data_type"]),
        )
        for field in raw["csv_fields"]
    )
    expected = int(raw["csv_column_count"])
    if len(csv_fields) != expected:
        raise MasterSchemaBreak(f"schema csv_fields length {len(csv_fields)} does not match csv_column_count {expected}", expected_columns=expected, actual_columns=len(csv_fields))
    return PositionalSchema(
        version=str(raw["version"]),
        mapping_status=str(raw["mapping_status"]),
        mapping_blocker=str(raw.get("mapping_blocker", "")),
        csv_column_count=expected,
        csv_fields=csv_fields,
    )


def ensure_mapping_allowed(schema: PositionalSchema, allow_candidate_mapping: bool = False) -> None:
    if schema.is_production_approved or allow_candidate_mapping:
        return
    raise MappingReviewRequired(schema.mapping_status, schema.mapping_blocker)


def parse_positional_csv_bytes(
    source: str,
    content: bytes,
    schema: PositionalSchema,
    allow_candidate_mapping: bool = False,
    max_records: int | None = None,
) -> tuple[PositionalMasterRecord, ...]:
    ensure_mapping_allowed(schema, allow_candidate_mapping=allow_candidate_mapping)
    _encoding, text = decode_csv_bytes(content)
    reader = csv.reader(StringIO(text), delimiter=",")
    records: list[PositionalMasterRecord] = []
    for row_number, row in enumerate(reader, start=1):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != schema.csv_column_count:
            raise MasterSchemaBreak(
                f"row {row_number} has {len(row)} columns; expected {schema.csv_column_count}",
                row_number=row_number,
                expected_columns=schema.csv_column_count,
                actual_columns=len(row),
            )
        values_by_item = {field.new_item_number: row[field.csv_position - 1].strip() for field in schema.csv_fields}
        values_by_position = {field.csv_position: row[field.csv_position - 1].strip() for field in schema.csv_fields}
        fields = {field.field_key: row[field.csv_position - 1].strip() for field in schema.csv_fields}
        records.append(PositionalMasterRecord(row_number=row_number, values_by_item=values_by_item, values_by_position=values_by_position, fields=fields))
        if max_records is not None and len(records) >= max_records:
            break
    return tuple(records)


def parse_positional_csv_source(
    source: str | Path,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    allow_candidate_mapping: bool = False,
    max_records: int | None = None,
) -> tuple[PositionalSchema, tuple[PositionalMasterRecord, ...]]:
    schema = load_positional_schema(schema_path)
    ensure_mapping_allowed(schema, allow_candidate_mapping=allow_candidate_mapping)
    source_str = str(source)
    records = parse_positional_csv_bytes(source_str, read_bytes(source_str), schema, allow_candidate_mapping=True, max_records=max_records)
    return schema, records


def summarize_parse(source: str, schema: PositionalSchema, records: Iterable[PositionalMasterRecord]) -> ParseSummary:
    record_tuple = tuple(records)
    return ParseSummary(
        source=source,
        schema_version=schema.version,
        mapping_status=schema.mapping_status,
        record_count=len(record_tuple),
        column_count=schema.csv_column_count,
        identity_item_numbers=IDENTITY_ITEM_NUMBERS,
        first_identity=record_tuple[0].identity if record_tuple else None,
    )
