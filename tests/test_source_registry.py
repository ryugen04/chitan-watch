from __future__ import annotations

import unittest
from pathlib import Path

from chitan_watch.models import ArtifactType
from chitan_watch.source_registry import load_source_registry, registry_specs
from chitan_watch.live_crawl import load_source_map

FIXTURES = Path(__file__).parent / "fixtures"


class SourceRegistryTest(unittest.TestCase):
    def test_default_registry_declares_multi_source_mvp_scope(self):
        registry = load_source_registry()
        entry_ids = {entry.id for entry in registry.entries}
        self.assertIn("ssk-titansys-official-materials", entry_ids)
        self.assertIn("ssk-chitan-commissioned-status", entry_ids)
        self.assertIn("mhlw-chitan-policy-page", entry_ids)
        material_entry = next(entry for entry in registry.entries if entry.id == "ssk-titansys-official-materials")
        self.assertIn(ArtifactType.MASTER_CSV, material_entry.artifact_types)
        self.assertIn(ArtifactType.MASTER_EXCEL, material_entry.artifact_types)
        self.assertIn(ArtifactType.SCHEMA, material_entry.artifact_types)
        self.assertIn(ArtifactType.FAQ, material_entry.artifact_types)
        self.assertEqual("always", material_entry.notify_policy)

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
        self.assertTrue(any(spec.notify_policy == "always" for spec in specs))
        self.assertFalse(any("example.com" in spec.canonical_url for spec in specs))


if __name__ == "__main__":
    unittest.main()
