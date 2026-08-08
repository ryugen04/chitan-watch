from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import asdict, is_dataclass
from enum import Enum
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .local_store import DEFAULT_STORE_DIR, LocalRunStore

DEFAULT_WEB_DIR = Path(__file__).resolve().parents[2] / "apps" / "web"


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


def json_response(value, status: int = 200) -> tuple[int, bytes, str]:
    return status, (json.dumps(to_jsonable(value), ensure_ascii=False, indent=2) + "\n").encode("utf-8"), "application/json; charset=utf-8"


def _sorted_run_ids(store: LocalRunStore) -> tuple[str, ...]:
    summaries = []
    for run_id in store.list_run_ids():
        try:
            evaluated_at = store.load_run_evaluation_json(run_id).get("evaluated_at", "")
        except FileNotFoundError:
            evaluated_at = ""
        summaries.append((evaluated_at, run_id))
    return tuple(run_id for _evaluated_at, run_id in sorted(summaries, reverse=True))


def _event_items(store: LocalRunStore) -> list[dict]:
    events: list[dict] = []
    for run_id in _sorted_run_ids(store):
        bundle = store.load_run_change_events_json(run_id)
        for event in bundle.get("events", []):
            item = dict(event)
            item["run_id"] = run_id
            events.append(item)
    return events


def _run_summary(store: LocalRunStore, run_id: str) -> dict:
    evaluation = store.load_run_evaluation_json(run_id)
    manifest = store.load_run_manifest(run_id)
    return {
        "run_id": run_id,
        "source_id": evaluation.get("source_id", manifest.source_id),
        "status": evaluation.get("status"),
        "evaluated_at": evaluation.get("evaluated_at"),
        "artifact_count": evaluation.get("artifact_count", len(manifest.artifacts)),
        "changed_artifact_count": evaluation.get("changed_artifact_count", 0),
        "failed_artifact_count": evaluation.get("failed_artifact_count", 0),
        "change_event_count": len(store.load_run_change_events_json(run_id).get("events", [])),
    }


def build_api_payload(path: str, store: LocalRunStore) -> tuple[int, bytes, str] | None:
    if path == "/api/health":
        return json_response({"ok": True, "store_dir": str(store.root), "run_count": len(store.list_run_ids())})
    if path == "/api/runs":
        return json_response({"runs": [_run_summary(store, run_id) for run_id in _sorted_run_ids(store)]})
    if path.startswith("/api/runs/"):
        run_id = unquote(path.removeprefix("/api/runs/")).strip("/")
        if not run_id or run_id not in store.list_run_ids():
            return json_response({"error": "run not found"}, status=404)
        return json_response(
            {
                "run": _run_summary(store, run_id),
                "manifest": to_jsonable(store.load_run_manifest(run_id)),
                "evaluation": store.load_run_evaluation_json(run_id),
                "change_events": store.load_run_change_events_json(run_id),
            }
        )
    if path == "/api/changes":
        return json_response({"changes": _event_items(store)})
    if path.startswith("/api/changes/"):
        change_id = unquote(path.removeprefix("/api/changes/")).strip("/")
        for event in _event_items(store):
            if event.get("id") == change_id:
                return json_response({"change": event})
        return json_response({"error": "change not found"}, status=404)
    if path == "/api/source-health":
        run_ids = _sorted_run_ids(store)
        latest = run_ids[0] if run_ids else None
        if not latest:
            return json_response({"latest_run_id": None, "sources": []})
        evaluation = store.load_run_evaluation_json(latest)
        manifest = store.load_run_manifest(latest)
        sources = []
        for record in manifest.artifacts:
            change = next((item for item in evaluation.get("artifact_changes", []) if item.get("artifact_id") == record.artifact.id), None)
            sources.append(
                {
                    "artifact_id": record.artifact.id,
                    "title": record.artifact.title,
                    "type": record.artifact.type.value,
                    "canonical_url": record.artifact.canonical_url,
                    "state": change.get("state") if change else "unknown",
                    "sha256": record.snapshot.sha256 if record.snapshot else None,
                    "error": record.error,
                }
            )
        return json_response({"latest_run_id": latest, "status": evaluation.get("status"), "sources": sources})
    return None


class ChitanRequestHandler(SimpleHTTPRequestHandler):
    store = LocalRunStore(DEFAULT_STORE_DIR)
    web_dir = DEFAULT_WEB_DIR

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            payload = build_api_payload(parsed.path, self.store)
            if payload is None:
                payload = json_response({"error": "not found"}, status=404)
            status, body, content_type = payload
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        self._serve_static(parsed.path)

    def _serve_static(self, path: str) -> None:
        relative = unquote(path.lstrip("/")) or "index.html"
        candidate = (self.web_dir / relative).resolve()
        web_root = self.web_dir.resolve()
        if not str(candidate).startswith(str(web_root)) or not candidate.exists() or candidate.is_dir():
            candidate = web_root / "index.html"
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(str(candidate))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def make_server(host: str, port: int, store_dir: str | Path = DEFAULT_STORE_DIR, web_dir: str | Path = DEFAULT_WEB_DIR) -> ThreadingHTTPServer:
    selected_store = LocalRunStore(store_dir)
    selected_web_dir = Path(web_dir)

    class Handler(ChitanRequestHandler):
        store = selected_store
        web_dir = selected_web_dir

    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    parser = argparse.ArgumentParser(prog="chitan-watch-api")
    parser.add_argument("--store-dir", default=str(DEFAULT_STORE_DIR))
    parser.add_argument("--web-dir", default=str(DEFAULT_WEB_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.host, args.port, store_dir=args.store_dir, web_dir=args.web_dir)
    print(f"Chitan Watch API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
