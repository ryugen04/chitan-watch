from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .discovery import discover_artifacts, discover_seed_url
from .local_store import DEFAULT_STORE_DIR, LocalRunResult, execute_local_run
from .models import ArtifactType
from .run_state import ArtifactSourceSpec
from .source_registry import DEFAULT_SOURCE_REGISTRY_PATH, load_source_registry, registry_specs

DEFAULT_ALLOWED_DOMAINS = ("www.ssk.or.jp", "www.mhlw.go.jp")
DEFAULT_ARTIFACT_TYPES = (ArtifactType.MASTER_CSV, ArtifactType.MASTER_EXCEL, ArtifactType.SCHEMA)


@dataclass(frozen=True)
class LiveDiscoveryResult:
    seed_url: str
    source_id: str
    artifact_count: int
    specs: tuple[ArtifactSourceSpec, ...]


def load_source_map(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if "sources" in raw:
        raw = raw["sources"]
    return {str(key): str(value) for key, value in raw.items()}


def _path_for_artifact(artifact_id: str, canonical_url: str, source_map: dict[str, str]) -> str:
    return source_map.get(artifact_id) or source_map.get(canonical_url) or canonical_url


def discover_live_specs(
    seed_url: str,
    source_id: str = "ssk-chitan",
    allowed_domains: tuple[str, ...] = DEFAULT_ALLOWED_DOMAINS,
    artifact_types: tuple[ArtifactType, ...] = DEFAULT_ARTIFACT_TYPES,
    seed_html: str | None = None,
    source_map: dict[str, str] | None = None,
    limit: int | None = None,
) -> LiveDiscoveryResult:
    discovered = (
        discover_artifacts(seed_url, seed_html, source_id=source_id, allowed_domains=allowed_domains, artifact_types=artifact_types)
        if seed_html is not None
        else discover_seed_url(seed_url, source_id=source_id, allowed_domains=allowed_domains, artifact_types=artifact_types)
    )
    mapping = source_map or {}
    specs = tuple(
        ArtifactSourceSpec(
            id=item.artifact.id,
            type=item.artifact.type,
            title=item.artifact.title,
            canonical_url=item.artifact.canonical_url,
            path=_path_for_artifact(item.artifact.id, item.artifact.canonical_url, mapping),
        )
        for item in discovered[:limit]
    )
    return LiveDiscoveryResult(seed_url=seed_url, source_id=source_id, artifact_count=len(specs), specs=specs)


def execute_live_local_run(
    seed_url: str,
    store_dir: str | Path = DEFAULT_STORE_DIR,
    source_id: str = "ssk-chitan",
    allowed_domains: tuple[str, ...] = DEFAULT_ALLOWED_DOMAINS,
    artifact_types: tuple[ArtifactType, ...] = DEFAULT_ARTIFACT_TYPES,
    seed_html_file: str | Path | None = None,
    source_map_file: str | Path | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
    previous: str | None = "latest",
    master_artifact_id: str | None = None,
    allow_candidate_mapping: bool = False,
    schema_path: str | Path | None = None,
    overwrite: bool = False,
    limit: int | None = None,
) -> LocalRunResult:
    seed_html = Path(seed_html_file).read_text(encoding="utf-8") if seed_html_file else None
    discovery = discover_live_specs(
        seed_url=seed_url,
        source_id=source_id,
        allowed_domains=allowed_domains,
        artifact_types=artifact_types,
        seed_html=seed_html,
        source_map=load_source_map(source_map_file),
        limit=limit,
    )
    return execute_local_run(
        discovery.specs,
        store_dir=store_dir,
        source_id=source_id,
        run_id=run_id,
        generated_at=generated_at,
        previous=previous,
        master_artifact_id=master_artifact_id,
        allow_candidate_mapping=allow_candidate_mapping,
        schema_path=schema_path,
        overwrite=overwrite,
    )


def execute_registry_local_run(
    registry_file: str | Path = DEFAULT_SOURCE_REGISTRY_PATH,
    store_dir: str | Path = DEFAULT_STORE_DIR,
    source_id: str = "chitan-watch",
    seed_html_file: str | Path | None = None,
    source_map_file: str | Path | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
    previous: str | None = "latest",
    master_artifact_id: str | None = None,
    allow_candidate_mapping: bool = False,
    schema_path: str | Path | None = None,
    overwrite: bool = False,
    limit: int | None = None,
) -> LocalRunResult:
    registry = load_source_registry(registry_file)
    seed_html_by_url = {}
    if seed_html_file:
        html = Path(seed_html_file).read_text(encoding="utf-8")
        seed_html_by_url = {entry.seed_url: html for entry in registry.entries}
    specs = registry_specs(
        registry,
        source_map=load_source_map(source_map_file),
        seed_html_by_url=seed_html_by_url,
        limit=limit,
    )
    return execute_local_run(
        specs,
        store_dir=store_dir,
        source_id=source_id,
        run_id=run_id,
        generated_at=generated_at,
        previous=previous,
        master_artifact_id=master_artifact_id,
        allow_candidate_mapping=allow_candidate_mapping,
        schema_path=schema_path,
        overwrite=overwrite,
    )
