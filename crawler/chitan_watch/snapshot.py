from __future__ import annotations

from datetime import datetime, timezone
from email.message import Message
from urllib.request import Request, urlopen
import hashlib

from .models import Snapshot


class SnapshotFetchError(RuntimeError):
    def __init__(self, url: str, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.url = url
        self.http_status = http_status


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_snapshot(
    artifact_id: str,
    source_url: str,
    http_status: int,
    headers: Message | dict[str, str],
    content: bytes,
    retrieved_at: str | None = None,
) -> Snapshot:
    if http_status < 200 or http_status >= 300:
        raise SnapshotFetchError(source_url, f"HTTP status {http_status} is not a successful snapshot", http_status=http_status)

    def header(name: str) -> str | None:
        if isinstance(headers, Message):
            return headers.get(name)
        return headers.get(name) or headers.get(name.lower())

    content_length = header("Content-Length")
    actual_length = len(content)
    return Snapshot(
        id=f"snap_{compute_sha256((artifact_id + source_url + compute_sha256(content)).encode('utf-8'))[:16]}",
        artifact_id=artifact_id,
        retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(),
        source_url=source_url,
        http_status=http_status,
        etag=header("ETag"),
        last_modified=header("Last-Modified"),
        sha256=compute_sha256(content),
        content_type=header("Content-Type"),
        content_length=int(content_length) if content_length and content_length.isdigit() else actual_length,
        storage_key=None,
        parser_status=None,
    )


def fetch_snapshot(artifact_id: str, source_url: str, timeout: int = 60) -> Snapshot:
    request = Request(source_url, headers={"User-Agent": "chitan-watch/0.1 snapshot-probe"})
    with urlopen(request, timeout=timeout) as response:
        content = response.read()
        return build_snapshot(
            artifact_id=artifact_id,
            source_url=source_url,
            http_status=response.status,
            headers=response.headers,
            content=content,
        )
