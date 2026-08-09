from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrEnum(str, Enum):
    pass


class ArtifactType(StrEnum):
    MASTER_CSV = "master_csv"
    MASTER_EXCEL = "master_excel"
    SCHEMA = "schema"
    INPUT_GUIDE = "input_guide"
    MANUAL = "manual"
    EXAMPLES = "examples"
    FAQ = "faq"
    MHLW_DOCUMENT = "mhlw_document"
    HTML = "html"
    OTHER = "other"


class NotifyPolicy(StrEnum):
    ALWAYS = "always"
    IMPORTANT_ONLY = "important_only"
    HEALTH_ONLY = "health_only"
    NEVER = "never"


class ReviewPolicy(StrEnum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    NONE = "none"


class CrawlerRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS_NO_CHANGE = "SUCCESS_NO_CHANGE"
    SUCCESS_CHANGED = "SUCCESS_CHANGED"
    FAILED = "FAILED"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    SCHEMA_BREAK = "SCHEMA_BREAK"


class MatchingStatus(StrEnum):
    MATCHED = "MATCHED"
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    AMBIGUOUS = "AMBIGUOUS"


class RawChangeType(StrEnum):
    RECORD_ADDED = "record_added"
    RECORD_REMOVED = "record_removed"
    RECORD_MODIFIED = "record_modified"
    ARTIFACT_ADDED = "artifact_added"
    ARTIFACT_REMOVED = "artifact_removed"
    ARTIFACT_CHANGED = "artifact_changed"
    DOCUMENT_CHANGED = "document_changed"
    SCHEMA_CHANGED = "schema_changed"


class EvidenceLevel(StrEnum):
    CONFIRMED = "CONFIRMED"
    CORROBORATED = "CORROBORATED"
    INFERRED = "INFERRED"
    UNRESOLVED = "UNRESOLVED"


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True)
class Source:
    id: str
    type: str
    url: str
    allowed_domains: tuple[str, ...]
    artifact_types: tuple[ArtifactType, ...]


@dataclass(frozen=True)
class Artifact:
    id: str
    source_id: str
    type: ArtifactType
    title: str
    canonical_url: str
    discovered_at: str | None = None
    last_seen_at: str | None = None
    active: bool = True
    source_group: str | None = None
    monitor_mode: str | None = None
    notify_policy: str | None = None
    review_policy: str | None = None
    freshness_sla: str | None = None


@dataclass(frozen=True)
class Snapshot:
    id: str
    artifact_id: str
    retrieved_at: str
    source_url: str
    http_status: int
    sha256: str
    content_type: str | None = None
    content_length: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    storage_key: str | None = None
    parser_status: str | None = None


@dataclass(frozen=True)
class MasterRecord:
    prefecture_code: str
    municipality_code: str
    public_funding_number: str
    program_subdivision_code: str
    program_name: str
    valid_from: str
    valid_to: str
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (
            self.prefecture_code,
            self.municipality_code,
            self.public_funding_number,
            self.program_subdivision_code,
        )


@dataclass(frozen=True)
class RawChange:
    type: RawChangeType
    identity: dict[str, str]
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    matching_status: MatchingStatus | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.CONFIRMED
    reason: str | None = None


@dataclass(frozen=True)
class ChangeBundle:
    run_id: str
    detected_at: str
    source_ids: tuple[str, ...]
    master_changes: tuple[RawChange, ...] = ()
    document_changes: tuple[RawChange, ...] = ()
    new_artifacts: tuple[Artifact, ...] = ()
    schema_changes: tuple[RawChange, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.master_changes or self.document_changes or self.new_artifacts or self.schema_changes)
