from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .master_diff import MasterRowChange
from .models import CrawlerRunStatus, EvidenceLevel, Severity
from .run_state import ArtifactRunChange, CrawlerRunEvaluation


@dataclass(frozen=True)
class ChangeEvidence:
    type: str
    evidence_level: EvidenceLevel
    source_url: str
    description: str
    snapshot_id: str | None = None
    field: str | None = None
    before: Any = None
    after: Any = None


@dataclass(frozen=True)
class ChangeEventCandidate:
    id: str
    jurisdiction: dict[str, str]
    program: dict[str, str]
    detected_at: str
    effective_from: str | None
    severity: Severity
    change_categories: tuple[str, ...]
    summary: str
    vendor_impacts: tuple[str, ...]
    evidence: tuple[ChangeEvidence, ...]
    source_run_status: CrawlerRunStatus
    review_required: bool = False


@dataclass(frozen=True)
class ChangeEventBundle:
    run_id: str
    source_id: str
    generated_at: str
    events: tuple[ChangeEventCandidate, ...] = ()


def _stable_id(prefix: str, value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _value(fields: dict[str, dict[str, Any]], item: str, side: str) -> str | None:
    raw = fields.get(item, {}).get(side)
    if raw in (None, ""):
        return None
    return str(raw)


def _identity_jurisdiction(identity: dict[str, str]) -> dict[str, str]:
    return {
        "prefecture_code": identity.get("prefecture_code", ""),
        "municipality_code": identity.get("municipality_code", ""),
    }


def _program(identity: dict[str, str], fields: dict[str, dict[str, Any]], side: str) -> dict[str, str]:
    return {
        "name": _value(fields, "item_1", side) or "地単公費マスター",
        "public_funding_number": identity.get("public_funding_number", ""),
        "classification": identity.get("program_subdivision_code", ""),
    }


def _field_evidence(change: MasterRowChange, source_url: str, snapshot_id: str | None) -> tuple[ChangeEvidence, ...]:
    evidence: list[ChangeEvidence] = []
    for field, delta in sorted(change.fields.items()):
        before = delta.get("before")
        after = delta.get("after")
        if before == "" and after == "":
            continue
        evidence.append(
            ChangeEvidence(
                type="master_field_diff",
                evidence_level=EvidenceLevel.CONFIRMED,
                source_url=source_url,
                snapshot_id=snapshot_id,
                field=field,
                before=before,
                after=after,
                description=f"{field} changed in positional master diff",
            )
        )
    return tuple(evidence)


def _severity_for_row_change(change: MasterRowChange) -> Severity:
    if change.type == "row_ambiguous":
        return Severity.HIGH
    if change.type in {"row_added", "row_removed"}:
        return Severity.MEDIUM
    changed_fields = set(change.fields)
    if changed_fields & {"item_10", "item_11"}:
        return Severity.HIGH
    if changed_fields & {"item_1", "item_8", "item_9"}:
        return Severity.MEDIUM
    return Severity.LOW


def _category_for_row_change(change: MasterRowChange) -> tuple[str, ...]:
    if change.type == "row_added":
        return ("master-row-added",)
    if change.type == "row_removed":
        return ("master-row-removed",)
    if change.type == "row_ambiguous":
        return ("admin-review", "ambiguous-master-row-match")
    categories = ["master-row-modified"]
    if any(field in change.fields for field in ("item_10", "item_11")):
        categories.append("validity-period")
    if "item_1" in change.fields:
        categories.append("program-name")
    return tuple(categories)


def _impacts_for(change: MasterRowChange, severity: Severity) -> tuple[str, ...]:
    impacts = ["master-import"]
    if severity in {Severity.HIGH, Severity.CRITICAL}:
        impacts.extend(["eligibility-determination", "patient-registration"])
    if change.type == "row_ambiguous":
        impacts.append("admin-review")
    return tuple(dict.fromkeys(impacts))


def event_from_master_change(run: CrawlerRunEvaluation, change: MasterRowChange, source_url: str, snapshot_id: str | None) -> ChangeEventCandidate:
    side = "after" if change.type != "row_removed" else "before"
    severity = _severity_for_row_change(change)
    categories = _category_for_row_change(change)
    evidence = _field_evidence(change, source_url, snapshot_id)
    if change.type == "row_ambiguous":
        evidence = (
            ChangeEvidence(
                type="ambiguous_master_match",
                evidence_level=EvidenceLevel.UNRESOLVED,
                source_url=source_url,
                snapshot_id=snapshot_id,
                description=change.reason or "Business identity requires Admin Review",
            ),
        )
    if not evidence:
        evidence = (
            ChangeEvidence(
                type="master_row_diff",
                evidence_level=EvidenceLevel.CONFIRMED,
                source_url=source_url,
                snapshot_id=snapshot_id,
                description=f"{change.type} detected in positional master diff",
            ),
        )
    program = _program(change.identity, change.fields, side)
    effective_from = _value(change.fields, "item_10", "after") or _value(change.fields, "item_10", side)
    summary = f"{program['name']} の地単公費マスター差分: {change.type}"
    return ChangeEventCandidate(
        id=_stable_id("chg", {"type": change.type, "identity": change.identity, "before": change.before_row_hash, "after": change.after_row_hash}),
        jurisdiction=_identity_jurisdiction(change.identity),
        program=program,
        detected_at=run.evaluated_at,
        effective_from=effective_from,
        severity=severity,
        change_categories=categories,
        summary=summary,
        vendor_impacts=_impacts_for(change, severity),
        evidence=evidence,
        source_run_status=run.status,
        review_required=change.type == "row_ambiguous",
    )


def event_from_artifact_change(run: CrawlerRunEvaluation, change: ArtifactRunChange) -> ChangeEventCandidate:
    severity = Severity.INFO if change.state == "unchanged" else Severity.LOW
    if change.state == "failed":
        severity = Severity.HIGH
    summary = f"Artifact {change.title} is {change.state}"
    return ChangeEventCandidate(
        id=_stable_id("chg", {"artifact_id": change.artifact_id, "state": change.state, "sha": change.current_sha256, "error": change.error}),
        jurisdiction={"prefecture_code": "", "municipality_code": ""},
        program={"name": change.title, "classification": change.artifact_type.value, "public_funding_number": ""},
        detected_at=run.evaluated_at,
        effective_from=None,
        severity=severity,
        change_categories=(f"artifact-{change.state}",),
        summary=summary,
        vendor_impacts=("source-monitoring",) if change.state == "failed" else ("master-import",),
        evidence=(
            ChangeEvidence(
                type="artifact_snapshot",
                evidence_level=EvidenceLevel.CONFIRMED if change.state != "failed" else EvidenceLevel.UNRESOLVED,
                source_url=change.canonical_url,
                snapshot_id=change.current_snapshot_id,
                description=change.error or f"Artifact state is {change.state}",
                before=change.previous_sha256,
                after=change.current_sha256,
            ),
        ),
        source_run_status=run.status,
        review_required=change.state == "failed",
    )


def build_change_event_bundle(run_id: str, run: CrawlerRunEvaluation) -> ChangeEventBundle:
    events: list[ChangeEventCandidate] = []
    master_snapshot_id = None
    source_url = "local://master-diff"
    if run.master_diff and run.master_diff.diff:
        source_url = run.master_diff.new_source
        for change in run.master_diff.diff.changes:
            events.append(event_from_master_change(run, change, source_url=source_url, snapshot_id=master_snapshot_id))
    else:
        for change in run.artifact_changes:
            if change.state != "unchanged":
                events.append(event_from_artifact_change(run, change))
    if run.status in {CrawlerRunStatus.FAILED, CrawlerRunStatus.PARTIAL_FAILURE, CrawlerRunStatus.SCHEMA_BREAK} and not events:
        events.extend(event_from_artifact_change(run, change) for change in run.artifact_changes if change.state == "failed")
    return ChangeEventBundle(run_id=run_id, source_id=run.source_id, generated_at=run.evaluated_at, events=tuple(events))


def flatten_events(bundles: Iterable[ChangeEventBundle]) -> tuple[ChangeEventCandidate, ...]:
    events: list[ChangeEventCandidate] = []
    for bundle in bundles:
        events.extend(bundle.events)
    return tuple(events)
