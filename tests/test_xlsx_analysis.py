from io import BytesIO
import unittest
import zipfile

from chitan_watch.xlsx_analysis import analyze_xlsx_bytes, column_to_number, parse_dimension


def fixture_xlsx() -> bytes:
    out = BytesIO()
    workbook_xml = '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Master" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    shared_xml = '<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>事業名</t></si><si><t>都道府県番号</t></si><si><t>こども医療費助成</t></si></sst>'
    sheet_xml = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:C2"/><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1"><v>42</v></c></row><row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>13</v></c><c r="C2"><v>1</v></c></row></sheetData></worksheet>'
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        zf.writestr("xl/sharedStrings.xml", shared_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return out.getvalue()


class XlsxAnalysisTest(unittest.TestCase):
    def test_column_to_number(self):
        self.assertEqual(1, column_to_number("A"))
        self.assertEqual(26, column_to_number("Z"))
        self.assertEqual(27, column_to_number("AA"))

    def test_parse_dimension(self):
        self.assertEqual((2, 3), parse_dimension("A1:C2"))

    def test_analyze_xlsx_bytes(self):
        analysis = analyze_xlsx_bytes("fixture.xlsx", fixture_xlsx())
        self.assertEqual(1, analysis.sheet_count)
        sheet = analysis.sheets[0]
        self.assertEqual("Master", sheet.name)
        self.assertEqual(2, sheet.max_row)
        self.assertEqual(3, sheet.max_column)
        self.assertEqual(("事業名", "都道府県番号", "42"), sheet.first_rows[0])
        self.assertEqual(("C2", "1"), sheet.tail_cells[-1])


if __name__ == "__main__":
    unittest.main()
