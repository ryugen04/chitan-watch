from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .snapshot import compute_sha256


ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp932")
DELIMITER_CANDIDATES = (",", "\t", ";", "|")


@dataclass(frozen=True)
class CsvAnalysis:
    source: str
    sha256: str
    byte_length: int
    encoding: str
    delimiter: str
    has_header: bool
    column_count: int
    headers: tuple[str, ...]
    record_count: int
    sample_row_count: int
    inconsistent_row_count: int


def read_bytes(source: str, timeout: int = 60) -> bytes:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = Request(source, headers={"User-Agent": "chitan-watch/0.1 csv-analysis"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    return Path(source).read_bytes()


def decode_csv_bytes(content: bytes, candidates: tuple[str, ...] = ENCODING_CANDIDATES) -> tuple[str, str]:
    errors: list[str] = []
    for encoding in candidates:
        try:
            return encoding, content.decode(encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeDecodeError("csv-analysis", content, 0, min(len(content), 1), "; ".join(errors))


def detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(DELIMITER_CANDIDATES))
        return dialect.delimiter
    except csv.Error:
        lines = [line for line in sample.splitlines() if line]
        scores = {delimiter: sum(line.count(delimiter) for line in lines[:10]) for delimiter in DELIMITER_CANDIDATES}
        return max(scores, key=scores.get)


def analyze_csv_bytes(source: str, content: bytes, sample_rows: int = 3) -> CsvAnalysis:
    encoding, text = decode_csv_bytes(content)
    sample = text[:65536]
    delimiter = detect_delimiter(sample)
    reader = csv.reader(StringIO(text), delimiter=delimiter)
    rows = list(reader)
    non_empty_rows = [row for row in rows if any(cell.strip() for cell in row)]

    if not non_empty_rows:
        return CsvAnalysis(
            source=source,
            sha256=compute_sha256(content),
            byte_length=len(content),
            encoding=encoding,
            delimiter=delimiter,
            has_header=False,
            column_count=0,
            headers=(),
            record_count=0,
            sample_row_count=0,
            inconsistent_row_count=0,
        )

    header = tuple(cell.strip() for cell in non_empty_rows[0])
    try:
        has_header = csv.Sniffer().has_header(sample)
    except csv.Error:
        has_header = any(not cell.strip().isdigit() for cell in header)
    column_count = len(header)
    data_rows = non_empty_rows[1:] if has_header else non_empty_rows
    inconsistent = sum(1 for row in data_rows if len(row) != column_count)

    return CsvAnalysis(
        source=source,
        sha256=compute_sha256(content),
        byte_length=len(content),
        encoding=encoding,
        delimiter=delimiter,
        has_header=has_header,
        column_count=column_count,
        headers=header if has_header else (),
        record_count=len(data_rows),
        sample_row_count=min(sample_rows, len(data_rows)),
        inconsistent_row_count=inconsistent,
    )


def analyze_csv_source(source: str) -> CsvAnalysis:
    return analyze_csv_bytes(source, read_bytes(source))
