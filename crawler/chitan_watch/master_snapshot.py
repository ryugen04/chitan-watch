from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .positional_master import IDENTITY_ITEM_NUMBERS, PositionalMasterRecord, PositionalSchema

ROW_FINGERPRINT_ALGORITHM = "chitan-watch-positional-row-v1"


@dataclass(frozen=True)
class BusinessIdentitySummary:
    identity: tuple[str, str, str, str]
    row_count: int


@dataclass(frozen=True)
class NormalizedMasterRow:
    row_number: int
    identity: dict[str, str]
    business_key: tuple[str, str, str, str]
    row_hash: str
    condition_fingerprint: str
    fields: dict[str, str]


@dataclass(frozen=True)
class MasterSnapshotPayload:
    source: str
    schema_version: str
    mapping_status: str
    record_count: int
    row_fingerprint_algorithm: str
    unique_row_hash_count: int
    business_identity_count: int
    duplicate_business_identity_count: int
    duplicate_business_identities: tuple[BusinessIdentitySummary, ...]
    rows: tuple[NormalizedMasterRow, ...]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _identity_dict(identity: tuple[str, str, str, str]) -> dict[str, str]:
    return {
        "prefecture_code": identity[0],
        "municipality_code": identity[1],
        "public_funding_number": identity[2],
        "program_subdivision_code": identity[3],
    }


def normalized_fields(record: PositionalMasterRecord, schema: PositionalSchema) -> dict[str, str]:
    return {field.field_key: record.value_for_item(field.new_item_number) for field in sorted(schema.csv_fields, key=lambda item: item.csv_position)}


def normalize_master_row(record: PositionalMasterRecord, schema: PositionalSchema) -> NormalizedMasterRow:
    fields = normalized_fields(record, schema)
    item_values = {field.new_item_number: record.value_for_item(field.new_item_number) for field in sorted(schema.csv_fields, key=lambda item: item.csv_position)}
    condition_values = {item_number: value for item_number, value in item_values.items() if item_number not in IDENTITY_ITEM_NUMBERS}
    row_hash = stable_sha256(
        {
            "algorithm": ROW_FINGERPRINT_ALGORITHM,
            "schema_version": schema.version,
            "items": item_values,
        }
    )
    condition_fingerprint = stable_sha256(
        {
            "algorithm": ROW_FINGERPRINT_ALGORITHM,
            "schema_version": schema.version,
            "identity_items_excluded": IDENTITY_ITEM_NUMBERS,
            "items": condition_values,
        }
    )
    return NormalizedMasterRow(
        row_number=record.row_number,
        identity=_identity_dict(record.identity),
        business_key=record.identity,
        row_hash=row_hash,
        condition_fingerprint=condition_fingerprint,
        fields=fields,
    )


def build_master_snapshot(source: str, schema: PositionalSchema, records: Iterable[PositionalMasterRecord]) -> MasterSnapshotPayload:
    rows = tuple(normalize_master_row(record, schema) for record in records)
    identity_counts = Counter(row.business_key for row in rows)
    duplicate_business_identities = tuple(
        BusinessIdentitySummary(identity=identity, row_count=count)
        for identity, count in sorted(identity_counts.items())
        if count > 1
    )
    return MasterSnapshotPayload(
        source=source,
        schema_version=schema.version,
        mapping_status=schema.mapping_status,
        record_count=len(rows),
        row_fingerprint_algorithm=ROW_FINGERPRINT_ALGORITHM,
        unique_row_hash_count=len({row.row_hash for row in rows}),
        business_identity_count=len(identity_counts),
        duplicate_business_identity_count=len(duplicate_business_identities),
        duplicate_business_identities=duplicate_business_identities,
        rows=rows,
    )
