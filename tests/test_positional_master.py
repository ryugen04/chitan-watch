from pathlib import Path
import unittest

from chitan_watch.positional_master import (
    DEFAULT_SCHEMA_PATH,
    MappingReviewRequired,
    MasterSchemaBreak,
    load_positional_schema,
    parse_positional_csv_source,
    summarize_parse,
)

FIXTURES = Path(__file__).parent / "fixtures"


class PositionalMasterTest(unittest.TestCase):
    def test_refuses_candidate_mapping_by_default(self):
        schema = load_positional_schema(DEFAULT_SCHEMA_PATH)
        self.assertFalse(schema.is_production_approved)
        with self.assertRaises(MappingReviewRequired):
            parse_positional_csv_source(FIXTURES / "master_positional_94.csv")

    def test_parses_with_explicit_candidate_allowance(self):
        schema, records = parse_positional_csv_source(FIXTURES / "master_positional_94.csv", allow_candidate_mapping=True)
        self.assertEqual(94, schema.csv_column_count)
        self.assertEqual(2, len(records))
        self.assertEqual(("13", "131016", "80130001", "1"), records[0].identity)
        self.assertEqual("20260401", records[0].value_for_item("10"))
        summary = summarize_parse("fixture", schema, records)
        self.assertEqual(2, summary.record_count)
        self.assertEqual(("3", "4", "8", "9"), summary.identity_item_numbers)

    def test_column_mismatch_is_schema_break(self):
        with self.assertRaises(MasterSchemaBreak):
            parse_positional_csv_source(FIXTURES / "master_positional_bad_columns.csv", allow_candidate_mapping=True)


if __name__ == "__main__":
    unittest.main()
