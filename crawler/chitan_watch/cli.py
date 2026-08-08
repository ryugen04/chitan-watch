from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from enum import Enum

from .csv_analysis import analyze_csv_source
from .diff import diff_master_records
from .discovery import discover_seed_url
from .models import ArtifactType
from .api import main as api_main
from .identity import validate_record_identities
from .events import build_change_bundle
from .live_crawl import DEFAULT_ALLOWED_DOMAINS, DEFAULT_ARTIFACT_TYPES, execute_live_local_run
from .local_store import DEFAULT_STORE_DIR, execute_local_run
from .master_diff import diff_master_snapshots
from .master_snapshot import build_master_snapshot
from .parser import parse_master_csv_file
from .positional_master import DEFAULT_SCHEMA_PATH, parse_positional_csv_source, summarize_parse
from .pdf_items import extract_pdf_text, parse_item_candidates
from .rss import RssFeedOptions, rss_xml_from_store_path
from .run_state import build_manifest_from_specs, build_master_diff_attachment, evaluate_run, load_manifest, load_specs
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

    build_manifest_cmd = sub.add_parser("build-manifest", help="Build a deterministic snapshot manifest from a local artifact spec JSON")
    build_manifest_cmd.add_argument("spec_json")
    build_manifest_cmd.add_argument("--source-id", default="ssk-chitan")
    build_manifest_cmd.add_argument("--generated-at", default=None)

    evaluate_run_cmd = sub.add_parser("evaluate-run", help="Evaluate current crawler manifest against an optional previous manifest")
    evaluate_run_cmd.add_argument("current_manifest")
    evaluate_run_cmd.add_argument("--previous-manifest", default=None)
    evaluate_run_cmd.add_argument("--master-old-source", default=None)
    evaluate_run_cmd.add_argument("--master-new-source", default=None)
    evaluate_run_cmd.add_argument("--schema", default=None)
    evaluate_run_cmd.add_argument("--allow-candidate-mapping", action="store_true")

    run_local_cmd = sub.add_parser("run-local", help="Execute a local crawler run into an ignored run directory")
    run_local_cmd.add_argument("spec_json")
    run_local_cmd.add_argument("--store-dir", default=str(DEFAULT_STORE_DIR))
    run_local_cmd.add_argument("--source-id", default="ssk-chitan")
    run_local_cmd.add_argument("--run-id", default=None)
    run_local_cmd.add_argument("--generated-at", default=None)
    run_local_cmd.add_argument("--previous", default="latest", help="latest, none, or an explicit previous run id")
    run_local_cmd.add_argument("--master-artifact-id", default=None)
    run_local_cmd.add_argument("--schema", default=None)
    run_local_cmd.add_argument("--allow-candidate-mapping", action="store_true")
    run_local_cmd.add_argument("--overwrite", action="store_true")

    run_official_cmd = sub.add_parser("run-official-local", help="Discover official artifacts and execute a local crawler run")
    run_official_cmd.add_argument("seed_url")
    run_official_cmd.add_argument("--store-dir", default=str(DEFAULT_STORE_DIR))
    run_official_cmd.add_argument("--source-id", default="ssk-chitan")
    run_official_cmd.add_argument("--allowed-domain", action="append", dest="allowed_domains")
    run_official_cmd.add_argument("--artifact-type", action="append", dest="artifact_types", choices=[item.value for item in ArtifactType])
    run_official_cmd.add_argument("--seed-html-file", default=None)
    run_official_cmd.add_argument("--source-map-file", default=None)
    run_official_cmd.add_argument("--run-id", default=None)
    run_official_cmd.add_argument("--generated-at", default=None)
    run_official_cmd.add_argument("--previous", default="latest")
    run_official_cmd.add_argument("--master-artifact-id", default=None)
    run_official_cmd.add_argument("--schema", default=None)
    run_official_cmd.add_argument("--allow-candidate-mapping", action="store_true")
    run_official_cmd.add_argument("--overwrite", action="store_true")
    run_official_cmd.add_argument("--limit", type=int, default=None)

    serve_cmd = sub.add_parser("serve", help="Serve the local API and web UI")
    serve_cmd.add_argument("--store-dir", default=str(DEFAULT_STORE_DIR))
    serve_cmd.add_argument("--web-dir", default="apps/web")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8765)
    serve_cmd.add_argument("--site-url", default=None)

    rss_cmd = sub.add_parser("rss", help="Emit RSS 2.0 XML for stored ChangeEvents")
    rss_cmd.add_argument("--store-dir", default=str(DEFAULT_STORE_DIR))
    rss_cmd.add_argument("--site-url", default="http://127.0.0.1:8765")
    rss_cmd.add_argument("--title", default="Chitan Watch Changes")
    rss_cmd.add_argument("--description", default="地単公費マスターの検知済み変更イベント")
    rss_cmd.add_argument("--max-items", type=int, default=50)

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

    if args.command == "build-manifest":
        manifest = build_manifest_from_specs(args.source_id, load_specs(args.spec_json), generated_at=args.generated_at)
        print(json.dumps(manifest, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "evaluate-run":
        current = load_manifest(args.current_manifest)
        previous = load_manifest(args.previous_manifest) if args.previous_manifest else None
        master_diff = None
        if args.master_old_source or args.master_new_source:
            if not args.master_old_source or not args.master_new_source:
                parser.error("evaluate-run requires both --master-old-source and --master-new-source when attaching master diff")
            master_diff = build_master_diff_attachment(
                args.master_old_source,
                args.master_new_source,
                schema_path=args.schema or DEFAULT_SCHEMA_PATH,
                allow_candidate_mapping=args.allow_candidate_mapping,
            )
        run = evaluate_run(current, previous=previous, master_diff=master_diff)
        print(json.dumps(run, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "run-local":
        result = execute_local_run(
            load_specs(args.spec_json),
            store_dir=args.store_dir,
            source_id=args.source_id,
            run_id=args.run_id,
            generated_at=args.generated_at,
            previous=args.previous,
            master_artifact_id=args.master_artifact_id,
            schema_path=args.schema or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
            overwrite=args.overwrite,
        )
        print(json.dumps(result, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "run-official-local":
        allowed_domains = tuple(args.allowed_domains or DEFAULT_ALLOWED_DOMAINS)
        artifact_types = tuple(ArtifactType(value) for value in (args.artifact_types or ())) or DEFAULT_ARTIFACT_TYPES
        result = execute_live_local_run(
            args.seed_url,
            store_dir=args.store_dir,
            source_id=args.source_id,
            allowed_domains=allowed_domains,
            artifact_types=artifact_types,
            seed_html_file=args.seed_html_file,
            source_map_file=args.source_map_file,
            run_id=args.run_id,
            generated_at=args.generated_at,
            previous=args.previous,
            master_artifact_id=args.master_artifact_id,
            schema_path=args.schema or DEFAULT_SCHEMA_PATH,
            allow_candidate_mapping=args.allow_candidate_mapping,
            overwrite=args.overwrite,
            limit=args.limit,
        )
        print(json.dumps(result, default=encode, ensure_ascii=False, indent=2))
        return 0

    if args.command == "serve":
        import sys

        sys.argv = ["chitan-watch-api", "--store-dir", args.store_dir, "--web-dir", args.web_dir, "--host", args.host, "--port", str(args.port)]
        if args.site_url:
            sys.argv.extend(["--site-url", args.site_url])
        return api_main()

    if args.command == "rss":
        xml = rss_xml_from_store_path(
            args.store_dir,
            options=RssFeedOptions(title=args.title, description=args.description, site_url=args.site_url, max_items=args.max_items),
        )
        print(xml, end="")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
