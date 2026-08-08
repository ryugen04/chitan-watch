from pathlib import Path
import unittest

from chitan_watch.discovery import discover_artifacts
from chitan_watch.models import ArtifactType

FIXTURES = Path(__file__).parent / "fixtures"


class DiscoveryTest(unittest.TestCase):
    def test_discovers_allowed_domain_artifacts_with_resolved_urls(self):
        html = (FIXTURES / "ssk_hub.html").read_text(encoding="utf-8")
        artifacts = discover_artifacts(
            seed_url="https://www.ssk.or.jp/seikyushiharai/titansys/index.html",
            html=html,
            source_id="ssk-chitan",
            allowed_domains=("www.ssk.or.jp", "www.mhlw.go.jp"),
        )
        urls = [item.artifact.canonical_url for item in artifacts]
        self.assertIn("https://www.ssk.or.jp/seikyushiharai/titansys/index.files/master_20260803.csv", urls)
        self.assertIn("https://www.mhlw.go.jp/stf/newpage_67679.html", urls)
        self.assertNotIn("https://example.com/not-official.pdf", urls)

    def test_classifies_core_artifact_types(self):
        html = (FIXTURES / "ssk_hub.html").read_text(encoding="utf-8")
        artifacts = discover_artifacts(
            seed_url="https://www.ssk.or.jp/seikyushiharai/titansys/index.html",
            html=html,
            source_id="ssk-chitan",
            allowed_domains=("www.ssk.or.jp", "www.mhlw.go.jp"),
        )
        by_url = {item.artifact.canonical_url: item.artifact.type for item in artifacts}
        self.assertEqual(ArtifactType.MASTER_CSV, by_url["https://www.ssk.or.jp/seikyushiharai/titansys/index.files/master_20260803.csv"])
        self.assertEqual(ArtifactType.MASTER_EXCEL, by_url["https://www.ssk.or.jp/seikyushiharai/titansys/index.files/master_20260803.xlsx"])
        self.assertEqual(ArtifactType.SCHEMA, by_url["https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo2_20260330.pdf"])
        self.assertEqual(ArtifactType.FAQ, by_url["https://www.ssk.or.jp/seikyushiharai/titansys/index.files/faq.pdf"])
        self.assertEqual(ArtifactType.MHLW_DOCUMENT, by_url["https://www.mhlw.go.jp/stf/newpage_67679.html"])

    def test_can_filter_by_artifact_type(self):
        html = (FIXTURES / "ssk_hub.html").read_text(encoding="utf-8")
        artifacts = discover_artifacts(
            seed_url="https://www.ssk.or.jp/seikyushiharai/titansys/index.html",
            html=html,
            source_id="ssk-chitan",
            allowed_domains=("www.ssk.or.jp", "www.mhlw.go.jp"),
            artifact_types=(ArtifactType.MASTER_CSV,),
        )
        self.assertEqual(1, len(artifacts))
        self.assertEqual(ArtifactType.MASTER_CSV, artifacts[0].artifact.type)


if __name__ == "__main__":
    unittest.main()
