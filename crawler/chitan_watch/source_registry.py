from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .discovery import discover_artifacts, discover_seed_url
from .models import ArtifactType
from .run_state import ArtifactSourceSpec

DEFAULT_SOURCE_REGISTRY_PATH = Path(__file__).with_name("source_registry.json")


@dataclass(frozen=True)
class SourceRegistryEntry:
    id: str
    title: str
    seed_url: str
    source_id: str
    allowed_domains: tuple[str, ...]
    artifact_types: tuple[ArtifactType, ...]
    source_group: str
    source_layer: str
    source_owner: str
    source_role: str
    jurisdiction_scope: str
    monitor_mode: str
    notify_policy: str
    review_policy: str
    evidence_level: str
    freshness_sla: str
    direct: bool = False
    include_title_keywords: tuple[str, ...] = ()
    include_url_keywords: tuple[str, ...] = ()
    exclude_title_keywords: tuple[str, ...] = ()
    exclude_url_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceRegistry:
    version: int
    entries: tuple[SourceRegistryEntry, ...]


def _tuple(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    return tuple(str(item) for item in raw)


def _entry_from_dict(raw: dict) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        id=str(raw["id"]),
        title=str(raw.get("title") or raw["id"]),
        seed_url=str(raw["seed_url"]),
        source_id=str(raw.get("source_id") or "ssk-chitan"),
        allowed_domains=_tuple(raw.get("allowed_domains")),
        artifact_types=tuple(ArtifactType(str(item)) for item in raw.get("artifact_types", ())),
        source_group=str(raw.get("source_group") or "source"),
        source_layer=str(raw.get("source_layer") or raw.get("source_group") or "source"),
        source_owner=str(raw.get("source_owner") or "unknown"),
        source_role=str(raw.get("source_role") or raw.get("source_group") or "source"),
        jurisdiction_scope=str(raw.get("jurisdiction_scope") or "national"),
        monitor_mode=str(raw.get("monitor_mode") or "file_hash"),
        notify_policy=str(raw.get("notify_policy") or "important_only"),
        review_policy=str(raw.get("review_policy") or "conditional"),
        evidence_level=str(raw.get("evidence_level") or "CONFIRMED"),
        freshness_sla=str(raw.get("freshness_sla") or "daily"),
        direct=bool(raw.get("direct", False)),
        include_title_keywords=_tuple(raw.get("include_title_keywords")),
        include_url_keywords=_tuple(raw.get("include_url_keywords")),
        exclude_title_keywords=_tuple(raw.get("exclude_title_keywords")),
        exclude_url_keywords=_tuple(raw.get("exclude_url_keywords")),
    )


def load_source_registry(path: str | Path = DEFAULT_SOURCE_REGISTRY_PATH) -> SourceRegistry:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return SourceRegistry(
        version=int(raw.get("version", 1)),
        entries=tuple(_entry_from_dict(item) for item in raw.get("entries", ())),
    )


def _matches(value: str, keywords: tuple[str, ...]) -> bool:
    if not keywords:
        return True
    haystack = value.lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _excluded(value: str, keywords: tuple[str, ...]) -> bool:
    haystack = value.lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _included(title: str, url: str, title_keywords: tuple[str, ...], url_keywords: tuple[str, ...]) -> bool:
    if not title_keywords and not url_keywords:
        return True
    title_match = bool(title_keywords) and _matches(title, title_keywords)
    url_match = bool(url_keywords) and _matches(url, url_keywords)
    return title_match or url_match


def _path_for_artifact(artifact_id: str, canonical_url: str, source_map: dict[str, str]) -> str:
    return source_map.get(artifact_id) or source_map.get(canonical_url) or canonical_url


def _spec_from_entry(entry: SourceRegistryEntry, canonical_url: str, title: str, artifact_type: ArtifactType, source_map: dict[str, str]) -> ArtifactSourceSpec:
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
    return ArtifactSourceSpec(
        id=f"art_{digest}",
        type=artifact_type,
        title=title,
        canonical_url=canonical_url,
        path=_path_for_artifact(f"art_{digest}", canonical_url, source_map),
        source_group=entry.source_group,
        source_layer=entry.source_layer,
        source_owner=entry.source_owner,
        source_role=entry.source_role,
        jurisdiction_scope=entry.jurisdiction_scope,
        monitor_mode=entry.monitor_mode,
        notify_policy=entry.notify_policy,
        review_policy=entry.review_policy,
        evidence_level=entry.evidence_level,
        freshness_sla=entry.freshness_sla,
    )


def registry_specs(
    registry: SourceRegistry,
    source_map: dict[str, str] | None = None,
    seed_html_by_url: dict[str, str] | None = None,
    limit: int | None = None,
) -> tuple[ArtifactSourceSpec, ...]:
    mapping = source_map or {}
    seed_html = seed_html_by_url or {}
    specs: list[ArtifactSourceSpec] = []
    seen_urls: set[str] = set()

    for entry in registry.entries:
        if entry.direct and entry.seed_url not in seen_urls:
            direct_type = entry.artifact_types[0] if entry.artifact_types else ArtifactType.HTML
            specs.append(_spec_from_entry(entry, entry.seed_url, entry.title, direct_type, mapping))
            seen_urls.add(entry.seed_url)

        html = seed_html.get(entry.seed_url)
        discovered = (
            discover_artifacts(entry.seed_url, html, source_id=entry.source_id, allowed_domains=entry.allowed_domains, artifact_types=entry.artifact_types or None)
            if html is not None
            else discover_seed_url(entry.seed_url, source_id=entry.source_id, allowed_domains=entry.allowed_domains, artifact_types=entry.artifact_types or None)
        )
        for item in discovered:
            artifact = item.artifact
            if not _included(artifact.title, artifact.canonical_url, entry.include_title_keywords, entry.include_url_keywords):
                continue
            if _excluded(artifact.title, entry.exclude_title_keywords) or _excluded(artifact.canonical_url, entry.exclude_url_keywords):
                continue
            if artifact.canonical_url in seen_urls:
                continue
            specs.append(_spec_from_entry(entry, artifact.canonical_url, artifact.title, artifact.type, mapping))
            seen_urls.add(artifact.canonical_url)
            if limit is not None and len(specs) >= limit:
                return tuple(specs)
    return tuple(specs)


def registry_source_ids(registry: SourceRegistry) -> tuple[str, ...]:
    return tuple(dict.fromkeys(entry.source_id for entry in registry.entries))
