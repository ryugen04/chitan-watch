from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


ITEM_ROW_PATTERN = re.compile(
    r"^\s*(?:(?P<old>\d+)\s+)?(?P<new>\d{1,2}(?:_\d+)?)\s+(?P<name>.+?)\s{2,}(?P<data_type>文字列|数字|日本語)\s+",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ItemCandidate:
    old_item_number: str | None
    new_item_number: str
    item_name: str
    data_type: str


@dataclass(frozen=True)
class ItemListExtraction:
    source_pdf: str
    candidate_count: int
    candidates: tuple[ItemCandidate, ...]

    @property
    def has_duplicate_new_numbers(self) -> bool:
        seen: set[str] = set()
        for candidate in self.candidates:
            if candidate.new_item_number in seen:
                return True
            seen.add(candidate.new_item_number)
        return False


def extract_pdf_text(pdf_path: str | Path, output_path: str | Path | None = None) -> str:
    pdf_path = Path(pdf_path)
    if output_path is None:
        output_path = pdf_path.with_suffix(".txt")
    output_path = Path(output_path)
    subprocess.run(["pdftotext", "-layout", str(pdf_path), str(output_path)], check=True)
    return output_path.read_text(encoding="utf-8", errors="replace")


def parse_item_candidates(text: str, source_pdf: str = "") -> ItemListExtraction:
    candidates: list[ItemCandidate] = []
    for match in ITEM_ROW_PATTERN.finditer(text):
        name = " ".join(match.group("name").split())
        candidates.append(
            ItemCandidate(
                old_item_number=match.group("old"),
                new_item_number=match.group("new"),
                item_name=name,
                data_type=match.group("data_type"),
            )
        )
    return ItemListExtraction(source_pdf=source_pdf, candidate_count=len(candidates), candidates=tuple(candidates))
