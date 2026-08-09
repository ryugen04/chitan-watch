from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

from chitan_watch.api import build_api_payload
from chitan_watch.local_store import LocalRunStore, execute_local_run
from chitan_watch.rss import RssFeedOptions, rss_xml_from_events, rss_xml_from_store
from chitan_watch.run_state import load_specs

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = FIXTURES.parent.parent


class RssTest(unittest.TestCase):
    def make_store(self, tmpdir: str) -> LocalRunStore:
        execute_local_run(
            load_specs(FIXTURES / "local_run_spec_old.json"),
            store_dir=tmpdir,
            run_id="rss-old",
            generated_at="2026-08-09T00:00:00+00:00",
            previous="none",
            master_artifact_id="art_master_csv",
            allow_candidate_mapping=True,
        )
        execute_local_run(
            load_specs(FIXTURES / "local_run_spec_new.json"),
            store_dir=tmpdir,
            run_id="rss-new",
            generated_at="2026-08-09T00:05:00+00:00",
            previous="latest",
            master_artifact_id="art_master_csv",
            allow_candidate_mapping=True,
        )
        return LocalRunStore(tmpdir)

    def test_rss_xml_from_events_is_parseable_and_escaped(self):
        xml = rss_xml_from_events(
            [
                {
                    "id": "chg-test",
                    "severity": "HIGH",
                    "summary": "A < B & C",
                    "detected_at": "2026-08-09T00:05:00+00:00",
                    "program": {"name": "制度 <test>"},
                    "jurisdiction": {"prefecture_code": "13", "municipality_code": "131016"},
                    "change_categories": ["master-row-modified"],
                    "vendor_impacts": ["master-import"],
                    "evidence": [{"type": "master_field_diff", "field": "item_1", "before": "A", "after": "B", "evidence_level": "CONFIRMED"}],
                    "interpretation": {
                        "headline": "13-131016 の制度 <test> が変更されています",
                        "summary": "制度名の変更を検知しました。",
                        "likely_impact": ["マスター更新確認が必要です。"],
                        "recommended_action": "公式ソースを確認してください。",
                        "confidence": "CONFIRMED",
                        "evidence_level": "CONFIRMED",
                        "generated_by": "deterministic",
                        "needs_review": False,
                    },
                }
            ],
            options=RssFeedOptions(site_url="https://example.test/chitan"),
        )
        root = ET.fromstring(xml)
        self.assertEqual("rss", root.tag)
        channel = root.find("channel")
        self.assertEqual("Chitan Watch Changes", channel.findtext("title"))
        item = channel.find("item")
        self.assertIn("13-131016 の制度 <test> が変更されています", item.findtext("title"))
        self.assertIn("https://example.test/chitan/#change-detail/chg-test", item.findtext("link"))
        description = item.findtext("description") or ""
        self.assertIn("制度名の変更を検知しました。", description)
        self.assertIn("想定影響: マスター更新確認が必要です。", description)
        self.assertIn("推奨対応: 公式ソースを確認してください。", description)
        self.assertIn("対象: 制度 <test>", description)
        self.assertIn("重要度: 高", description)
        self.assertIn("検知日時: 2026-08-09 09:05 JST", description)
        self.assertIn("分類: マスター行の変更", description)
        self.assertIn("詳細: https://example.test/chitan/#change-detail/chg-test", description)
        self.assertIn("通知の見方: https://example.test/chitan/#guide", description)
        self.assertNotIn("master_field_diff", description)
        self.assertNotIn("A -> B", description)

    def test_rss_xml_from_store_contains_change_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            xml = rss_xml_from_store(store, options=RssFeedOptions(site_url="https://example.test"))
        root = ET.fromstring(xml)
        items = root.findall("./channel/item")
        self.assertGreaterEqual(len(items), 1)
        categories = [category.text for item in items for category in item.findall("category")]
        self.assertIn("severity:MEDIUM", categories)

    def test_api_rss_endpoint_returns_rss_content_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            status, body, content_type = build_api_payload("/rss.xml", store, site_url="https://example.test")
        self.assertEqual(200, status)
        self.assertEqual("application/rss+xml; charset=utf-8", content_type)
        root = ET.fromstring(body)
        self.assertEqual("rss", root.tag)

    def test_cli_rss_smoke(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        with tempfile.TemporaryDirectory() as tmpdir:
            self.make_store(tmpdir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chitan_watch.cli",
                    "rss",
                    "--store-dir",
                    tmpdir,
                    "--site-url",
                    "https://example.test",
                    "--max-items",
                    "5",
                ],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
        self.assertTrue(result.stdout.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
        root = ET.fromstring(result.stdout)
        self.assertEqual("rss", root.tag)

    def test_web_advertises_rss_auto_discovery(self):
        html = (ROOT / "apps/web/index.html").read_text(encoding="utf-8")
        self.assertIn('rel="alternate"', html)
        self.assertIn('type="application/rss+xml"', html)
        self.assertIn('href="/rss.xml"', html)


if __name__ == "__main__":
    unittest.main()
