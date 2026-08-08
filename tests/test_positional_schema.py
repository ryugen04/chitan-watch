import json
from pathlib import Path
import unittest


SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "master" / "2026-03-30.positional.json"


class PositionalSchemaTest(unittest.TestCase):
    def test_positional_schema_records_csv_pdf_mismatch(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(94, schema["csv_column_count"])
        self.assertEqual(95, schema["pdf_candidate_count"])
        self.assertEqual("csv_mapping_candidate_requires_review", schema["mapping_status"])
        self.assertIn("CSV likely excludes new item 79", schema["mapping_blocker"])
        self.assertEqual(95, len(schema["fields"]))
        self.assertEqual(94, len(schema["csv_fields"]))
        self.assertEqual("78", schema["csv_fields"][-1]["new_item_number"])
        self.assertEqual("79", schema["excluded_from_csv_candidates"][0]["new_item_number"])

    def test_candidate_fields_have_required_metadata(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        first = schema["fields"][0]
        self.assertEqual(1, first["candidate_position"])
        self.assertEqual("1", first["new_item_number"])
        self.assertEqual("事業名 正式名称", first["item_name"])
        self.assertEqual("candidate_from_pdf_text", first["mapping_status"])


if __name__ == "__main__":
    unittest.main()
