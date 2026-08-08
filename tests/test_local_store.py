from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from chitan_watch.local_store import LocalRunStore, execute_local_run
from chitan_watch.models import CrawlerRunStatus
from chitan_watch.run_state import load_specs

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = FIXTURES.parent.parent


class LocalRunStoreTest(unittest.TestCase):
    def test_first_run_writes_directory_payloads_and_latest_pointer(self):
        specs = load_specs(FIXTURES / "local_run_spec_old.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = execute_local_run(
                specs,
                store_dir=tmpdir,
                run_id="run-old",
                generated_at="2026-08-09T00:00:00+00:00",
                previous="none",
                master_artifact_id="art_master_csv",
                allow_candidate_mapping=True,
            )
            store = LocalRunStore(tmpdir)
            self.assertEqual("run-old", store.latest_run_id("ssk-chitan"))
            self.assertIsNone(result.previous_run_id)
            self.assertEqual(CrawlerRunStatus.SUCCESS_CHANGED, result.evaluation.status)
            self.assertTrue(Path(result.manifest_path).exists())
            self.assertTrue(Path(result.evaluation_path).exists())
            self.assertTrue(Path(result.source_spec_path).exists())
            self.assertGreaterEqual(len(result.payload_paths), 2)
            for payload_path in result.payload_paths:
                self.assertTrue(Path(payload_path).exists())
            manifest = store.load_run_manifest("run-old")
            storage_keys = [record.snapshot.storage_key for record in manifest.artifacts if record.snapshot]
            self.assertIn("payloads/art_master_csv.csv", storage_keys)

    def test_second_run_compares_against_latest_and_attaches_master_diff(self):
        old_specs = load_specs(FIXTURES / "local_run_spec_old.json")
        new_specs = load_specs(FIXTURES / "local_run_spec_new.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            execute_local_run(
                old_specs,
                store_dir=tmpdir,
                run_id="run-old",
                generated_at="2026-08-09T00:00:00+00:00",
                previous="none",
                master_artifact_id="art_master_csv",
                allow_candidate_mapping=True,
            )
            result = execute_local_run(
                new_specs,
                store_dir=tmpdir,
                run_id="run-new",
                generated_at="2026-08-09T00:05:00+00:00",
                previous="latest",
                master_artifact_id="art_master_csv",
                allow_candidate_mapping=True,
            )
            self.assertEqual("run-old", result.previous_run_id)
            self.assertEqual(CrawlerRunStatus.SUCCESS_CHANGED, result.evaluation.status)
            self.assertEqual(2, result.evaluation.changed_artifact_count)
            self.assertIsNotNone(result.evaluation.master_diff)
            self.assertEqual("ok", result.evaluation.master_diff.status)
            self.assertEqual(1, result.evaluation.master_diff.diff.modified_row_count)
            self.assertEqual(1, result.evaluation.master_diff.diff.added_row_count)
            self.assertTrue(Path(result.master_diff_path).exists())
            self.assertEqual("run-new", LocalRunStore(tmpdir).latest_run_id("ssk-chitan"))

    def test_explicit_previous_run_id_is_supported(self):
        old_specs = load_specs(FIXTURES / "local_run_spec_old.json")
        new_specs = load_specs(FIXTURES / "local_run_spec_new.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            execute_local_run(old_specs, store_dir=tmpdir, run_id="baseline", previous="none")
            result = execute_local_run(new_specs, store_dir=tmpdir, run_id="candidate", previous="baseline")
            self.assertEqual("baseline", result.previous_run_id)
            self.assertEqual(CrawlerRunStatus.SUCCESS_CHANGED, result.evaluation.status)

    def test_refuses_to_overwrite_existing_run_directory_by_default(self):
        specs = load_specs(FIXTURES / "manifest_spec_old.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            execute_local_run(specs, store_dir=tmpdir, run_id="same", previous="none")
            with self.assertRaises(FileExistsError):
                execute_local_run(specs, store_dir=tmpdir, run_id="same", previous="none")

    def test_cli_run_local_smoke_first_and_second_run(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        with tempfile.TemporaryDirectory() as tmpdir:
            first = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chitan_watch.cli",
                    "run-local",
                    "tests/fixtures/local_run_spec_old.json",
                    "--store-dir",
                    tmpdir,
                    "--run-id",
                    "run-old",
                    "--generated-at",
                    "2026-08-09T00:00:00+00:00",
                    "--previous",
                    "none",
                    "--master-artifact-id",
                    "art_master_csv",
                    "--allow-candidate-mapping",
                ],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
            first_payload = json.loads(first.stdout)
            self.assertEqual("run-old", first_payload["run_id"])
            self.assertIsNone(first_payload["previous_run_id"])
            second = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chitan_watch.cli",
                    "run-local",
                    "tests/fixtures/local_run_spec_new.json",
                    "--store-dir",
                    tmpdir,
                    "--run-id",
                    "run-new",
                    "--generated-at",
                    "2026-08-09T00:05:00+00:00",
                    "--previous",
                    "latest",
                    "--master-artifact-id",
                    "art_master_csv",
                    "--allow-candidate-mapping",
                ],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
            second_payload = json.loads(second.stdout)
        self.assertEqual("run-old", second_payload["previous_run_id"])
        self.assertEqual("SUCCESS_CHANGED", second_payload["evaluation"]["status"])
        self.assertEqual("ok", second_payload["evaluation"]["master_diff"]["status"])


if __name__ == "__main__":
    unittest.main()
