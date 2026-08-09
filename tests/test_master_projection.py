from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from chitan_watch.api import build_api_payload
from chitan_watch.local_store import LocalRunStore, execute_local_run
from chitan_watch.master_projection import build_master_diffs_payload, build_master_versions_payload
from chitan_watch.run_state import load_specs

FIXTURES = Path(__file__).parent / "fixtures"


class MasterProjectionTest(unittest.TestCase):
    def build_store(self, store_dir: str) -> LocalRunStore:
        execute_local_run(
            load_specs(FIXTURES / "local_run_spec_old.json"),
            store_dir=store_dir,
            run_id="run-old",
            generated_at="2026-08-09T00:00:00+00:00",
            previous="none",
            master_artifact_id="art_master_csv",
            allow_candidate_mapping=True,
        )
        execute_local_run(
            load_specs(FIXTURES / "local_run_spec_new.json"),
            store_dir=store_dir,
            run_id="run-new",
            generated_at="2026-08-09T00:05:00+00:00",
            previous="latest",
            master_artifact_id="art_master_csv",
            allow_candidate_mapping=True,
        )
        return LocalRunStore(store_dir)

    def test_master_versions_payload_exposes_csv_versions_without_local_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(tmpdir)
            payload = build_master_versions_payload(store)
        self.assertEqual(1, payload["contract_version"])
        self.assertFalse(payload["arbitrary_comparison_supported"])
        self.assertEqual("adjacent_observed_versions", payload["comparison_scope"])
        self.assertEqual(2, payload["version_count"])
        latest = payload["versions"][0]
        self.assertIn("run-new:art_master_csv", latest["version_id"])
        self.assertTrue(latest["content_version_id"].startswith("sha256:"))
        self.assertEqual("parsed", latest["parser_status"])
        self.assertEqual("csv_mapping_candidate_requires_review", latest["mapping_status"])
        self.assertTrue(latest["mapping_review_required"])
        self.assertGreaterEqual(latest["row_count"], 1)
        self.assertGreaterEqual(len(latest["sample_rows"]), 1)
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(tmpdir, encoded)
        self.assertNotIn("payloads/", encoded)

    def test_master_diffs_payload_exposes_adjacent_diff_and_detail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(tmpdir)
            index, details = build_master_diffs_payload(store)
        self.assertEqual(1, index["contract_version"])
        self.assertFalse(index["arbitrary_comparison_supported"])
        self.assertEqual("adjacent_observed_versions", index["comparison_scope"])
        self.assertEqual(1, index["diff_count"])
        summary = index["diffs"][0]
        self.assertEqual("run-new", summary["run_id"])
        self.assertEqual("run-old", summary["old_run_id"])
        self.assertEqual("run-old:art_master_csv", summary["old_version_id"])
        self.assertEqual("run-new:art_master_csv", summary["new_version_id"])
        self.assertIn("static/master-diffs/", summary["detail_url"])
        self.assertGreaterEqual(summary["summary"]["modified_row_count"], 1)
        self.assertGreaterEqual(len(summary["top_changed_fields"]), 1)
        detail = details[summary["diff_id"]]
        self.assertEqual(summary["diff_id"], detail["diff_id"])
        self.assertGreaterEqual(detail["pagination"]["total_change_count"], 1)
        self.assertGreaterEqual(len(detail["changes"]), 1)
        row = detail["changes"][0]
        self.assertIn("row_change_id", row)
        self.assertIn("changed_fields", row)
        self.assertIn("related_change_event_ids", row)
        encoded = json.dumps(detail, ensure_ascii=False)
        self.assertNotIn(tmpdir, encoded)
        self.assertNotIn("payloads/", encoded)

    def test_master_api_routes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(tmpdir)
            versions_status, versions_body, _ = build_api_payload("/api/master/versions", store)
            diffs_status, diffs_body, _ = build_api_payload("/api/master/diffs", store)
            diff_id = json.loads(diffs_body)["diffs"][0]["diff_id"]
            detail_status, detail_body, _ = build_api_payload(f"/api/master/diffs/{diff_id}", store)
        self.assertEqual(200, versions_status)
        self.assertEqual(200, diffs_status)
        self.assertEqual(200, detail_status)
        self.assertEqual(2, json.loads(versions_body)["version_count"])
        self.assertEqual(diff_id, json.loads(detail_body)["diff"]["diff_id"])


if __name__ == "__main__":
    unittest.main()
