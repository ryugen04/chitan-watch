from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from enum import Enum

from .diff import diff_master_records
from .events import build_change_bundle
from .parser import parse_master_csv_file


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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
