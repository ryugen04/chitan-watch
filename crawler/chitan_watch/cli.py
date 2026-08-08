from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from enum import Enum

from .csv_analysis import analyze_csv_source
from .diff import diff_master_records
from .discovery import discover_seed_url
from .models import ArtifactType
from .identity import validate_record_identities
from .events import build_change_bundle
from .master_diff import diff_master_snapshots
from .master_snapshot import build_master_snapshot
from .parser import parse_master_csv_file
from .positional_master import DEFAULT_SCHEMA_PATH, parse_positional_csv_source, summarize_parse
from .pdf_items import extract_pdf_text, parse_item_candidates
from .snapshot import fetch_snapshot
from .xlsx_analysis import analyze_xlsx_source


def encode(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object is not JSON serializable: {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="chitan-watch")
    sub = parser.add_subparsers(dest="command", required=True)
    diff_cmd = sub.add_parser("diff", help="Diff two master CSV snapshots")
    diff_cmd.add_argument("old_csv")
    diff_cmd.add_argument("new_csv")

    discover_cmd = sub.add_parser("discover", help="Discover artifacts from an official seed page")
    discover_cmd.add_argument("seed_url")
    discover_cmd.add_argument("--source-id", default="ssk-chitan")
    discover_cmd.add_argument("--allowed-domain", action="append", dest="allowed_domains")
    discover_cmd.add_argument("--artifact-type", action="append", dest="artifact_types", choices=[item.value for item in ArtifactType])

    snapshot_cmd = sub.add_parser("snapshot", help="Fetch one artifact and emit deterministic Snapshot metadata")
    snapshot_cmd.add_argument("url")
    snapshot_cmd.add_argument("--artifact-id", required=True)

    analyze_cmd = sub.add_parser("analyze-csv", help="Analyze CSV structure from a URL or local file without storing payload")
    analyze_cmd.add_argument("source")

    pdf_items_cmd = sub.add_parser("extract-pdf-items", help="Extract item-list candidates from a local PDF using pdftotext")
    pdf_items_cmd.add_argument("pdf_path")

    xlsx_cmd = sub.add_parser("analyze-xlsx", help="Analyze XLSX workbook structure from a URL or local file without storing payload")
    xlsx_cmd.add_argument("source")

    parse_master_cmd = sub.add_parser("parse-master", help="Parse the 94-column headerless master CSV with the positional schema")
    parse_master_cmd.add_argument("source")
    parse_master_cmd.add_argument("--schema", default=None)
    parse_master_cmd.add_argument("--allow-candidate-mapping", action="store_true")
    parse_master_cmd.add_argument("--max-records", type=int, default=None)

    identity_cmd = sub.add_parser("validate-identity", help="Validate candidate record identity uniqueness for a master CSV")
    identity_cmd.add_argument("source")
    identity_cmd.add_argument("--schema", default=None)
    identity_cmd.add_argument("--allow-candidate-mapping", action="store_true")

    snapshot_master_cmd = sub.add_parser("snapshot-master", help="Emit normalized row fingerprints for a positional master CSV")
    snapshot_master_cmd.add_argument("source")
    snapshot_master_cmd.add_argument("--schema", default=None)
    snapshot_master_cmd.add_argument("--allow-candidate-mapping", action="store_true")
    snapshot_master_cmd.add_argument("--max-records", type=int, default=None)

    diff_master_cmd = sub.add_parser("diff-master", help="Diff two positional master CSV snapshots with row fingerprint safeguards")
    diff_master_cmd.add_argument("old_source")
    diff_master_cmd.add_argument("new_source")
    diff_master_cmd.add_argument("--schema", default=None)
    diff_master_cmd.add_argument("--allow-candidate-mapping", action="store_true")

    args = parser.parse_args()

    if args.command == "diff":
        old_validation, old_records = parse_master_csv_file(args.old_csv)
        new_validation, new_records = parse_master_csv_file(args.new_csv)
        errors = []
        if not old_validation.ok:
            errors.append(f"old schema break: missing {old_validation.missing_columns}")
        if not new_validation.ok:
            errors.append(f"new schema break: missing {new_validation.missing_columns}")
        changes = () if errors else diff_master_records(old_records, new_records)
        bundle = build_change_bundle(changes, errors=tuple(errors))
        print(json.dumps(bundle, default=encode, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    if args.command == "discover":
        allowed_domains = tuple(args.allowed_domains or ())
        if not allowed_domains:
            parser.error("discover requires at least one --allowed-domain")
        artifact_types = tuple(ArtifactType(value) for value in (args.artifact_types or ())) or None
        artifacts = discover_seed_url(args.seed_url, source_id=args.source_id, allowed_domains=allowed_domains, artifact_types=artifact_types)
        print(json.dumps({"seed_url": args.seed_url, "source_id": args.source_id, "artifacts": artifacts}, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "snapshot":
        snapshot = fetch_snapshot(args.artifact_id, args.url)
        print(json.dumps(snapshot, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "analyze-csv":
        analysis = analyze_csv_source(args.source)
        print(json.dumps(analysis, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "extract-pdf-items":
        text = extract_pdf_text(args.pdf_path)
        extraction = parse_item_candidates(text, source_pdf=args.pdf_path)
        print(json.dumps(extraction, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "analyze-xlsx":
        analysis = analyze_xlsx_source(args.source)
        print(json.dumps(analysis, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "parse-master":
        schema_path = args.schema or None
        schema, records = parse_positional_csv_source(
            args.source,
            schema_path=schema_path or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
            max_records=args.max_records,
        )
        print(json.dumps(summarize_parse(args.source, schema, records), default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "validate-identity":
        schema_path = args.schema or None
        _schema, records = parse_positional_csv_source(
            args.source,
            schema_path=schema_path or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
        )
        print(json.dumps(validate_record_identities(records), default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "snapshot-master":
        schema_path = args.schema or None
        schema, records = parse_positional_csv_source(
            args.source,
            schema_path=schema_path or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
            max_records=args.max_records,
        )
        snapshot = build_master_snapshot(args.source, schema, records)
        print(json.dumps(snapshot, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "diff-master":
        schema_path = args.schema or None
        old_schema, old_records = parse_positional_csv_source(
            args.old_source,
            schema_path=schema_path or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
        )
        new_schema, new_records = parse_positional_csv_source(
            args.new_source,
            schema_path=schema_path or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
        )
        old_snapshot = build_master_snapshot(args.old_source, old_schema, old_records)
        new_snapshot = build_master_snapshot(args.new_source, new_schema, new_records)
        diff = diff_master_snapshots(old_snapshot.rows, new_snapshot.rows)
        print(json.dumps(diff, default=encode, ensure_ascii=False, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
