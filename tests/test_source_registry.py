from __future__ import annotations

import unittest
from pathlib import Path

from chitan_watch.discovery import _safe_charset
from chitan_watch.models import ArtifactType
from chitan_watch.source_registry import _included, load_source_registry, registry_specs
from chitan_watch.live_crawl import load_source_map

FIXTURES = Path(__file__).parent / "fixtures"


class SourceRegistryTest(unittest.TestCase):
    def test_safe_charset_accepts_windows_31j(self):
        self.assertEqual("cp932", _safe_charset("Windows-31J"))

    def test_include_filter_does_not_treat_empty_url_keywords_as_match_all(self):
        self.assertFalse(_included("ホーム", "https://www.ssk.or.jp/", ("地単公費マスター確定事業一覧",), ()))
        self.assertTrue(_included("地単公費マスター確定事業一覧", "https://www.ssk.or.jp/file.csv", ("地単公費マスター確定事業一覧",), ()))

    def test_default_registry_declares_confirmed_master_watch_scope(self):
        registry = load_source_registry()
        entry_ids = {entry.id for entry in registry.entries}
        self.assertIn("ssk-titansys-latest-master-data", entry_ids)
        self.assertIn("ssk-titansys-registration-guidance", entry_ids)
        self.assertIn("mhlw-chitan-policy-page", entry_ids)
        self.assertIn("mhlw-chitan-policy-materials", entry_ids)
        self.assertIn("shinryohoshu-seido-master", entry_ids)
        self.assertIn("ssk-top-news", entry_ids)
        self.assertIn("sapporo-child-medical-subsidy-context", entry_ids)
        self.assertIn("yokohama-child-medical-subsidy-context", entry_ids)
        self.assertIn("sumida-child-medical-subsidy-context", entry_ids)
        self.assertFalse(any("pmh" in entry.id for entry in registry.entries))
        municipality_entries = [entry for entry in registry.entries if entry.source_layer == "municipality-policy-context"]
        self.assertEqual(3, len(municipality_entries))
        self.assertTrue(all(entry.notify_policy == "important_only" for entry in municipality_entries))
        self.assertTrue(all(entry.monitor_mode == "semantic_context_diff" for entry in municipality_entries))
        data_entry = next(entry for entry in registry.entries if entry.id == "ssk-titansys-latest-master-data")
        self.assertIn(ArtifactType.MASTER_CSV, data_entry.artifact_types)
        self.assertIn(ArtifactType.MASTER_EXCEL, data_entry.artifact_types)
        self.assertEqual("always", data_entry.notify_policy)
        self.assertEqual("required", data_entry.review_policy)
        layers = {entry.source_layer for entry in registry.entries}
        self.assertIn("master-latest-data", layers)
        self.assertIn("master-registration-operation", layers)
        self.assertIn("policy-faq", layers)
        self.assertIn("reference-portal", layers)
        self.assertIn("site-news-health", layers)
        self.assertIn("municipality-policy-context", layers)
        self.assertTrue(all(entry.source_owner for entry in registry.entries))

    def test_registry_specs_capture_official_materials_with_metadata(self):
        registry = load_source_registry()
        seed_html_by_url = {entry.seed_url: (FIXTURES / "ssk_hub.html").read_text(encoding="utf-8") for entry in registry.entries}
        specs = registry_specs(registry, source_map=load_source_map(FIXTURES / "live_source_map_old.json"), seed_html_by_url=seed_html_by_url)
        by_type = {spec.type for spec in specs}
        self.assertIn(ArtifactType.HTML, by_type)
        self.assertIn(ArtifactType.MASTER_CSV, by_type)
        self.assertIn(ArtifactType.MASTER_EXCEL, by_type)
        self.assertIn(ArtifactType.SCHEMA, by_type)
        self.assertIn(ArtifactType.FAQ, by_type)
        self.assertGreaterEqual(len(specs), 8)
        self.assertTrue(all(spec.source_group for spec in specs))
        self.assertTrue(all(spec.source_layer for spec in specs))
        self.assertTrue(all(spec.source_owner for spec in specs))
        self.assertTrue(any(spec.source_layer == "master-latest-data" for spec in specs))
        self.assertTrue(any(spec.source_layer == "master-registration-operation" for spec in specs))
        self.assertTrue(any(spec.source_layer == "policy-faq" for spec in specs))
        self.assertTrue(any(spec.source_layer == "reference-portal" for spec in specs))
        self.assertTrue(any(spec.source_layer == "municipality-policy-context" for spec in specs))
        self.assertTrue(any(spec.notify_policy == "always" for spec in specs))
        self.assertTrue(any("city." in spec.canonical_url for spec in specs))
        self.assertTrue(all(spec.notify_policy == "important_only" for spec in specs if spec.source_layer == "municipality-policy-context"))
        self.assertFalse(any("digital.go.jp" in spec.canonical_url for spec in specs))
        self.assertFalse(any("example.com" in spec.canonical_url for spec in specs))


if __name__ == "__main__":
    unittest.main()
