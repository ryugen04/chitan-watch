from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

from chitan_watch.local_store import execute_local_run
from chitan_watch.run_state import load_specs
from chitan_watch.static_export import export_static_site

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = FIXTURES.parent.parent


class StaticExportTest(unittest.TestCase):
    def build_store(self, store_dir: str) -> None:
        execute_local_run(
            load_specs(FIXTURES / "local_run_spec_old.json"),
            store_dir=store_dir,
            run_id="static-old",
            generated_at="2026-08-09T00:00:00+00:00",
            previous="none",
            master_artifact_id="art_master_csv",
            allow_candidate_mapping=True,
        )
        execute_local_run(
            load_specs(FIXTURES / "local_run_spec_new.json"),
            store_dir=store_dir,
            run_id="static-new",
            generated_at="2026-08-09T00:05:00+00:00",
            previous="latest",
            master_artifact_id="art_master_csv",
            allow_candidate_mapping=True,
        )

    def test_export_static_site_writes_web_json_and_rss(self):
        with tempfile.TemporaryDirectory() as store_dir, tempfile.TemporaryDirectory() as output_dir:
            self.build_store(store_dir)
            result = export_static_site(
                store_dir=store_dir,
                output_dir=output_dir,
                web_dir=ROOT / "apps/web",
                site_url="https://example.test/chitan-watch",
                max_rss_items=10,
            )
            output = Path(output_dir)
            self.assertEqual(output_dir, result.output_dir)
            self.assertIn("index.html", result.files)
            self.assertIn("rss.xml", result.files)
            self.assertIn("static/changes.json", result.files)
            self.assertTrue((output / "app.js").exists())
            self.assertTrue((output / "styles.css").exists())
            self.assertIn('href="#guide"', (output / "index.html").read_text(encoding="utf-8"))
            root = ET.fromstring((output / "rss.xml").read_text(encoding="utf-8"))
            self.assertEqual("rss", root.tag)
            self.assertGreaterEqual(len(root.findall("./channel/item")), 1)
            changes = json.loads((output / "static/changes.json").read_text(encoding="utf-8"))
            runs = json.loads((output / "static/runs.json").read_text(encoding="utf-8"))
            source_health = json.loads((output / "static/source-health.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(changes["changes"]), 1)
            self.assertEqual("static-new", runs["runs"][0]["run_id"])
            self.assertEqual("static-new", source_health["latest_run_id"])


    def test_export_static_site_can_replay_latest_real_rss_item(self):
        with tempfile.TemporaryDirectory() as store_dir, tempfile.TemporaryDirectory() as output_dir:
            self.build_store(store_dir)
            export_static_site(
                store_dir=store_dir,
                output_dir=output_dir,
                web_dir=ROOT / "apps/web",
                site_url="https://example.test/chitan-watch",
                max_rss_items=10,
                replay_latest_rss_item=True,
                rss_replay_nonce="manual-001",
                rss_replay_detected_at="2026-08-09T01:00:00+00:00",
            )
            root = ET.fromstring((Path(output_dir) / "rss.xml").read_text(encoding="utf-8"))
            items = root.findall("./channel/item")
            self.assertGreaterEqual(len(items), 2)
            replay = next(item for item in items if item.findtext("guid", "").endswith(":replay:manual-001"))
            original_guid = replay.findtext("guid").removesuffix(":replay:manual-001")
            original = next(item for item in items if item.findtext("guid") == original_guid)
            description = replay.findtext("description") or ""
            self.assertIn("【再通知】", replay.findtext("title"))
            self.assertEqual(original.findtext("link"), replay.findtext("link"))
            self.assertIn("これは通知動作確認のための再通知です。", description)
            self.assertIn("新しい変更を検知した通知ではありません。", description)
            self.assertIn("対象:", description)
            self.assertIn("重要度: ", description)
            self.assertIn("詳細: https://example.test/chitan-watch/#change-detail/", description)
            self.assertIn("背景知識と通知の見方: https://example.test/chitan-watch/#guide", description)
            self.assertNotIn("artifact_snapshot", description)
            self.assertNotIn("Manual delivery replay", description)
            self.assertNotIn("->", description)
            self.assertIn("manual-replay", [node.text for node in replay.findall("category")])

    def test_web_app_references_static_json_fallback(self):
        app_js = (ROOT / "apps/web/app.js").read_text(encoding="utf-8")
        self.assertIn("static/runs.json", app_js)
        self.assertIn("static/changes.json", app_js)
        self.assertIn("Static export", app_js)
        self.assertIn("renderGuide", app_js)
        self.assertIn("まず見るページ", app_js)
        self.assertIn("地単公費マスターの対象", app_js)
        self.assertIn("償還払い制度はこのマスターには含まれません", app_js)
        self.assertIn("公開 CSV をそのまま本番反映するのではなく", app_js)


if __name__ == "__main__":
    unittest.main()
