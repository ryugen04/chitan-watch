from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from .positional_master import IDENTITY_ITEM_NUMBERS, PositionalMasterRecord


DEFAULT_IDENTITY_PROFILES: dict[str, tuple[str, ...]] = {
    "business_candidate": ("3", "4", "8", "9"),
    "with_validity": ("3", "4", "8", "9", "10", "11"),
    "with_program_name": ("3", "4", "8", "9", "1"),
    "with_program_name_and_validity": ("3", "4", "8", "9", "1", "10", "11"),
}


@dataclass(frozen=True)
class IdentityProfileResult:
    item_numbers: tuple[str, ...]
    unique_identity_count: int
    duplicate_identity_count: int
    duplicate_row_count: int
    blank_counts_by_item: dict[str, int]
    sample_duplicate_identities: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class IdentityValidationSummary:
    record_count: int
    identity_item_numbers: tuple[str, ...]
    unique_identity_count: int
    duplicate_identity_count: int
    duplicate_row_count: int
    blank_counts_by_item: dict[str, int]
    sample_duplicate_identities: tuple[tuple[str, ...], ...]
    full_row_unique_count: int
    full_row_duplicate_count: int
    profile_results: dict[str, IdentityProfileResult]

    @property
    def has_duplicates(self) -> bool:
        return self.duplicate_identity_count > 0

    @property
    def has_blank_identity_parts(self) -> bool:
        return any(count > 0 for count in self.blank_counts_by_item.values())


def _identity_for_items(record: PositionalMasterRecord, item_numbers: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(record.value_for_item(item_number) for item_number in item_numbers)


def _profile(records: tuple[PositionalMasterRecord, ...], item_numbers: tuple[str, ...], sample_limit: int) -> IdentityProfileResult:
    counter: Counter[tuple[str, ...]] = Counter(_identity_for_items(record, item_numbers) for record in records)
    duplicate_keys = tuple(identity for identity, count in counter.items() if count > 1)
    blank_counts = defaultdict(int)
    for record in records:
        for item_number in item_numbers:
            if record.value_for_item(item_number) == "":
                blank_counts[item_number] += 1
    return IdentityProfileResult(
        item_numbers=item_numbers,
        unique_identity_count=len(counter),
        duplicate_identity_count=len(duplicate_keys),
        duplicate_row_count=sum(count for count in counter.values() if count > 1),
        blank_counts_by_item={item_number: blank_counts[item_number] for item_number in item_numbers},
        sample_duplicate_identities=duplicate_keys[:sample_limit],
    )


def _full_row_identity(record: PositionalMasterRecord) -> tuple[str, ...]:
    return tuple(value for _position, value in sorted(record.values_by_position.items()))


def validate_record_identities(records: Iterable[PositionalMasterRecord], sample_limit: int = 20) -> IdentityValidationSummary:
    record_tuple = tuple(records)
    profile_results = {
        name: _profile(record_tuple, item_numbers, sample_limit)
        for name, item_numbers in DEFAULT_IDENTITY_PROFILES.items()
    }
    primary = profile_results["business_candidate"]
    full_row_counter: Counter[tuple[str, ...]] = Counter(_full_row_identity(record) for record in record_tuple)
    return IdentityValidationSummary(
        record_count=len(record_tuple),
        identity_item_numbers=IDENTITY_ITEM_NUMBERS,
        unique_identity_count=primary.unique_identity_count,
        duplicate_identity_count=primary.duplicate_identity_count,
        duplicate_row_count=primary.duplicate_row_count,
        blank_counts_by_item=primary.blank_counts_by_item,
        sample_duplicate_identities=primary.sample_duplicate_identities,
        full_row_unique_count=len(full_row_counter),
        full_row_duplicate_count=sum(1 for count in full_row_counter.values() if count > 1),
        profile_results=profile_results,
    )
