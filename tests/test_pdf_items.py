import unittest

from chitan_watch.pdf_items import parse_item_candidates


class PdfItemsTest(unittest.TestCase):
    def test_parse_item_candidates(self):
        text = """
項番(旧) 項番(新) 項目名１ 項目名２ タ型 桁数 必須 設定値 項目の説明
    1     1 事業名        正式名称                          日本語     100 ○      事業名の正式名称を入力
          18           保険種別    社保                      文字列       1 ○         以下、いずれかを選択して入力
        22_2                   所得区分名称（独自               文字列       30 △        前項目でA0-ZZを選択した場合
"""
        extraction = parse_item_candidates(text, source_pdf="fixture.pdf")
        self.assertEqual(3, extraction.candidate_count)
        self.assertEqual("1", extraction.candidates[0].old_item_number)
        self.assertEqual("1", extraction.candidates[0].new_item_number)
        self.assertEqual("事業名 正式名称", extraction.candidates[0].item_name)
        self.assertEqual("18", extraction.candidates[1].new_item_number)
        self.assertEqual("22_2", extraction.candidates[2].new_item_number)

    def test_duplicate_new_numbers_are_detected(self):
        text = """
    1     1 事業名        正式名称                          日本語     100 ○      text
    2     1            略称                            日本語      12        text
"""
        extraction = parse_item_candidates(text)
        self.assertTrue(extraction.has_duplicate_new_numbers)


if __name__ == "__main__":
    unittest.main()
