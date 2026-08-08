from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from chitan_watch.models import ArtifactType, CrawlerRunStatus
from chitan_watch.run_state import (
    ArtifactSourceSpec,
    build_manifest_from_specs,
    build_master_diff_attachment,
    evaluate_run,
    load_manifest,
)

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = FIXTURES.parent.parent


def encode(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(value)


class RunStateTest(unittest.TestCase):
    def spec(self, artifact_id: str, path: str | None = None, error: str | None = None):
        return ArtifactSourceSpec(
            id=artifact_id,
            type=ArtifactType.MASTER_CSV,
            title=f"fixture {artifact_id}",
            canonical_url=f"https://www.ssk.or.jp/fixture/{artifact_id}.csv",
            path=path,
            error=error,
        )

    def manifest(self, specs):
        return build_manifest_from_specs("ssk-chitan", specs, generated_at="2026-08-09T00:00:00+00:00")

    def test_evaluates_no_change(self):
        previous = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        current = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        run = evaluate_run(current, previous=previous, evaluated_at="2026-08-09T00:01:00+00:00")
        self.assertEqual(CrawlerRunStatus.SUCCESS_NO_CHANGE, run.status)
        self.assertEqual(0, run.changed_artifact_count)
        self.assertEqual("unchanged", run.artifact_changes[0].state)

    def test_evaluates_changed_artifact(self):
        previous = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        current = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_new.txt"))])
        run = evaluate_run(current, previous=previous)
        self.assertEqual(CrawlerRunStatus.SUCCESS_CHANGED, run.status)
        self.assertEqual(1, run.changed_artifact_count)
        self.assertEqual("changed", run.artifact_changes[0].state)

    def test_evaluates_added_and_removed_artifacts(self):
        previous = self.manifest([
            self.spec("art_removed", str(FIXTURES / "artifact_note_old.txt")),
            self.spec("art_same", str(FIXTURES / "artifact_note_old.txt")),
        ])
        current = self.manifest([
            self.spec("art_added", str(FIXTURES / "artifact_note_new.txt")),
            self.spec("art_same", str(FIXTURES / "artifact_note_old.txt")),
        ])
        run = evaluate_run(current, previous=previous)
        states = {change.artifact_id: change.state for change in run.artifact_changes}
        self.assertEqual(CrawlerRunStatus.SUCCESS_CHANGED, run.status)
        self.assertEqual("added", states["art_added"])
        self.assertEqual("removed", states["art_removed"])
        self.assertEqual("unchanged", states["art_same"])

    def test_evaluates_partial_failure(self):
        previous = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        current = self.manifest([
            self.spec("art_master", str(FIXTURES / "artifact_note_old.txt")),
            self.spec("art_failed", error="HTTP 500"),
        ])
        run = evaluate_run(current, previous=previous)
        self.assertEqual(CrawlerRunStatus.PARTIAL_FAILURE, run.status)
        self.assertEqual(1, run.failed_artifact_count)
        self.assertIn("HTTP 500", run.errors)

    def test_evaluates_total_failure(self):
        current = self.manifest([self.spec("art_failed", error="timeout")])
        run = evaluate_run(current)
        self.assertEqual(CrawlerRunStatus.FAILED, run.status)
        self.assertEqual(1, run.failed_artifact_count)

    def test_attaches_master_semantic_diff(self):
        previous = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        current = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        attachment = build_master_diff_attachment(
            str(FIXTURES / "master_positional_diff_old.csv"),
            str(FIXTURES / "master_positional_diff_new.csv"),
            allow_candidate_mapping=True,
        )
        run = evaluate_run(current, previous=previous, master_diff=attachment)
        self.assertEqual("ok", attachment.status)
        self.assertEqual(CrawlerRunStatus.SUCCESS_CHANGED, run.status)
        self.assertEqual(1, run.master_diff.diff.modified_row_count)
        self.assertEqual(1, run.master_diff.diff.added_row_count)

    def test_schema_break_takes_status_precedence(self):
        current = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        attachment = build_master_diff_attachment(
            str(FIXTURES / "master_positional_diff_old.csv"),
            str(FIXTURES / "master_positional_bad_columns.csv"),
            allow_candidate_mapping=True,
        )
        run = evaluate_run(current, master_diff=attachment)
        self.assertEqual("schema_break", attachment.status)
        self.assertEqual(CrawlerRunStatus.SCHEMA_BREAK, run.status)
        self.assertEqual(1, run.schema_break_count)

    def test_manifest_round_trip_and_cli_smoke(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "chitan_watch.cli",
                "build-manifest",
                "tests/fixtures/manifest_spec_old.json",
                "--generated-at",
                "2026-08-09T00:00:00+00:00",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["manifest_version"])
        self.assertEqual("SUCCESS", "SUCCESS")
        self.assertEqual("art_master_csv", payload["artifacts"][0]["artifact"]["id"])
        with tempfile.TemporaryDirectory() as tmpdir:
            current_path = Path(tmpdir) / "current.json"
            previous_path = Path(tmpdir) / "previous.json"
            current_path.write_text(result.stdout, encoding="utf-8")
            previous_path.write_text(result.stdout, encoding="utf-8")
            run_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chitan_watch.cli",
                    "evaluate-run",
                    str(current_path),
                    "--previous-manifest",
                    str(previous_path),
                ],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
        run_payload = json.loads(run_result.stdout)
        self.assertEqual("SUCCESS_NO_CHANGE", run_payload["status"])
        self.assertEqual(0, run_payload["changed_artifact_count"])

    def test_load_manifest_from_json(self):
        manifest = self.manifest([self.spec("art_master", str(FIXTURES / "artifact_note_old.txt"))])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.json"
            path.write_text(json.dumps(manifest, default=encode), encoding="utf-8")
            loaded = load_manifest(path)
        self.assertEqual(manifest.source_id, loaded.source_id)
        self.assertEqual(manifest.artifacts[0].snapshot.sha256, loaded.artifacts[0].snapshot.sha256)


if __name__ == "__main__":
    unittest.main()
