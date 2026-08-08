from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from chitan_watch.master_diff import diff_master_snapshots
from chitan_watch.master_snapshot import build_master_snapshot
from chitan_watch.models import MatchingStatus
from chitan_watch.positional_master import parse_positional_csv_source

FIXTURES = Path(__file__).parent / "fixtures"


class MasterSnapshotDiffTest(unittest.TestCase):
    def load_snapshot(self, fixture_name: str):
        schema, records = parse_positional_csv_source(FIXTURES / fixture_name, allow_candidate_mapping=True)
        return build_master_snapshot(fixture_name, schema, records)

    def test_builds_deterministic_row_fingerprints(self):
        first = self.load_snapshot("master_positional_diff_old.csv")
        second = self.load_snapshot("master_positional_diff_old.csv")
        self.assertEqual(3, first.record_count)
        self.assertEqual(3, first.unique_row_hash_count)
        self.assertEqual(first.rows[0].row_hash, second.rows[0].row_hash)
        self.assertEqual(first.rows[0].condition_fingerprint, second.rows[0].condition_fingerprint)
        self.assertEqual(("13", "131016", "80130001", "1"), first.rows[0].business_key)

    def test_reports_duplicate_business_identity_without_collapsing_rows(self):
        snapshot = self.load_snapshot("master_positional_ambiguous_old.csv")
        self.assertEqual(2, snapshot.record_count)
        self.assertEqual(1, snapshot.business_identity_count)
        self.assertEqual(1, snapshot.duplicate_business_identity_count)
        self.assertEqual(("13", "131050", "80130005", "1"), snapshot.duplicate_business_identities[0].identity)

    def test_diffs_added_removed_modified_and_unchanged_rows(self):
        old_snapshot = self.load_snapshot("master_positional_diff_old.csv")
        new_snapshot = self.load_snapshot("master_positional_diff_new.csv")
        diff = diff_master_snapshots(old_snapshot.rows, new_snapshot.rows)
        self.assertTrue(diff.has_changes)
        self.assertEqual(1, diff.unchanged_row_count)
        self.assertEqual(1, diff.added_row_count)
        self.assertEqual(1, diff.removed_row_count)
        self.assertEqual(1, diff.modified_row_count)
        self.assertEqual(0, diff.ambiguous_group_count)
        modified = next(change for change in diff.changes if change.type == "row_modified")
        self.assertEqual(MatchingStatus.MATCHED, modified.matching_status)
        self.assertEqual("こども医療費助成", modified.fields["item_1"]["before"])
        self.assertEqual("こども医療費助成 改定", modified.fields["item_1"]["after"])

    def test_routes_many_to_many_unmatched_rows_to_admin_review(self):
        old_snapshot = self.load_snapshot("master_positional_ambiguous_old.csv")
        new_snapshot = self.load_snapshot("master_positional_ambiguous_new.csv")
        diff = diff_master_snapshots(old_snapshot.rows, new_snapshot.rows)
        self.assertEqual(0, diff.modified_row_count)
        self.assertEqual(1, diff.ambiguous_group_count)
        self.assertEqual(1, len(diff.changes))
        ambiguous = diff.changes[0]
        self.assertEqual("row_ambiguous", ambiguous.type)
        self.assertEqual(MatchingStatus.AMBIGUOUS, ambiguous.matching_status)
        self.assertEqual(2, ambiguous.before_unmatched_count)
        self.assertEqual(2, ambiguous.after_unmatched_count)

    def test_cli_snapshot_master_smoke(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "chitan_watch.cli",
                "snapshot-master",
                str(FIXTURES / "master_positional_diff_old.csv"),
                "--allow-candidate-mapping",
                "--max-records",
                "1",
            ],
            cwd=FIXTURES.parent.parent,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["record_count"])
        self.assertEqual("chitan-watch-positional-row-v1", payload["row_fingerprint_algorithm"])
        self.assertEqual(1, len(payload["rows"]))

    def test_cli_diff_master_smoke(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "chitan_watch.cli",
                "diff-master",
                str(FIXTURES / "master_positional_diff_old.csv"),
                str(FIXTURES / "master_positional_diff_new.csv"),
                "--allow-candidate-mapping",
            ],
            cwd=FIXTURES.parent.parent,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["added_row_count"])
        self.assertEqual(1, payload["removed_row_count"])
        self.assertEqual(1, payload["modified_row_count"])


if __name__ == "__main__":
    unittest.main()
