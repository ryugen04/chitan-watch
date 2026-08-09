from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from .local_store import LocalRunStore
from .models import ArtifactType
from .positional_master import DEFAULT_SCHEMA_PATH, MasterSchemaBreak, load_positional_schema, parse_positional_csv_source

MASTER_COMPARISON_SCOPE = "adjacent_observed_versions"
MASTER_DIFF_DETAIL_LIMIT = 500
MASTER_VERSION_SAMPLE_LIMIT = 25
_REIWA_DATE = re.compile(r"令和(?P<year>[0-9０-９]+)年(?P<month>[0-9０-９]+)月(?P<day>[0-9０-９]+)日(?:時点)?")
_WESTERN_DATE = re.compile(r"(?P<year>20[0-9]{2})年(?P<month>[0-9]{1,2})月(?P<day>[0-9]{1,2})日(?:時点)?")


def _stable_id(prefix: str, value: object, length: int = 16) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:length]}"


def _ascii_id(value: str) -> str:
    return quote(value, safe="A-Za-z0-9_.:-")


def detail_file_name(diff_id: str) -> str:
    return f"{_ascii_id(diff_id)}.json"


def diff_id_from_detail_file_name(file_name: str) -> str:
    return unquote(file_name.removesuffix(".json"))


def _sorted_run_ids(store: LocalRunStore) -> tuple[str, ...]:
    summaries: list[tuple[str, str]] = []
    for run_id in store.list_run_ids():
        try:
            evaluated_at = str(store.load_run_evaluation_json(run_id).get("evaluated_at", ""))
        except FileNotFoundError:
            evaluated_at = ""
        summaries.append((evaluated_at, run_id))
    return tuple(run_id for _evaluated_at, run_id in sorted(summaries, reverse=True))


def _parse_number(value: str) -> int:
    return int(value.translate(str.maketrans("０１２３４５６７８９", "0123456789")))


def basis_date_from_title(title: str) -> tuple[str | None, str | None]:
    match = _REIWA_DATE.search(title)
    if match:
        year = 2018 + _parse_number(match.group("year"))
        month = _parse_number(match.group("month"))
        day = _parse_number(match.group("day"))
        return match.group(0), f"{year:04d}-{month:02d}-{day:02d}"
    match = _WESTERN_DATE.search(title)
    if match:
        year = _parse_number(match.group("year"))
        month = _parse_number(match.group("month"))
        day = _parse_number(match.group("day"))
        return match.group(0), f"{year:04d}-{month:02d}-{day:02d}"
    return None, None


def _is_master_csv_record(record) -> bool:
    artifact = record.artifact
    if artifact.type != ArtifactType.MASTER_CSV:
        return False
    if artifact.source_layer and artifact.source_layer != "master-latest-data":
        return False
    return True


def _schema_metadata(schema_path: str | Path = DEFAULT_SCHEMA_PATH) -> tuple[dict[str, Any], dict[str, str]]:
    schema = load_positional_schema(schema_path)
    labels = {field.field_key: field.item_name for field in schema.csv_fields}
    return (
        {
            "schema_version": schema.version,
            "schema_path": Path(schema_path).name,
            "mapping_status": schema.mapping_status,
            "mapping_blocker": schema.mapping_blocker,
            "csv_column_count": schema.csv_column_count,
            "mapping_review_required": not schema.is_production_approved,
        },
        labels,
    )


def _display_fields(record, field_labels: dict[str, str]) -> dict[str, str]:
    keys = ("item_1", "item_3", "item_4", "item_8", "item_9", "item_10", "item_11")
    return {key: record.fields.get(key, "") for key in keys if key in field_labels}


def _parse_version_rows(store: LocalRunStore, run_id: str, storage_key: str | None, schema_path: str | Path, sample_limit: int) -> tuple[str, int | None, list[dict[str, Any]], str | None]:
    if not storage_key:
        return "missing_payload", None, [], "snapshot storage key is missing"
    source = store.payload_path(run_id, storage_key)
    try:
        schema, records = parse_positional_csv_source(source, schema_path=schema_path, allow_candidate_mapping=True)
    except MasterSchemaBreak as exc:
        return "schema_break", None, [], str(exc)
    except FileNotFoundError:
        return "missing_payload", None, [], "payload file is missing"
    except Exception as exc:  # projection should not break old public outputs
        return "parse_failed", None, [], str(exc)
    field_labels = {field.field_key: field.item_name for field in schema.csv_fields}
    samples = [
        {
            "row_number": record.row_number,
            "identity": {
                "prefecture_code": record.identity[0],
                "municipality_code": record.identity[1],
                "public_funding_number": record.identity[2],
                "program_subdivision_code": record.identity[3],
            },
            "display_fields": _display_fields(record, field_labels),
        }
        for record in records[:sample_limit]
    ]
    return "parsed", len(records), samples, None


def _version_record(store: LocalRunStore, run_id: str, record, schema_meta: dict[str, Any], sample_limit: int) -> dict[str, Any]:
    artifact = record.artifact
    snapshot = record.snapshot
    basis_label, basis_iso = basis_date_from_title(artifact.title)
    parser_status = "failed" if record.error else "missing_snapshot"
    row_count = None
    sample_rows: list[dict[str, Any]] = []
    parser_error = record.error
    if snapshot:
        parser_status, row_count, sample_rows, parser_error = _parse_version_rows(store, run_id, snapshot.storage_key, DEFAULT_SCHEMA_PATH, sample_limit)
    sha = snapshot.sha256 if snapshot else None
    return {
        "version_id": f"{run_id}:{artifact.id}",
        "content_version_id": f"sha256:{sha}" if sha else None,
        "run_id": run_id,
        "artifact_id": artifact.id,
        "is_primary_candidate": artifact.source_layer == "master-latest-data" and artifact.source_role == "confirmed-master-list-download",
        "title": artifact.title,
        "basis_date_label": basis_label,
        "basis_date_iso": basis_iso,
        "source_url": artifact.canonical_url,
        "retrieved_at": snapshot.retrieved_at if snapshot else None,
        "sha256": sha,
        "content_length": snapshot.content_length if snapshot else None,
        "http_status": snapshot.http_status if snapshot else None,
        "parser_status": parser_status,
        "parser_error": parser_error,
        "row_count": row_count,
        "schema_version": schema_meta["schema_version"],
        "schema_path": schema_meta["schema_path"],
        "mapping_status": schema_meta["mapping_status"],
        "mapping_review_required": schema_meta["mapping_review_required"],
        "mapping_blocker": schema_meta["mapping_blocker"],
        "storage_key_present": bool(snapshot and snapshot.storage_key),
        "sample_limit": sample_limit,
        "sample_rows": sample_rows,
    }


def build_master_versions_payload(store: LocalRunStore, sample_limit: int = MASTER_VERSION_SAMPLE_LIMIT) -> dict[str, Any]:
    schema_meta, _field_labels = _schema_metadata()
    versions: list[dict[str, Any]] = []
    for run_id in _sorted_run_ids(store):
        manifest = store.load_run_manifest(run_id)
        for record in manifest.artifacts:
            if _is_master_csv_record(record):
                versions.append(_version_record(store, run_id, record, schema_meta, sample_limit))
    observations_by_content: dict[str, int] = Counter(version["content_version_id"] for version in versions if version.get("content_version_id"))
    by_basis: dict[str, set[str]] = {}
    for version in versions:
        if version.get("basis_date_iso") and version.get("sha256"):
            by_basis.setdefault(version["basis_date_iso"], set()).add(version["sha256"])
    for version in versions:
        content_id = version.get("content_version_id")
        version["duplicate_content_observation"] = bool(content_id and observations_by_content.get(content_id, 0) > 1)
        basis = version.get("basis_date_iso")
        version["same_basis_date_different_sha_review_required"] = bool(basis and len(by_basis.get(basis, set())) > 1)
    versions.sort(key=lambda item: (item.get("basis_date_iso") or "", item.get("retrieved_at") or "", item.get("run_id") or "", item.get("artifact_id") or ""), reverse=True)
    return {
        "contract_version": 1,
        "latest_run_id": _sorted_run_ids(store)[0] if store.list_run_ids() else None,
        "comparison_scope": MASTER_COMPARISON_SCOPE,
        "arbitrary_comparison_supported": False,
        "schema": schema_meta,
        "version_count": len(versions),
        "versions": versions,
    }


def _public_summary(diff: dict[str, Any] | None) -> dict[str, int]:
    if not diff:
        return {
            "old_record_count": 0,
            "new_record_count": 0,
            "unchanged_row_count": 0,
            "added_row_count": 0,
            "removed_row_count": 0,
            "modified_row_count": 0,
            "ambiguous_group_count": 0,
        }
    return {key: int(diff.get(key, 0) or 0) for key in ("old_record_count", "new_record_count", "unchanged_row_count", "added_row_count", "removed_row_count", "modified_row_count", "ambiguous_group_count")}


def _event_ids_by_identity(bundle: dict[str, Any]) -> dict[tuple[str, str, str, str], list[str]]:
    result: dict[tuple[str, str, str, str], list[str]] = {}
    for event in bundle.get("events", []):
        program = event.get("program") or {}
        jurisdiction = event.get("jurisdiction") or {}
        key = (
            str(jurisdiction.get("prefecture_code") or ""),
            str(jurisdiction.get("municipality_code") or ""),
            str(program.get("public_funding_number") or ""),
            str(program.get("classification") or ""),
        )
        result.setdefault(key, []).append(str(event.get("id")))
    return result


def _field_diff_items(fields: dict[str, dict[str, Any]], field_labels: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "field": field,
            "label": field_labels.get(field, field),
            "before": delta.get("before"),
            "after": delta.get("after"),
        }
        for field, delta in sorted(fields.items())
    ]


def _project_row_change(change: dict[str, Any], field_labels: dict[str, str], event_ids: dict[tuple[str, str, str, str], list[str]]) -> dict[str, Any]:
    identity = change.get("identity") or {}
    key = (
        str(identity.get("prefecture_code") or ""),
        str(identity.get("municipality_code") or ""),
        str(identity.get("public_funding_number") or ""),
        str(identity.get("program_subdivision_code") or ""),
    )
    fields = change.get("fields") or {}
    return {
        "row_change_id": _stable_id("rowchg", {"type": change.get("type"), "identity": identity, "before": change.get("before_row_hash"), "after": change.get("after_row_hash")}),
        "type": change.get("type"),
        "identity": identity,
        "matching_status": change.get("matching_status"),
        "before_row_number": change.get("before_row_number"),
        "after_row_number": change.get("after_row_number"),
        "before_row_hash": change.get("before_row_hash"),
        "after_row_hash": change.get("after_row_hash"),
        "changed_field_count": len(fields),
        "changed_fields": _field_diff_items(fields, field_labels),
        "related_change_event_ids": event_ids.get(key, []),
        "review_required": change.get("type") == "row_ambiguous",
        "review_reason": change.get("reason"),
        "before_unmatched_count": change.get("before_unmatched_count", 0),
        "after_unmatched_count": change.get("after_unmatched_count", 0),
    }


def _infer_run_id_from_source(source: str) -> str | None:
    parts = Path(source).parts
    for index, part in enumerate(parts):
        if part == "runs" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def _primary_version_by_run(versions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for version in versions:
        if version.get("is_primary_candidate") or version.get("run_id") not in result:
            result[str(version["run_id"])] = version
    return result


def _top_jurisdictions(changes: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for change in changes:
        identity = change.get("identity") or {}
        counts[(str(identity.get("prefecture_code") or ""), str(identity.get("municipality_code") or ""))] += 1
    return [
        {"prefecture_code": pref, "municipality_code": muni, "count": count}
        for (pref, muni), count in counts.most_common(limit)
    ]


def _top_fields(changes: list[dict[str, Any]], field_labels: dict[str, str], limit: int = 10) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for change in changes:
        for field in change.get("fields", {}) or {}:
            counts[str(field)] += 1
    return [{"field": field, "label": field_labels.get(field, field), "count": count} for field, count in counts.most_common(limit)]


def build_master_diffs_payload(store: LocalRunStore, max_changes_per_detail: int = MASTER_DIFF_DETAIL_LIMIT) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    versions_payload = build_master_versions_payload(store)
    versions = versions_payload["versions"]
    version_by_run = _primary_version_by_run(versions)
    _schema_meta, field_labels = _schema_metadata()
    diff_summaries: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}

    for run_id in _sorted_run_ids(store):
        evaluation = store.load_run_evaluation_json(run_id)
        master_diff = evaluation.get("master_diff") or {}
        diff = master_diff.get("diff") if isinstance(master_diff, dict) else None
        if not master_diff:
            continue
        old_run_id = _infer_run_id_from_source(str(master_diff.get("old_source") or ""))
        new_version = version_by_run.get(run_id)
        old_version = version_by_run.get(old_run_id or "")
        if not new_version:
            continue
        diff_id = _stable_id("diff", {"run_id": run_id, "old": old_version.get("version_id") if old_version else old_run_id, "new": new_version.get("version_id")})
        raw_changes = list((diff or {}).get("changes", [])) if isinstance(diff, dict) else []
        bundle = store.load_run_change_events_json(run_id)
        event_ids = _event_ids_by_identity(bundle)
        projected_changes = [_project_row_change(change, field_labels, event_ids) for change in raw_changes]
        summary = _public_summary(diff if isinstance(diff, dict) else None)
        has_changes = any(summary[key] for key in ("added_row_count", "removed_row_count", "modified_row_count", "ambiguous_group_count"))
        review_required = bool(summary["ambiguous_group_count"] or master_diff.get("status") != "ok")
        base_summary = {
            "diff_id": diff_id,
            "run_id": run_id,
            "old_run_id": old_run_id,
            "new_run_id": run_id,
            "old_version_id": old_version.get("version_id") if old_version else None,
            "new_version_id": new_version.get("version_id"),
            "old_basis_date_label": old_version.get("basis_date_label") if old_version else None,
            "new_basis_date_label": new_version.get("basis_date_label"),
            "old_source_url": old_version.get("source_url") if old_version else None,
            "new_source_url": new_version.get("source_url"),
            "status": master_diff.get("status"),
            "error": master_diff.get("error"),
            "summary": summary,
            "has_changes": has_changes,
            "review_required": review_required,
            "comparison_scope": MASTER_COMPARISON_SCOPE,
            "arbitrary_comparison_supported": False,
            "top_changed_fields": _top_fields(raw_changes, field_labels),
            "top_jurisdictions": _top_jurisdictions(raw_changes),
            "detail_url": f"static/master-diffs/{detail_file_name(diff_id)}",
        }
        detail = {
            **base_summary,
            "field_labels": field_labels,
            "changes": projected_changes[:max_changes_per_detail],
            "pagination": {
                "total_change_count": len(projected_changes),
                "included_change_count": min(len(projected_changes), max_changes_per_detail),
                "limit": max_changes_per_detail,
                "truncated": len(projected_changes) > max_changes_per_detail,
            },
        }
        diff_summaries.append(base_summary)
        details[diff_id] = detail

    diff_summaries.sort(key=lambda item: (item.get("new_basis_date_label") or "", item.get("run_id") or ""), reverse=True)
    return (
        {
            "contract_version": 1,
            "latest_run_id": _sorted_run_ids(store)[0] if store.list_run_ids() else None,
            "comparison_scope": MASTER_COMPARISON_SCOPE,
            "arbitrary_comparison_supported": False,
            "diff_count": len(diff_summaries),
            "diffs": diff_summaries,
        },
        details,
    )
