from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO

from .models import MasterRecord


REQUIRED_MASTER_FIELDS = (
    "prefecture_code",
    "municipality_code",
    "public_funding_number",
    "program_subdivision_code",
    "program_name",
    "valid_from",
    "valid_to",
)


@dataclass(frozen=True)
class SchemaValidationResult:
    ok: bool
    missing_columns: tuple[str, ...] = ()
    additional_columns: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        return "OK" if self.ok else "SCHEMA_BREAK"


def validate_header(fieldnames: Iterable[str] | None, expected: Iterable[str] = REQUIRED_MASTER_FIELDS) -> SchemaValidationResult:
    actual = tuple(fieldnames or ())
    expected_tuple = tuple(expected)
    missing = tuple(field for field in expected_tuple if field not in actual)
    additional = tuple(field for field in actual if field not in expected_tuple)
    return SchemaValidationResult(ok=not missing, missing_columns=missing, additional_columns=additional)


def parse_master_csv_file(path: str | Path, encoding: str = "utf-8-sig") -> tuple[SchemaValidationResult, tuple[MasterRecord, ...]]:
    with Path(path).open("r", encoding=encoding, newline="") as fp:
        return parse_master_csv(fp)


def parse_master_csv(fp: TextIO) -> tuple[SchemaValidationResult, tuple[MasterRecord, ...]]:
    reader = csv.DictReader(fp)
    validation = validate_header(reader.fieldnames)
    if not validation.ok:
        return validation, ()

    records: list[MasterRecord] = []
    for row in reader:
        fields = {key: (value or "").strip() for key, value in row.items() if key is not None}
        records.append(
            MasterRecord(
                prefecture_code=fields["prefecture_code"],
                municipality_code=fields["municipality_code"],
                public_funding_number=fields["public_funding_number"],
                program_subdivision_code=fields["program_subdivision_code"],
                program_name=fields["program_name"],
                valid_from=fields["valid_from"],
                valid_to=fields["valid_to"],
                fields=fields,
            )
        )
    return validation, tuple(records)
