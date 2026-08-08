from __future__ import annotations

from urllib.parse import urlparse

from .models import ArtifactType


CLASSIFICATION_RULES: tuple[tuple[tuple[str, ...], ArtifactType], ...] = (
    (("csv",), ArtifactType.MASTER_CSV),
    (("xlsx", "xls"), ArtifactType.MASTER_EXCEL),
    (("faq",), ArtifactType.FAQ),
    (("項目一覧", "schema", "siryo2"), ArtifactType.SCHEMA),
    (("入力要領", "guide"), ArtifactType.INPUT_GUIDE),
    (("マニュアル", "manual"), ArtifactType.MANUAL),
    (("入力例", "example"), ArtifactType.EXAMPLES),
)


def classify_artifact(url: str, title: str = "") -> ArtifactType:
    haystack = f"{url} {title}".lower()
    parsed = urlparse(url)
    path = parsed.path.lower()
    for needles, artifact_type in CLASSIFICATION_RULES:
        if any(needle.lower() in haystack for needle in needles):
            return artifact_type
    if "mhlw.go.jp" in parsed.netloc.lower():
        return ArtifactType.MHLW_DOCUMENT
    if path.endswith(".html") or path.endswith(".htm"):
        return ArtifactType.HTML
    if path.endswith(".pdf"):
        return ArtifactType.OTHER
    return ArtifactType.OTHER
