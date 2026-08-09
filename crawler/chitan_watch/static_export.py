from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .api import build_api_payload
from .local_store import DEFAULT_STORE_DIR, LocalRunStore
from .rss import RssFeedOptions, rss_xml_from_store

DEFAULT_STATIC_DIR = Path("public")
DEFAULT_WEB_DIR = Path("apps") / "web"


@dataclass(frozen=True)
class StaticExportResult:
    output_dir: str
    site_url: str
    files: tuple[str, ...]
    run_count: int
    change_count: int


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json_payload(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _copy_web_assets(web_dir: Path, output_dir: Path) -> list[Path]:
    copied: list[Path] = []
    for source in web_dir.iterdir():
        if source.is_file() and source.name in {"index.html", "app.js", "styles.css"}:
            destination = output_dir / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied.append(destination)
    return copied


def export_static_site(
    store_dir: str | Path = DEFAULT_STORE_DIR,
    output_dir: str | Path = DEFAULT_STATIC_DIR,
    web_dir: str | Path = DEFAULT_WEB_DIR,
    site_url: str = "http://127.0.0.1:8765",
    max_rss_items: int = 50,
    replay_latest_rss_item: bool = False,
    rss_replay_nonce: str | None = None,
    rss_replay_detected_at: str | None = None,
) -> StaticExportResult:
    store = LocalRunStore(store_dir)
    output = Path(output_dir)
    web = Path(web_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    written = _copy_web_assets(web, output)
    rss_xml = rss_xml_from_store(
        store,
        options=RssFeedOptions(
            site_url=site_url,
            max_items=max_rss_items,
            replay_latest_item=replay_latest_rss_item,
            replay_nonce=rss_replay_nonce,
            replay_detected_at=rss_replay_detected_at,
        ),
    )
    _write_text(output / "rss.xml", rss_xml)
    _write_text(output / "feeds" / "changes.xml", rss_xml)
    written.extend([output / "rss.xml", output / "feeds" / "changes.xml"])

    payloads = {
        "runs.json": build_api_payload("/api/runs", store, site_url=site_url),
        "changes.json": build_api_payload("/api/changes", store, site_url=site_url),
        "source-health.json": build_api_payload("/api/source-health", store, site_url=site_url),
        "health.json": build_api_payload("/api/health", store, site_url=site_url),
    }
    for name, payload in payloads.items():
        if payload is None:
            continue
        _status, body, _content_type = payload
        path = output / "static" / name
        _write_json_payload(path, body)
        written.append(path)

    changes_payload = json.loads((output / "static" / "changes.json").read_text(encoding="utf-8")) if (output / "static" / "changes.json").exists() else {"changes": []}
    return StaticExportResult(
        output_dir=str(output),
        site_url=site_url,
        files=tuple(str(path.relative_to(output)) for path in sorted(written)),
        run_count=len(store.list_run_ids()),
        change_count=len(changes_payload.get("changes", [])),
    )
