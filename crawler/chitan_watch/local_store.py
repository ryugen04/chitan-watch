from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

from .csv_analysis import read_bytes
from .models import ArtifactType, Snapshot
from .positional_master import DEFAULT_SCHEMA_PATH
from .run_state import (
    ArtifactSnapshotRecord,
    ArtifactSourceSpec,
    CrawlerRunEvaluation,
    MasterDiffAttachment,
    SnapshotManifest,
    build_manifest_from_specs,
    build_master_diff_attachment,
    evaluate_run,
    load_manifest,
)

DEFAULT_STORE_DIR = Path("storage") / "chitan-watch"
RUN_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class LocalRunResult:
    run_id: str
    source_id: str
    run_dir: str
    previous_run_id: str | None
    manifest_path: str
    evaluation_path: str
    source_spec_path: str
    master_diff_path: str | None
    payload_paths: tuple[str, ...]
    evaluation: CrawlerRunEvaluation


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")


def sanitize_path_part(value: str) -> str:
    sanitized = RUN_ID_PATTERN.sub("_", value.strip())
    return sanitized.strip("._") or "item"


def to_jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_jsonable(item) for item in value]
    return value


def write_json(path: str | Path, value) -> None:
    Path(path).write_text(json.dumps(to_jsonable(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class LocalRunStore:
    def __init__(self, root: str | Path = DEFAULT_STORE_DIR) -> None:
        self.root = Path(root)

    def runs_dir(self) -> Path:
        return self.root / "runs"

    def sources_dir(self) -> Path:
        return self.root / "sources"

    def run_dir(self, run_id: str) -> Path:
        return self.runs_dir() / sanitize_path_part(run_id)

    def latest_pointer_path(self, source_id: str) -> Path:
        return self.sources_dir() / sanitize_path_part(source_id) / "latest.txt"

    def latest_run_id(self, source_id: str) -> str | None:
        pointer = self.latest_pointer_path(source_id)
        if not pointer.exists():
            return None
        value = pointer.read_text(encoding="utf-8").strip()
        return value or None

    def load_run_manifest(self, run_id: str) -> SnapshotManifest:
        return load_manifest(self.run_dir(run_id) / "manifest.json")

    def load_latest_manifest(self, source_id: str) -> tuple[str, SnapshotManifest] | None:
        run_id = self.latest_run_id(source_id)
        if not run_id:
            return None
        return run_id, self.load_run_manifest(run_id)

    def payload_path(self, run_id: str, storage_key: str) -> Path:
        return self.run_dir(run_id) / storage_key

    def prepare_run_dir(self, run_id: str, overwrite: bool = False) -> Path:
        run_dir = self.run_dir(run_id)
        if run_dir.exists() and not overwrite:
            raise FileExistsError(f"run directory already exists: {run_dir}")
        (run_dir / "payloads").mkdir(parents=True, exist_ok=True)
        return run_dir

    def copy_payloads(self, run_id: str, specs: Iterable[ArtifactSourceSpec]) -> tuple[tuple[ArtifactSourceSpec, ...], dict[str, str]]:
        run_dir = self.run_dir(run_id)
        copied_specs: list[ArtifactSourceSpec] = []
        storage_keys: dict[str, str] = {}
        used_names: set[str] = set()
        for spec in specs:
            if spec.path and not spec.error:
                original = Path(spec.path)
                suffix = original.suffix if original.suffix else ".bin"
                base_name = sanitize_path_part(spec.id)
                file_name = f"{base_name}{suffix}"
                counter = 2
                while file_name in used_names:
                    file_name = f"{base_name}-{counter}{suffix}"
                    counter += 1
                used_names.add(file_name)
                storage_key = f"payloads/{file_name}"
                destination = run_dir / storage_key
                destination.write_bytes(read_bytes(spec.path))
                storage_keys[spec.id] = storage_key
                copied_specs.append(replace(spec, path=str(destination)))
            else:
                copied_specs.append(spec)
        return tuple(copied_specs), storage_keys

    def manifest_with_storage_keys(self, manifest: SnapshotManifest, storage_keys: dict[str, str]) -> SnapshotManifest:
        records: list[ArtifactSnapshotRecord] = []
        for record in manifest.artifacts:
            snapshot = record.snapshot
            if snapshot and record.artifact.id in storage_keys:
                snapshot = replace(snapshot, storage_key=storage_keys[record.artifact.id])
            records.append(replace(record, snapshot=snapshot))
        return replace(manifest, artifacts=tuple(records))

    def save_run(
        self,
        run_id: str,
        source_id: str,
        original_specs: tuple[ArtifactSourceSpec, ...],
        manifest: SnapshotManifest,
        evaluation: CrawlerRunEvaluation,
        master_diff: MasterDiffAttachment | None = None,
        update_latest: bool = True,
    ) -> LocalRunResult:
        run_dir = self.run_dir(run_id)
        source_spec_path = run_dir / "source-spec.json"
        manifest_path = run_dir / "manifest.json"
        evaluation_path = run_dir / "evaluation.json"
        master_diff_path = run_dir / "master-diff.json" if master_diff else None

        write_json(source_spec_path, {"source_id": source_id, "artifacts": original_specs})
        write_json(manifest_path, manifest)
        write_json(evaluation_path, evaluation)
        if master_diff and master_diff_path:
            write_json(master_diff_path, master_diff)
        if update_latest:
            pointer = self.latest_pointer_path(source_id)
            pointer.parent.mkdir(parents=True, exist_ok=True)
            pointer.write_text(run_id + "\n", encoding="utf-8")

        payload_paths = tuple(str(run_dir / key) for key in sorted(record.snapshot.storage_key for record in manifest.artifacts if record.snapshot and record.snapshot.storage_key))
        return LocalRunResult(
            run_id=run_id,
            source_id=source_id,
            run_dir=str(run_dir),
            previous_run_id=None,
            manifest_path=str(manifest_path),
            evaluation_path=str(evaluation_path),
            source_spec_path=str(source_spec_path),
            master_diff_path=str(master_diff_path) if master_diff_path else None,
            payload_paths=payload_paths,
            evaluation=evaluation,
        )


def _select_master_record(manifest: SnapshotManifest, artifact_id: str | None) -> ArtifactSnapshotRecord | None:
    candidates = [record for record in manifest.artifacts if record.snapshot and record.snapshot.storage_key]
    if artifact_id:
        for record in candidates:
            if record.artifact.id == artifact_id:
                return record
        return None
    master_candidates = [record for record in candidates if record.artifact.type == ArtifactType.MASTER_CSV]
    return master_candidates[0] if len(master_candidates) == 1 else None


def _resolve_previous(
    store: LocalRunStore,
    source_id: str,
    previous: str | None,
) -> tuple[str | None, SnapshotManifest | None]:
    if previous in (None, "latest"):
        latest = store.load_latest_manifest(source_id)
        return latest if latest else (None, None)
    if previous == "none":
        return None, None
    return previous, store.load_run_manifest(previous)


def execute_local_run(
    specs: Iterable[ArtifactSourceSpec],
    store_dir: str | Path = DEFAULT_STORE_DIR,
    source_id: str = "ssk-chitan",
    run_id: str | None = None,
    generated_at: str | None = None,
    previous: str | None = "latest",
    master_artifact_id: str | None = None,
    allow_candidate_mapping: bool = False,
    schema_path: str | Path | None = None,
    overwrite: bool = False,
) -> LocalRunResult:
    original_specs = tuple(specs)
    actual_run_id = sanitize_path_part(run_id or _now_run_id())
    store = LocalRunStore(store_dir)
    store.prepare_run_dir(actual_run_id, overwrite=overwrite)
    previous_run_id, previous_manifest = _resolve_previous(store, source_id, previous)
    copied_specs, storage_keys = store.copy_payloads(actual_run_id, original_specs)
    manifest = build_manifest_from_specs(source_id, copied_specs, generated_at=generated_at)
    manifest = store.manifest_with_storage_keys(manifest, storage_keys)

    master_diff = None
    current_master = _select_master_record(manifest, master_artifact_id)
    previous_master = _select_master_record(previous_manifest, master_artifact_id) if previous_manifest else None
    if current_master and previous_master and previous_run_id:
        old_source = store.payload_path(previous_run_id, previous_master.snapshot.storage_key)
        new_source = store.payload_path(actual_run_id, current_master.snapshot.storage_key)
        master_diff = build_master_diff_attachment(
            str(old_source),
            str(new_source),
            schema_path=schema_path or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=allow_candidate_mapping,
        )

    evaluation = evaluate_run(manifest, previous=previous_manifest, master_diff=master_diff)
    result = store.save_run(
        actual_run_id,
        source_id,
        original_specs,
        manifest,
        evaluation,
        master_diff=master_diff,
    )
    return replace(result, previous_run_id=previous_run_id)
