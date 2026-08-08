from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import hashlib

from .collector import classify_artifact
from .models import Artifact, ArtifactType


@dataclass(frozen=True)
class DiscoveredArtifact:
    artifact: Artifact
    href: str
    domain: str


class AnchorExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href.strip()
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        title = " ".join(part.strip() for part in self._current_text if part.strip())
        self.links.append((self._current_href, " ".join(title.split())))
        self._current_href = None
        self._current_text = []


def fetch_html(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": "chitan-watch/0.1 source-discovery"})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def discover_artifacts(
    seed_url: str,
    html: str,
    source_id: str,
    allowed_domains: tuple[str, ...],
    artifact_types: tuple[ArtifactType, ...] | None = None,
) -> tuple[DiscoveredArtifact, ...]:
    extractor = AnchorExtractor()
    extractor.feed(html)

    allowed = {domain.lower() for domain in allowed_domains}
    artifacts: list[DiscoveredArtifact] = []
    seen: set[str] = set()

    for href, title in extractor.links:
        if href.startswith("#") or href.lower().startswith(("javascript:", "mailto:", "tel:")):
            continue
        absolute_url = urljoin(seed_url, href)
        parsed = urlparse(absolute_url)
        domain = parsed.netloc.lower()
        if domain not in allowed:
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)

        artifact_type = classify_artifact(absolute_url, title)
        if artifact_types is not None and artifact_type not in artifact_types:
            continue

        digest = hashlib.sha256(absolute_url.encode("utf-8")).hexdigest()[:16]
        artifacts.append(
            DiscoveredArtifact(
                artifact=Artifact(
                    id=f"art_{digest}",
                    source_id=source_id,
                    type=artifact_type,
                    title=title or absolute_url,
                    canonical_url=absolute_url,
                ),
                href=href,
                domain=domain,
            )
        )

    return tuple(artifacts)


def discover_seed_url(
    seed_url: str,
    source_id: str,
    allowed_domains: tuple[str, ...],
    artifact_types: tuple[ArtifactType, ...] | None = None,
) -> tuple[DiscoveredArtifact, ...]:
    return discover_artifacts(
        seed_url=seed_url,
        html=fetch_html(seed_url),
        source_id=source_id,
        allowed_domains=allowed_domains,
        artifact_types=artifact_types,
    )
