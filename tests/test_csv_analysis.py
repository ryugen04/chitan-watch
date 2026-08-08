import unittest

from chitan_watch.csv_analysis import analyze_csv_bytes, decode_csv_bytes, detect_delimiter


class CsvAnalysisTest(unittest.TestCase):
    def test_analyzes_utf8_csv_with_header(self):
        content = "prefecture_code,municipality_code,program_name\n13,131016,こども医療費助成\n14,141003,ひとり親医療費助成\n".encode("utf-8")
        analysis = analyze_csv_bytes("fixture.csv", content)
        self.assertEqual("utf-8-sig", analysis.encoding)
        self.assertEqual(",", analysis.delimiter)
        self.assertTrue(analysis.has_header)
        self.assertEqual(3, analysis.column_count)
        self.assertEqual(("prefecture_code", "municipality_code", "program_name"), analysis.headers)
        self.assertEqual(2, analysis.record_count)
        self.assertEqual(0, analysis.inconsistent_row_count)

    def test_detects_tab_delimiter(self):
        self.assertEqual("\t", detect_delimiter("a\tb\tc\n1\t2\t3\n"))

    def test_decodes_cp932_fallback(self):
        encoding, text = decode_csv_bytes("制度名\nこども\n".encode("cp932"))
        self.assertEqual("cp932", encoding)
        self.assertIn("制度名", text)

    def test_counts_inconsistent_rows(self):
        content = b"a,b,c\n1,2,3\n4,5\n"
        analysis = analyze_csv_bytes("fixture.csv", content)
        self.assertEqual(1, analysis.inconsistent_row_count)


if __name__ == "__main__":
    unittest.main()
