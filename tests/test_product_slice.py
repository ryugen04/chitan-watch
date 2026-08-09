from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from chitan_watch.api import build_api_payload
from chitan_watch.change_events import build_change_event_bundle, event_in_current_notification_scope
from chitan_watch.live_crawl import execute_live_local_run, execute_registry_local_run
from chitan_watch.change_events import build_change_event_bundle, event_in_current_notification_scope
from chitan_watch.local_store import LocalRunStore, execute_local_run
from chitan_watch.models import ArtifactType, CrawlerRunStatus
from chitan_watch.run_state import ArtifactRunChange, CrawlerRunEvaluation, load_specs

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


    def test_legacy_scope_artifacts_do_not_emit_feed_events(self):
        run = CrawlerRunEvaluation(
            status=CrawlerRunStatus.SUCCESS_CHANGED,
            source_id="chitan-watch",
            evaluated_at="2026-08-09T00:05:00+00:00",
            artifact_count=1,
            changed_artifact_count=1,
            failed_artifact_count=0,
            schema_break_count=0,
            artifact_changes=(
                ArtifactRunChange(
                    artifact_id="legacy-pmh",
                    artifact_type=ArtifactType.HTML,
                    title="旧 PMH 監視ページ",
                    canonical_url="https://www.digital.go.jp/policies/health/public-medical-hub",
                    state="removed",
                    previous_sha256="old",
                    source_group="pmh-online-qualification",
                    source_layer="pmh-online-qualification",
                    source_owner="digital-agency",
                    notify_policy="important_only",
                    review_policy="conditional",
                ),
                ArtifactRunChange(
                    artifact_id="legacy-pmh-added",
                    artifact_type=ArtifactType.HTML,
                    title="旧 PMH 追加通知",
                    canonical_url="https://www.digital.go.jp/policies/health/public-medical-hub",
                    state="added",
                    current_sha256="new",
                    source_group="pmh-online-qualification",
                    source_layer="pmh-online-qualification",
                    source_owner="digital-agency",
                    notify_policy="important_only",
                    review_policy="conditional",
                ),
                ArtifactRunChange(
                    artifact_id="current-faq",
                    artifact_type=ArtifactType.FAQ,
                    title="5_FAQ",
                    canonical_url="https://www.ssk.or.jp/seikyushiharai/titansys/index.files/siryo5_FAQ_20250530.pdf",
                    state="removed",
                    previous_sha256="old",
                    source_group="master-registration-operation",
                    source_layer="master-registration-operation",
                    source_owner="ssk",
                    notify_policy="important_only",
                    review_policy="conditional",
                ),
            ),
        )
        events = build_change_event_bundle("scope-cleanup", run).events
        categories = {category for event in events for category in event.change_categories}
        self.assertEqual(1, len(events))
        self.assertEqual("5_FAQ", events[0].program["name"])
        self.assertIn("source-layer:master-registration-operation", categories)
        self.assertNotIn("source-layer:pmh-online-qualification", categories)

    def test_current_scope_filter_removes_legacy_historical_events(self):
        legacy_event = {
            "id": "legacy",
            "change_categories": ["artifact-added", "source-layer:pmh-online-qualification"],
            "source_context": {"source_layer": "pmh-online-qualification"},
        }
        current_event = {
            "id": "current",
            "change_categories": ["artifact-added", "source-layer:policy-faq"],
            "source_context": {"source_layer": "policy-faq"},
        }
        master_row_event = {"id": "master-row", "change_categories": ["master-row-modified"]}
        municipality_seed_event = {
            "id": "municipality-seed",
            "change_categories": ["artifact-added", "source-layer:municipality-policy-seed"],
            "source_context": {"source_layer": "municipality-policy-seed"},
        }
        self.assertFalse(event_in_current_notification_scope(legacy_event))
        self.assertFalse(event_in_current_notification_scope(municipality_seed_event))
        self.assertTrue(event_in_current_notification_scope(current_event))
        self.assertTrue(event_in_current_notification_scope(master_row_event))

    def test_registry_backed_run_emits_master_and_document_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            execute_registry_local_run(
                store_dir=tmpdir,
                seed_html_file=FIXTURES / "ssk_hub.html",
                source_map_file=FIXTURES / "live_source_map_old.json",
                run_id="registry-old",
                generated_at="2026-08-09T00:00:00+00:00",
                previous="none",
                source_id="chitan-watch",
                allow_candidate_mapping=True,
            )
            second = execute_registry_local_run(
                store_dir=tmpdir,
                seed_html_file=FIXTURES / "ssk_hub.html",
                source_map_file=FIXTURES / "live_source_map_new.json",
                run_id="registry-new",
                generated_at="2026-08-09T00:05:00+00:00",
                previous="latest",
                source_id="chitan-watch",
                allow_candidate_mapping=True,
            )
            store = LocalRunStore(tmpdir)
            events = store.load_run_change_events_json("registry-new")["events"]
            _status, health_body, _ = build_api_payload("/api/source-health", store)
        categories = {category for event in events for category in event.get("change_categories", [])}
        self.assertEqual("SUCCESS_CHANGED", second.evaluation.status)
        self.assertTrue(any(event["program"].get("public_funding_number") == "80130001" for event in events))
        self.assertIn("document-update", categories)
        self.assertIn("artifact-type:schema", categories)
        health = json.loads(health_body)
        self.assertIn("master-latest-data", health["source_layers"])
        self.assertIn("master-registration-operation", health["source_layers"])
        self.assertIn("policy-faq", health["source_layers"])
        self.assertIn("reference-portal", health["source_layers"])
        self.assertIn("municipality-policy-seed", health["source_layers"])
        self.assertFalse(any(source.get("source_owner") == "digital-agency" for source in health["sources"]))
        self.assertFalse(any(source.get("source_layer") == "municipality-policy" for source in health["sources"]))
        self.assertTrue(any(source.get("source_layer") == "municipality-policy-seed" and source.get("notify_policy") == "health_only" for source in health["sources"]))
        self.assertTrue(any(source.get("notify_policy") == "always" for source in health["sources"]))
        self.assertFalse(any("source-layer:municipality-policy-seed" in event.get("change_categories", []) for event in events))

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


    def test_run_official_local_cli_uses_source_registry(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "crawler"
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chitan_watch.cli",
                    "run-official-local",
                    "--source-registry",
                    "crawler/chitan_watch/source_registry.json",
                    "--store-dir",
                    tmpdir,
                    "--source-id",
                    "chitan-watch",
                    "--seed-html-file",
                    "tests/fixtures/ssk_hub.html",
                    "--source-map-file",
                    "tests/fixtures/live_source_map_old.json",
                    "--run-id",
                    "cli-registry",
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
        self.assertEqual("cli-registry", payload["run_id"])
        self.assertEqual("chitan-watch", payload["source_id"])
        self.assertGreaterEqual(payload["evaluation"]["artifact_count"], 8)

    def test_publish_workflow_uses_source_registry_not_single_csv_filter(self):
        workflow = (ROOT / ".github/workflows/publish-static.yml").read_text(encoding="utf-8")
        self.assertIn("--source-registry crawler/chitan_watch/source_registry.json", workflow)
        self.assertIn("--source-id chitan-watch", workflow)
        self.assertNotIn("--artifact-type master_csv", workflow)

    def test_web_app_contains_api_fallback_and_product_routes(self):
        app_js = (ROOT / "apps/web/app.js").read_text(encoding="utf-8")
        self.assertIn('/api/changes', app_js)
        self.assertIn('Fixture fallback', app_js)
        self.assertIn('function interpretation(change)', app_js)
        self.assertIn('推奨対応:', app_js)
        self.assertIn('解釈', app_js)
        self.assertIn('renderGuide', app_js)
        self.assertIn('公費制度、データ構造、通知の読み方', app_js)
        self.assertIn('まず見るページ', app_js)
        self.assertIn('地単公費マスターの対象', app_js)
        self.assertIn('最新データの見方', app_js)
        self.assertIn('確定事業一覧', app_js)
        self.assertIn('現在の監視範囲', app_js)
        self.assertIn('Source Registry', app_js)
        self.assertIn('情報層の分け方', app_js)
        self.assertIn('master-latest-data', app_js)
        self.assertIn('master-registration-operation', app_js)
        self.assertIn('policy-faq', app_js)
        self.assertIn('municipality-policy-seed', app_js)
        self.assertIn('Source Health にだけ出します', app_js)
        self.assertIn('償還払い制度はこのマスターには含まれません', app_js)
        self.assertIn('同値性テスト', app_js)
        self.assertIn('自治体 seed の扱い', app_js)
        self.assertIn('notify_policy', app_js)
        self.assertIn('source_layer', app_js)
        self.assertIn('source_owner', app_js)
        self.assertIn('外部 LLM に判断を任せていません', app_js)
        self.assertIn('制度カタログではありません', app_js)
        self.assertIn('説明会・FAQ', app_js)
        self.assertIn('renderSources', app_js)
        self.assertIn('change-detail', app_js)


if __name__ == "__main__":
    unittest.main()
