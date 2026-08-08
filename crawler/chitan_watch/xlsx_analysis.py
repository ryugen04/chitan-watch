from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import io
import re
import xml.etree.ElementTree as ET
import zipfile

from .snapshot import compute_sha256

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


@dataclass(frozen=True)
class SheetAnalysis:
    name: str
    sheet_id: str
    relationship_id: str
    path: str
    dimension_ref: str | None
    max_row: int
    max_column: int
    non_empty_cell_count: int
    first_rows: tuple[tuple[str, ...], ...]
    tail_cells: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class XlsxAnalysis:
    source: str
    sha256: str
    byte_length: int
    sheet_count: int
    sheets: tuple[SheetAnalysis, ...]


def read_xlsx_bytes(source: str, timeout: int = 60) -> bytes:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = Request(source, headers={"User-Agent": "chitan-watch/0.1 xlsx-analysis"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    return Path(source).read_bytes()


def column_to_number(column: str) -> int:
    value = 0
    for char in column:
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def parse_dimension(dimension_ref: str | None) -> tuple[int, int]:
    if not dimension_ref:
        return 0, 0
    end_ref = dimension_ref.split(":")[-1]
    match = CELL_REF.fullmatch(end_ref)
    if not match:
        return 0, 0
    column, row = match.groups()
    return int(row), column_to_number(column)


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall("main:si", NS):
        parts = [node.text or "" for node in si.findall(".//main:t", NS)]
        values.append("".join(parts))
    return values


def _sheet_paths(zf: zipfile.ZipFile) -> list[tuple[str, str, str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pkgrel:Relationship", NS)}
    result = []
    for sheet in workbook.findall("main:sheets/main:sheet", NS):
        name = sheet.attrib["name"]
        sheet_id = sheet.attrib["sheetId"]
        relationship_id = sheet.attrib[f"{{{NS['rel']}}}id"]
        target = rel_targets[relationship_id]
        path = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
        result.append((name, sheet_id, relationship_id, path))
    return result


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS))
    value = cell.find("main:v", NS)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text


def analyze_xlsx_bytes(source: str, content: bytes, sample_rows: int = 3, tail_cells: int = 12) -> XlsxAnalysis:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared_strings = _read_shared_strings(zf)
        sheets: list[SheetAnalysis] = []
        for name, sheet_id, relationship_id, path in _sheet_paths(zf):
            root = ET.fromstring(zf.read(path))
            dimension = root.find("main:dimension", NS)
            dimension_ref = dimension.attrib.get("ref") if dimension is not None else None
            max_row, max_column = parse_dimension(dimension_ref)
            rows_out: list[tuple[str, ...]] = []
            cells_seen: list[tuple[str, str]] = []
            for row in root.findall("main:sheetData/main:row", NS):
                row_values: list[str] = []
                for cell in row.findall("main:c", NS):
                    value = _cell_value(cell, shared_strings)
                    if value != "":
                        cells_seen.append((cell.attrib.get("r", ""), value))
                    row_values.append(value)
                if any(row_values) and len(rows_out) < sample_rows:
                    rows_out.append(tuple(row_values))
            sheets.append(
                SheetAnalysis(
                    name=name,
                    sheet_id=sheet_id,
                    relationship_id=relationship_id,
                    path=path,
                    dimension_ref=dimension_ref,
                    max_row=max_row,
                    max_column=max_column,
                    non_empty_cell_count=len(cells_seen),
                    first_rows=tuple(rows_out),
                    tail_cells=tuple(cells_seen[-tail_cells:]),
                )
            )
    return XlsxAnalysis(source=source, sha256=compute_sha256(content), byte_length=len(content), sheet_count=len(sheets), sheets=tuple(sheets))


def analyze_xlsx_source(source: str) -> XlsxAnalysis:
    return analyze_xlsx_bytes(source, read_xlsx_bytes(source))
