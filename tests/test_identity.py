from pathlib import Path
import unittest

from chitan_watch.identity import validate_record_identities
from chitan_watch.positional_master import parse_positional_csv_source

FIXTURES = Path(__file__).parent / "fixtures"


class IdentityValidationTest(unittest.TestCase):
    def test_validates_unique_identity(self):
        _schema, records = parse_positional_csv_source(FIXTURES / "master_positional_94.csv", allow_candidate_mapping=True)
        summary = validate_record_identities(records)
        self.assertEqual(2, summary.record_count)
        self.assertEqual(2, summary.unique_identity_count)
        self.assertFalse(summary.has_duplicates)
        self.assertEqual(0, summary.blank_counts_by_item["3"])
        self.assertEqual(2, summary.full_row_unique_count)
        self.assertIn("with_validity", summary.profile_results)

    def test_reports_duplicate_identity(self):
        _schema, records = parse_positional_csv_source(FIXTURES / "master_positional_94.csv", allow_candidate_mapping=True)
        summary = validate_record_identities(records + (records[0],))
        self.assertTrue(summary.has_duplicates)
        self.assertEqual(1, summary.duplicate_identity_count)
        self.assertEqual(2, summary.duplicate_row_count)
        self.assertEqual(("13", "131016", "80130001", "1"), summary.sample_duplicate_identities[0])
        self.assertEqual(1, summary.full_row_duplicate_count)


if __name__ == "__main__":
    unittest.main()
