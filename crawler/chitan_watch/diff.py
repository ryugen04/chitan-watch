from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import MasterRecord, MatchingStatus, RawChange, RawChangeType


IGNORED_FIELDS = frozenset({"prefecture_code", "municipality_code", "public_funding_number", "program_subdivision_code"})


def _identity_dict(identity: tuple[str, str, str, str]) -> dict[str, str]:
    return {
        "prefecture_code": identity[0],
        "municipality_code": identity[1],
        "public_funding_number": identity[2],
        "program_subdivision_code": identity[3],
    }


def _index(records: Iterable[MasterRecord]) -> dict[tuple[str, str, str, str], list[MasterRecord]]:
    indexed: dict[tuple[str, str, str, str], list[MasterRecord]] = defaultdict(list)
    for record in records:
        indexed[record.identity].append(record)
    return indexed


def diff_master_records(old: Iterable[MasterRecord], new: Iterable[MasterRecord]) -> tuple[RawChange, ...]:
    old_index = _index(old)
    new_index = _index(new)
    changes: list[RawChange] = []

    for identity in sorted(old_index.keys() | new_index.keys()):
        old_matches = old_index.get(identity, [])
        new_matches = new_index.get(identity, [])

        if len(old_matches) > 1 or len(new_matches) > 1:
            changes.append(
                RawChange(
                    type=RawChangeType.RECORD_MODIFIED,
                    identity=_identity_dict(identity),
                    matching_status=MatchingStatus.AMBIGUOUS,
                    reason="identity matched multiple rows; route to Admin Review",
                )
            )
            continue

        if not old_matches:
            changes.append(
                RawChange(
                    type=RawChangeType.RECORD_ADDED,
                    identity=_identity_dict(identity),
                    matching_status=MatchingStatus.ADDED,
                    fields={field: {"before": None, "after": value} for field, value in new_matches[0].fields.items()},
                )
            )
            continue

        if not new_matches:
            changes.append(
                RawChange(
                    type=RawChangeType.RECORD_REMOVED,
                    identity=_identity_dict(identity),
                    matching_status=MatchingStatus.REMOVED,
                    fields={field: {"before": value, "after": None} for field, value in old_matches[0].fields.items()},
                )
            )
            continue

        old_record = old_matches[0]
        new_record = new_matches[0]
        field_changes = {}
        for field in sorted(set(old_record.fields) | set(new_record.fields)):
            if field in IGNORED_FIELDS:
                continue
            before = old_record.fields.get(field)
            after = new_record.fields.get(field)
            if before != after:
                field_changes[field] = {"before": before, "after": after}

        if field_changes:
            changes.append(
                RawChange(
                    type=RawChangeType.RECORD_MODIFIED,
                    identity=_identity_dict(identity),
                    matching_status=MatchingStatus.MATCHED,
                    fields=field_changes,
                )
            )

    return tuple(changes)
