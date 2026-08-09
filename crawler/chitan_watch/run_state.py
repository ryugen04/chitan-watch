from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .csv_analysis import read_bytes
from .master_diff import MasterDiffSummary, diff_master_snapshots
from .master_snapshot import build_master_snapshot
from .models import Artifact, ArtifactType, CrawlerRunStatus, Snapshot
from .positional_master import DEFAULT_SCHEMA_PATH, MasterSchemaBreak, parse_positional_csv_source
from .snapshot import build_snapshot

MANIFEST_VERSION = 1


@dataclass(frozen=True)
class ArtifactSourceSpec:
    id: str
    type: ArtifactType
    title: str
    canonical_url: str
    path: str | None = None
    error: str | None = None
    source_group: str | None = None
    source_layer: str | None = None
    source_owner: str | None = None
    source_role: str | None = None
    jurisdiction_scope: str | None = None
    monitor_mode: str | None = None
    notify_policy: str | None = None
    review_policy: str | None = None
    evidence_level: str | None = None
    freshness_sla: str | None = None


@dataclass(frozen=True)
class ArtifactSnapshotRecord:
    artifact: Artifact
    snapshot: Snapshot | None = None
    error: str | None = None


@dataclass(frozen=True)
class SnapshotManifest:
    manifest_version: int
    source_id: str
    generated_at: str
    artifacts: tuple[ArtifactSnapshotRecord, ...]


@dataclass(frozen=True)
class ArtifactRunChange:
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    canonical_url: str
    state: str
    previous_sha256: str | None = None
    current_sha256: str | None = None
    previous_snapshot_id: str | None = None
    current_snapshot_id: str | None = None
    error: str | None = None
    source_group: str | None = None
    source_layer: str | None = None
    source_owner: str | None = None
    source_role: str | None = None
    jurisdiction_scope: str | None = None
    monitor_mode: str | None = None
    notify_policy: str | None = None
    review_policy: str | None = None
    freshness_sla: str | None = None


@dataclass(frozen=True)
class MasterDiffAttachment:
    old_source: str
    new_source: str
    status: str
    diff: MasterDiffSummary | None = None
    error: str | None = None


@dataclass(frozen=True)
class CrawlerRunEvaluation:
    status: CrawlerRunStatus
    source_id: str
    evaluated_at: str
    artifact_count: int
    changed_artifact_count: int
    failed_artifact_count: int
    schema_break_count: int
    master_diff: MasterDiffAttachment | None = None
    artifact_changes: tuple[ArtifactRunChange, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        if any(change.state in {"added", "removed", "changed"} for change in self.artifact_changes):
            return True
        return bool(self.master_diff and self.master_diff.diff and self.master_diff.diff.has_changes)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def artifact_from_spec(spec: ArtifactSourceSpec, source_id: str) -> Artifact:
    return Artifact(
        id=spec.id,
        source_id=source_id,
        type=spec.type,
        title=spec.title,
        canonical_url=spec.canonical_url,
        source_group=spec.source_group,
        source_layer=spec.source_layer,
        source_owner=spec.source_owner,
        source_role=spec.source_role,
        jurisdiction_scope=spec.jurisdiction_scope,
        monitor_mode=spec.monitor_mode,
        notify_policy=spec.notify_policy,
        review_policy=spec.review_policy,
        freshness_sla=spec.freshness_sla,
    )


def build_manifest_from_specs(
    source_id: str,
    specs: Iterable[ArtifactSourceSpec],
    generated_at: str | None = None,
) -> SnapshotManifest:
    records: list[ArtifactSnapshotRecord] = []
    for spec in specs:
        artifact = artifact_from_spec(spec, source_id)
        if spec.error:
            records.append(ArtifactSnapshotRecord(artifact=artifact, error=spec.error))
            continue
        if not spec.path:
            records.append(ArtifactSnapshotRecord(artifact=artifact, error="missing local path for snapshot source"))
            continue
        content = read_bytes(spec.path)
        snapshot = build_snapshot(
            artifact_id=artifact.id,
            source_url=artifact.canonical_url,
            http_status=200,
            headers={"Content-Length": str(len(content))},
            content=content,
            retrieved_at=generated_at,
        )
        records.append(ArtifactSnapshotRecord(artifact=artifact, snapshot=snapshot))
    return SnapshotManifest(
        manifest_version=MANIFEST_VERSION,
        source_id=source_id,
        generated_at=generated_at or _now(),
        artifacts=tuple(records),
    )


def _artifact_record_from_dict(raw: dict[str, Any]) -> ArtifactSnapshotRecord:
    artifact_raw = raw["artifact"]
    artifact = Artifact(
        id=str(artifact_raw["id"]),
        source_id=str(artifact_raw["source_id"]),
        type=ArtifactType(str(artifact_raw["type"])),
        title=str(artifact_raw["title"]),
        canonical_url=str(artifact_raw["canonical_url"]),
        discovered_at=artifact_raw.get("discovered_at"),
        last_seen_at=artifact_raw.get("last_seen_at"),
        active=bool(artifact_raw.get("active", True)),
        source_group=artifact_raw.get("source_group"),
        source_layer=artifact_raw.get("source_layer"),
        source_owner=artifact_raw.get("source_owner"),
        source_role=artifact_raw.get("source_role"),
        jurisdiction_scope=artifact_raw.get("jurisdiction_scope"),
        monitor_mode=artifact_raw.get("monitor_mode"),
        notify_policy=artifact_raw.get("notify_policy"),
        review_policy=artifact_raw.get("review_policy"),
        freshness_sla=artifact_raw.get("freshness_sla"),
    )
    snapshot_raw = raw.get("snapshot")
    snapshot = None
    if snapshot_raw:
        snapshot = Snapshot(
            id=str(snapshot_raw["id"]),
            artifact_id=str(snapshot_raw["artifact_id"]),
            retrieved_at=str(snapshot_raw["retrieved_at"]),
            source_url=str(snapshot_raw["source_url"]),
            http_status=int(snapshot_raw["http_status"]),
            sha256=str(snapshot_raw["sha256"]),
            content_type=snapshot_raw.get("content_type"),
            content_length=snapshot_raw.get("content_length"),
            etag=snapshot_raw.get("etag"),
            last_modified=snapshot_raw.get("last_modified"),
            storage_key=snapshot_raw.get("storage_key"),
            parser_status=snapshot_raw.get("parser_status"),
        )
    return ArtifactSnapshotRecord(artifact=artifact, snapshot=snapshot, error=raw.get("error"))


def manifest_from_dict(raw: dict[str, Any]) -> SnapshotManifest:
    return SnapshotManifest(
        manifest_version=int(raw.get("manifest_version", MANIFEST_VERSION)),
        source_id=str(raw["source_id"]),
        generated_at=str(raw["generated_at"]),
        artifacts=tuple(_artifact_record_from_dict(item) for item in raw.get("artifacts", ())),
    )


def load_manifest(path: str | Path) -> SnapshotManifest:
    return manifest_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def specs_from_dict(raw: dict[str, Any]) -> tuple[ArtifactSourceSpec, ...]:
    return tuple(
        ArtifactSourceSpec(
            id=str(item["id"]),
            type=ArtifactType(str(item["type"])),
            title=str(item.get("title") or item["canonical_url"]),
            canonical_url=str(item["canonical_url"]),
            path=item.get("path"),
            error=item.get("error"),
            source_group=item.get("source_group"),
            source_layer=item.get("source_layer"),
            source_owner=item.get("source_owner"),
            source_role=item.get("source_role"),
            jurisdiction_scope=item.get("jurisdiction_scope"),
            monitor_mode=item.get("monitor_mode"),
            notify_policy=item.get("notify_policy"),
            review_policy=item.get("review_policy"),
            evidence_level=item.get("evidence_level"),
            freshness_sla=item.get("freshness_sla"),
        )
        for item in raw.get("artifacts", ())
    )


def load_specs(path: str | Path) -> tuple[ArtifactSourceSpec, ...]:
    return specs_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def compare_artifact_manifests(previous: SnapshotManifest | None, current: SnapshotManifest) -> tuple[ArtifactRunChange, ...]:
    previous_by_id = {record.artifact.id: record for record in previous.artifacts} if previous else {}
    current_by_id = {record.artifact.id: record for record in current.artifacts}
    changes: list[ArtifactRunChange] = []

    for artifact_id in sorted(previous_by_id.keys() | current_by_id.keys()):
        old = previous_by_id.get(artifact_id)
        new = current_by_id.get(artifact_id)
        record = new or old
        if record is None:
            continue
        artifact = record.artifact
        if old is not None and new is None:
            changes.append(
                ArtifactRunChange(
                    artifact_id=artifact_id,
                    artifact_type=artifact.type,
                    title=artifact.title,
                    canonical_url=artifact.canonical_url,
                    state="removed",
                    previous_sha256=old.snapshot.sha256 if old.snapshot else None,
                    previous_snapshot_id=old.snapshot.id if old.snapshot else None,
                    error=old.error,
                    source_group=artifact.source_group,
                    source_layer=artifact.source_layer,
                    source_owner=artifact.source_owner,
                    source_role=artifact.source_role,
                    jurisdiction_scope=artifact.jurisdiction_scope,
                    monitor_mode=artifact.monitor_mode,
                    notify_policy=artifact.notify_policy,
                    review_policy=artifact.review_policy,
                    freshness_sla=artifact.freshness_sla,
                )
            )
            continue
        if new is not None and new.error:
            changes.append(
                ArtifactRunChange(
                    artifact_id=artifact_id,
                    artifact_type=artifact.type,
                    title=artifact.title,
                    canonical_url=artifact.canonical_url,
                    state="failed",
                    previous_sha256=old.snapshot.sha256 if old and old.snapshot else None,
                    previous_snapshot_id=old.snapshot.id if old and old.snapshot else None,
                    error=new.error,
                    source_group=artifact.source_group,
                    source_layer=artifact.source_layer,
                    source_owner=artifact.source_owner,
                    source_role=artifact.source_role,
                    jurisdiction_scope=artifact.jurisdiction_scope,
                    monitor_mode=artifact.monitor_mode,
                    notify_policy=artifact.notify_policy,
                    review_policy=artifact.review_policy,
                    freshness_sla=artifact.freshness_sla,
                )
            )
            continue
        if old is None and new is not None:
            changes.append(
                ArtifactRunChange(
                    artifact_id=artifact_id,
                    artifact_type=artifact.type,
                    title=artifact.title,
                    canonical_url=artifact.canonical_url,
                    state="added",
                    current_sha256=new.snapshot.sha256 if new.snapshot else None,
                    current_snapshot_id=new.snapshot.id if new.snapshot else None,
                    source_group=artifact.source_group,
                    source_layer=artifact.source_layer,
                    source_owner=artifact.source_owner,
                    source_role=artifact.source_role,
                    jurisdiction_scope=artifact.jurisdiction_scope,
                    monitor_mode=artifact.monitor_mode,
                    notify_policy=artifact.notify_policy,
                    review_policy=artifact.review_policy,
                    freshness_sla=artifact.freshness_sla,
                )
            )
            continue
        if old is None or new is None:
            continue
        old_sha = old.snapshot.sha256 if old.snapshot else None
        new_sha = new.snapshot.sha256 if new.snapshot else None
        state = "unchanged" if old_sha and new_sha and old_sha == new_sha else "changed"
        changes.append(
            ArtifactRunChange(
                artifact_id=artifact_id,
                artifact_type=artifact.type,
                title=artifact.title,
                canonical_url=artifact.canonical_url,
                state=state,
                previous_sha256=old_sha,
                current_sha256=new_sha,
                previous_snapshot_id=old.snapshot.id if old.snapshot else None,
                current_snapshot_id=new.snapshot.id if new.snapshot else None,
                source_group=artifact.source_group,
                source_layer=artifact.source_layer,
                source_owner=artifact.source_owner,
                source_role=artifact.source_role,
                jurisdiction_scope=artifact.jurisdiction_scope,
                monitor_mode=artifact.monitor_mode,
                notify_policy=artifact.notify_policy,
                review_policy=artifact.review_policy,
                freshness_sla=artifact.freshness_sla,
            )
        )
    return tuple(changes)


def build_master_diff_attachment(
    old_source: str,
    new_source: str,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    allow_candidate_mapping: bool = False,
) -> MasterDiffAttachment:
    try:
        old_schema, old_records = parse_positional_csv_source(old_source, schema_path=schema_path, allow_candidate_mapping=allow_candidate_mapping)
        new_schema, new_records = parse_positional_csv_source(new_source, schema_path=schema_path, allow_candidate_mapping=allow_candidate_mapping)
        old_snapshot = build_master_snapshot(old_source, old_schema, old_records)
        new_snapshot = build_master_snapshot(new_source, new_schema, new_records)
        diff = diff_master_snapshots(old_snapshot.rows, new_snapshot.rows)
        return MasterDiffAttachment(old_source=old_source, new_source=new_source, status="ok", diff=diff)
    except MasterSchemaBreak as exc:
        return MasterDiffAttachment(old_source=old_source, new_source=new_source, status="schema_break", error=str(exc))
    except Exception as exc:
        return MasterDiffAttachment(old_source=old_source, new_source=new_source, status="failed", error=str(exc))


def evaluate_run(
    current: SnapshotManifest,
    previous: SnapshotManifest | None = None,
    master_diff: MasterDiffAttachment | None = None,
    evaluated_at: str | None = None,
) -> CrawlerRunEvaluation:
    artifact_changes = compare_artifact_manifests(previous, current)
    failed_count = sum(1 for change in artifact_changes if change.state == "failed")
    changed_count = sum(1 for change in artifact_changes if change.state in {"added", "removed", "changed"})
    schema_break_count = 1 if master_diff and master_diff.status == "schema_break" else 0
    errors = tuple(change.error for change in artifact_changes if change.error) + ((master_diff.error,) if master_diff and master_diff.error else ())

    if schema_break_count:
        status = CrawlerRunStatus.SCHEMA_BREAK
    elif failed_count and failed_count == len(current.artifacts):
        status = CrawlerRunStatus.FAILED
    elif failed_count:
        status = CrawlerRunStatus.PARTIAL_FAILURE
    elif changed_count or (master_diff and master_diff.diff and master_diff.diff.has_changes):
        status = CrawlerRunStatus.SUCCESS_CHANGED
    else:
        status = CrawlerRunStatus.SUCCESS_NO_CHANGE

    return CrawlerRunEvaluation(
        status=status,
        source_id=current.source_id,
        evaluated_at=evaluated_at or _now(),
        artifact_count=len(current.artifacts),
        changed_artifact_count=changed_count,
        failed_artifact_count=failed_count,
        schema_break_count=schema_break_count,
        master_diff=master_diff,
        artifact_changes=artifact_changes,
        errors=errors,
    )
