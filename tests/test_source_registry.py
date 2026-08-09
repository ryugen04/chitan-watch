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
        self.assertFalse(_included("ホーム", "https://www.digital.go.jp/", ("制度関連マスタ",), ()))
        self.assertTrue(_included("PMH制度関連マスタ", "https://www.digital.go.jp/assets/master.xlsx", ("制度関連マスタ",), ()))

    def test_default_registry_declares_multi_source_mvp_scope(self):
        registry = load_source_registry()
        entry_ids = {entry.id for entry in registry.entries}
        self.assertIn("ssk-titansys-official-materials", entry_ids)
        self.assertIn("ssk-chitan-commissioned-status", entry_ids)
        self.assertIn("mhlw-chitan-policy-page", entry_ids)
        self.assertIn("digital-agency-pmh-hub-page", entry_ids)
        self.assertIn("shinryohoshu-seido-master", entry_ids)
        self.assertIn("sapporo-child-medical-subsidy", entry_ids)
        material_entry = next(entry for entry in registry.entries if entry.id == "ssk-titansys-official-materials")
        self.assertIn(ArtifactType.MASTER_CSV, material_entry.artifact_types)
        self.assertIn(ArtifactType.MASTER_EXCEL, material_entry.artifact_types)
        self.assertIn(ArtifactType.SCHEMA, material_entry.artifact_types)
        self.assertIn(ArtifactType.FAQ, material_entry.artifact_types)
        self.assertEqual("always", material_entry.notify_policy)
        layers = {entry.source_layer for entry in registry.entries}
        self.assertIn("master-publication", layers)
        self.assertIn("pmh-online-qualification", layers)
        self.assertIn("claim-processing", layers)
        self.assertIn("municipality-policy", layers)
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
        self.assertIn(ArtifactType.MHLW_DOCUMENT, by_type)
        self.assertGreaterEqual(len(specs), 8)
        self.assertTrue(all(spec.source_group for spec in specs))
        self.assertTrue(all(spec.source_layer for spec in specs))
        self.assertTrue(all(spec.source_owner for spec in specs))
        self.assertTrue(any(spec.source_layer == "pmh-online-qualification" for spec in specs))
        self.assertTrue(any(spec.source_layer == "municipality-policy" for spec in specs))
        self.assertTrue(any(spec.notify_policy == "always" for spec in specs))
        self.assertFalse(any("example.com" in spec.canonical_url for spec in specs))


if __name__ == "__main__":
    unittest.main()
