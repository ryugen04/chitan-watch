from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from chitan_watch.api import build_api_payload
from chitan_watch.change_events import build_change_event_bundle
from chitan_watch.live_crawl import execute_live_local_run
from chitan_watch.local_store import LocalRunStore, execute_local_run
from chitan_watch.models import ArtifactType, CrawlerRunStatus
from chitan_watch.run_state import load_specs

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = FIXTURES.parent.parent
SEED_URL = "https://www.ssk.or.jp/seikyushiharai/titansys/index.html"


class ProductSliceTest(unittest.TestCase):
    def test_change_events_from_master_diff(self):
        old_manifest_specs = load_specs(FIXTURES / "local_run_spec_old.json")
        current_manifest_specs = load_specs(FIXTURES / "local_run_spec_new.json")
        # Build a compact run directly from a real local run result for stable event generation.
        with tempfile.TemporaryDirectory() as tmpdir:
            first = execute_local_run(old_manifest_specs, store_dir=tmpdir, run_id="run-old", previous="none", master_artifact_id="art_master_csv", allow_candidate_mapping=True)
            second = execute_local_run(current_manifest_specs, store_dir=tmpdir, run_id="run-new", previous="latest", master_artifact_id="art_master_csv", allow_candidate_mapping=True)
        bundle = build_change_event_bundle("run-new", second.evaluation)
        self.assertGreaterEqual(len(bundle.events), 1)
        self.assertTrue(any(event.program["public_funding_number"] == "80130001" for event in bundle.events))
        self.assertTrue(any(evidence.type == "master_field_diff" for event in bundle.events for evidence in event.evidence))
        interpreted = next(event for event in bundle.events if event.interpretation.generated_by == "deterministic")
        self.assertTrue(interpreted.interpretation.headline)
        self.assertTrue(interpreted.interpretation.summary)
        self.assertGreaterEqual(len(interpreted.interpretation.likely_impact), 1)
        self.assertIn("公式ソース", interpreted.interpretation.recommended_action)

    def test_fixture_backed_live_local_run_discovers_and_persists_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = execute_live_local_run(
                SEED_URL,
                store_dir=tmpdir,
                seed_html_file=FIXTURES / "ssk_hub.html",
                source_map_file=FIXTURES / "live_source_map_old.json",
                artifact_types=(ArtifactType.MASTER_CSV,),
                run_id="live-old",
                generated_at="2026-08-09T00:00:00+00:00",
                previous="none",
                master_artifact_id=None,
                allow_candidate_mapping=True,
            )
            second = execute_live_local_run(
                SEED_URL,
                store_dir=tmpdir,
                seed_html_file=FIXTURES / "ssk_hub.html",
                source_map_file=FIXTURES / "live_source_map_new.json",
                artifact_types=(ArtifactType.MASTER_CSV,),
                run_id="live-new",
                generated_at="2026-08-09T00:05:00+00:00",
                previous="latest",
                master_artifact_id=None,
                allow_candidate_mapping=True,
            )
            store = LocalRunStore(tmpdir)
            events = store.load_run_change_events_json("live-new")
            event_path_exists = Path(second.change_events_path).exists()
        self.assertEqual("live-old", second.previous_run_id)
        self.assertEqual("SUCCESS_CHANGED", second.evaluation.status)
        self.assertTrue(event_path_exists)
        self.assertGreaterEqual(len(events["events"]), 1)
        self.assertEqual("live-new", events["run_id"])
        self.assertGreaterEqual(first.change_event_count, 1)

    def test_api_payloads_expose_runs_changes_and_source_health(self):
        specs_old = load_specs(FIXTURES / "local_run_spec_old.json")
        specs_new = load_specs(FIXTURES / "local_run_spec_new.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            execute_local_run(specs_old, store_dir=tmpdir, run_id="run-old", previous="none", master_artifact_id="art_master_csv", allow_candidate_mapping=True)
            execute_local_run(specs_new, store_dir=tmpdir, run_id="run-new", previous="latest", master_artifact_id="art_master_csv", allow_candidate_mapping=True)
            store = LocalRunStore(tmpdir)
            runs_status, runs_body, _ = build_api_payload("/api/runs", store)
            changes_status, changes_body, _ = build_api_payload("/api/changes", store)
            health_status, health_body, _ = build_api_payload("/api/source-health", store)
        self.assertEqual(200, runs_status)
        self.assertEqual(200, changes_status)
        self.assertEqual(200, health_status)
        self.assertEqual("run-new", json.loads(runs_body)["runs"][0]["run_id"])
        changes = json.loads(changes_body)["changes"]
        self.assertGreaterEqual(len(changes), 1)
        self.assertIn("interpretation", changes[0])
        self.assertIn("recommended_action", changes[0]["interpretation"])
        self.assertEqual("deterministic", changes[0]["interpretation"]["generated_by"])
        self.assertEqual("run-new", json.loads(health_body)["latest_run_id"])

    def test_run_official_local_cli_smoke(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chitan_watch.cli",
                    "run-official-local",
                    SEED_URL,
                    "--store-dir",
                    tmpdir,
                    "--seed-html-file",
                    "tests/fixtures/ssk_hub.html",
                    "--source-map-file",
                    "tests/fixtures/live_source_map_old.json",
                    "--artifact-type",
                    "master_csv",
                    "--run-id",
                    "cli-live",
                    "--generated-at",
                    "2026-08-09T00:00:00+00:00",
                    "--previous",
                    "none",
                    "--allow-candidate-mapping",
                ],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
        payload = json.loads(result.stdout)
        self.assertEqual("cli-live", payload["run_id"])
        self.assertTrue(payload["change_events_path"].endswith("change-events.json"))
        self.assertGreaterEqual(payload["change_event_count"], 1)

    def test_web_app_contains_api_fallback_and_product_routes(self):
        app_js = (ROOT / "apps/web/app.js").read_text(encoding="utf-8")
        self.assertIn('/api/changes', app_js)
        self.assertIn('Fixture fallback', app_js)
        self.assertIn('function interpretation(change)', app_js)
        self.assertIn('推奨対応:', app_js)
        self.assertIn('解釈', app_js)
        self.assertIn('renderGuide', app_js)
        self.assertIn('通知の読み方や確認順', app_js)
        self.assertIn('確度や再通知の読み方', app_js)
        self.assertIn('全体像', app_js)
        self.assertIn('画面の構造', app_js)
        self.assertIn('外部 LLM に判断を任せていません', app_js)
        self.assertIn('更新の価値観', app_js)
        self.assertIn('再通知と実変更', app_js)
        self.assertIn('renderSources', app_js)
        self.assertIn('change-detail', app_js)


if __name__ == "__main__":
    unittest.main()
