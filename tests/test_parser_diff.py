from pathlib import Path
import unittest

from chitan_watch.diff import diff_master_records
from chitan_watch.models import MatchingStatus, RawChangeType
from chitan_watch.parser import parse_master_csv_file, validate_header

FIXTURES = Path(__file__).parent / "fixtures"


class ParserDiffTest(unittest.TestCase):
    def test_parse_master_csv_fixture(self):
        validation, records = parse_master_csv_file(FIXTURES / "master_old.csv")
        self.assertTrue(validation.ok)
        self.assertEqual(2, len(records))
        self.assertEqual(("13", "131016", "80130001", "1"), records[0].identity)

    def test_missing_required_column_is_schema_break(self):
        validation = validate_header(["prefecture_code", "municipality_code"])
        self.assertFalse(validation.ok)
        self.assertEqual("SCHEMA_BREAK", validation.status)
        self.assertIn("public_funding_number", validation.missing_columns)

    def test_diff_added_and_modified_records(self):
        _, old_records = parse_master_csv_file(FIXTURES / "master_old.csv")
        _, new_records = parse_master_csv_file(FIXTURES / "master_new.csv")
        changes = diff_master_records(old_records, new_records)
        change_types = [change.type for change in changes]
        self.assertIn(RawChangeType.RECORD_MODIFIED, change_types)
        self.assertIn(RawChangeType.RECORD_ADDED, change_types)
        modified = next(change for change in changes if change.type == RawChangeType.RECORD_MODIFIED)
        self.assertEqual(MatchingStatus.MATCHED, modified.matching_status)
        self.assertEqual({"before": "18", "after": "22"}, modified.fields["age_upper"])

    def test_duplicate_identity_routes_to_ambiguous(self):
        _, old_records = parse_master_csv_file(FIXTURES / "master_old.csv")
        duplicated = old_records + (old_records[0],)
        changes = diff_master_records(duplicated, old_records)
        self.assertEqual(MatchingStatus.AMBIGUOUS, changes[0].matching_status)


if __name__ == "__main__":
    unittest.main()
