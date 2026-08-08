from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from .master_snapshot import NormalizedMasterRow
from .models import MatchingStatus


@dataclass(frozen=True)
class MasterRowChange:
    type: str
    identity: dict[str, str]
    matching_status: MatchingStatus
    before_row_number: int | None = None
    after_row_number: int | None = None
    before_row_hash: str | None = None
    after_row_hash: str | None = None
    fields: dict[str, dict[str, str | None]] = field(default_factory=dict)
    reason: str | None = None
    before_unmatched_count: int = 0
    after_unmatched_count: int = 0
    before_unmatched_hashes: tuple[str, ...] = ()
    after_unmatched_hashes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MasterDiffSummary:
    old_record_count: int
    new_record_count: int
    unchanged_row_count: int
    added_row_count: int
    removed_row_count: int
    modified_row_count: int
    ambiguous_group_count: int
    changes: tuple[MasterRowChange, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.added_row_count or self.removed_row_count or self.modified_row_count or self.ambiguous_group_count)


def _index_by_identity(rows: Iterable[NormalizedMasterRow]) -> dict[tuple[str, str, str, str], list[NormalizedMasterRow]]:
    indexed: dict[tuple[str, str, str, str], list[NormalizedMasterRow]] = defaultdict(list)
    for row in rows:
        indexed[row.business_key].append(row)
    return indexed


def _without_exact_matches(
    old_rows: list[NormalizedMasterRow],
    new_rows: list[NormalizedMasterRow],
) -> tuple[int, list[NormalizedMasterRow], list[NormalizedMasterRow]]:
    old_hash_counts = Counter(row.row_hash for row in old_rows)
    new_hash_counts = Counter(row.row_hash for row in new_rows)
    matched_by_hash = {row_hash: min(old_hash_counts[row_hash], new_hash_counts[row_hash]) for row_hash in old_hash_counts.keys() & new_hash_counts.keys()}

    def remaining(rows: list[NormalizedMasterRow]) -> list[NormalizedMasterRow]:
        allowances = {row_hash: count for row_hash, count in matched_by_hash.items()}
        result: list[NormalizedMasterRow] = []
        for row in rows:
            if allowances.get(row.row_hash, 0) > 0:
                allowances[row.row_hash] -= 1
            else:
                result.append(row)
        return result

    return sum(matched_by_hash.values()), remaining(old_rows), remaining(new_rows)


def _field_changes(old_row: NormalizedMasterRow, new_row: NormalizedMasterRow) -> dict[str, dict[str, str | None]]:
    changes: dict[str, dict[str, str | None]] = {}
    for field in sorted(set(old_row.fields) | set(new_row.fields)):
        before = old_row.fields.get(field)
        after = new_row.fields.get(field)
        if before != after:
            changes[field] = {"before": before, "after": after}
    return changes


def _added_change(row: NormalizedMasterRow) -> MasterRowChange:
    return MasterRowChange(
        type="row_added",
        identity=row.identity,
        matching_status=MatchingStatus.ADDED,
        after_row_number=row.row_number,
        after_row_hash=row.row_hash,
        fields={field: {"before": None, "after": value} for field, value in row.fields.items()},
    )


def _removed_change(row: NormalizedMasterRow) -> MasterRowChange:
    return MasterRowChange(
        type="row_removed",
        identity=row.identity,
        matching_status=MatchingStatus.REMOVED,
        before_row_number=row.row_number,
        before_row_hash=row.row_hash,
        fields={field: {"before": value, "after": None} for field, value in row.fields.items()},
    )


def _modified_change(old_row: NormalizedMasterRow, new_row: NormalizedMasterRow) -> MasterRowChange:
    return MasterRowChange(
        type="row_modified",
        identity=new_row.identity,
        matching_status=MatchingStatus.MATCHED,
        before_row_number=old_row.row_number,
        after_row_number=new_row.row_number,
        before_row_hash=old_row.row_hash,
        after_row_hash=new_row.row_hash,
        fields=_field_changes(old_row, new_row),
    )


def _ambiguous_change(identity: tuple[str, str, str, str], old_rows: list[NormalizedMasterRow], new_rows: list[NormalizedMasterRow]) -> MasterRowChange:
    sample = (new_rows or old_rows)[0]
    return MasterRowChange(
        type="row_ambiguous",
        identity=sample.identity,
        matching_status=MatchingStatus.AMBIGUOUS,
        reason="business identity has multiple unmatched old/new rows after exact hash matching; route to Admin Review",
        before_unmatched_count=len(old_rows),
        after_unmatched_count=len(new_rows),
        before_unmatched_hashes=tuple(row.row_hash for row in old_rows),
        after_unmatched_hashes=tuple(row.row_hash for row in new_rows),
    )


def diff_master_snapshots(old_rows: Iterable[NormalizedMasterRow], new_rows: Iterable[NormalizedMasterRow]) -> MasterDiffSummary:
    old_tuple = tuple(old_rows)
    new_tuple = tuple(new_rows)
    old_index = _index_by_identity(old_tuple)
    new_index = _index_by_identity(new_tuple)
    changes: list[MasterRowChange] = []
    unchanged_row_count = 0
    added_row_count = 0
    removed_row_count = 0
    modified_row_count = 0
    ambiguous_group_count = 0

    for identity in sorted(old_index.keys() | new_index.keys()):
        old_group = sorted(old_index.get(identity, []), key=lambda row: (row.row_hash, row.row_number))
        new_group = sorted(new_index.get(identity, []), key=lambda row: (row.row_hash, row.row_number))
        matched_count, old_remaining, new_remaining = _without_exact_matches(old_group, new_group)
        unchanged_row_count += matched_count

        if not old_remaining and not new_remaining:
            continue

        if not old_group:
            for row in new_remaining:
                changes.append(_added_change(row))
                added_row_count += 1
            continue

        if not new_group:
            for row in old_remaining:
                changes.append(_removed_change(row))
                removed_row_count += 1
            continue

        if not old_remaining:
            for row in new_remaining:
                changes.append(_added_change(row))
                added_row_count += 1
            continue

        if not new_remaining:
            for row in old_remaining:
                changes.append(_removed_change(row))
                removed_row_count += 1
            continue

        if len(old_remaining) == 1 and len(new_remaining) == 1:
            changes.append(_modified_change(old_remaining[0], new_remaining[0]))
            modified_row_count += 1
            continue

        changes.append(_ambiguous_change(identity, old_remaining, new_remaining))
        ambiguous_group_count += 1

    return MasterDiffSummary(
        old_record_count=len(old_tuple),
        new_record_count=len(new_tuple),
        unchanged_row_count=unchanged_row_count,
        added_row_count=added_row_count,
        removed_row_count=removed_row_count,
        modified_row_count=modified_row_count,
        ambiguous_group_count=ambiguous_group_count,
        changes=tuple(changes),
    )
