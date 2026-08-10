from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chitan_watch.llm import (
    DisabledLLMProvider,
    GeminiLLMProvider,
    build_llm_export_payloads,
    load_llm_provider_from_env,
    validate_llm_interpretation,
)
from chitan_watch.local_store import LocalRunStore, execute_local_run
from chitan_watch.run_state import load_specs

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class RecordingOpener:
    def __init__(self, output):
        self.output = output
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse({"candidates": [{"content": {"parts": [{"text": json.dumps(self.output, ensure_ascii=False)}]}}]})


class LLMTest(unittest.TestCase):
    def build_store(self, store_dir: str) -> LocalRunStore:
        execute_local_run(load_specs(FIXTURES / "local_run_spec_old.json"), store_dir=store_dir, run_id="old", previous="none", master_artifact_id="art_master_csv", allow_candidate_mapping=True)
        execute_local_run(load_specs(FIXTURES / "local_run_spec_new.json"), store_dir=store_dir, run_id="new", previous="latest", master_artifact_id="art_master_csv", allow_candidate_mapping=True)
        return LocalRunStore(store_dir)

    def test_disabled_provider_selected_without_key(self):
        provider = load_llm_provider_from_env({})
        self.assertIsInstance(provider, DisabledLLMProvider)

    def test_validate_llm_interpretation_rejects_bad_output(self):
        with self.assertRaises(ValueError):
            validate_llm_interpretation({"summary_for_humans": "missing fields"})

    def test_validate_llm_interpretation_rejects_uncited_key_point(self):
        with self.assertRaises(ValueError):
            validate_llm_interpretation({
                "summary_for_humans": "CSV差分の確認が必要です。",
                "key_points": [{"text": "根拠なしです。", "evidence_ids": []}],
                "fact_basis": [{"text": "diff", "evidence_ids": ["d1"]}],
                "inferences": [{"text": "推論", "evidence_ids": ["d1"]}],
                "uncertainties": [],
                "recommended_review": {"text": "確認", "evidence_ids": ["d1"]},
                "related_context_to_check": [{"text": "資料", "evidence_ids": ["d1"]}],
                "risk_label": "needs_review",
            })

    def test_gemini_provider_parses_structured_response_without_exposing_key(self):
        output = {
            "summary_for_humans": "CSV差分の確認が必要です。",
            "key_points": [{"text": "制度名が変更されています。", "evidence_ids": ["d1"]}],
            "fact_basis": [{"text": "deterministic CSV diff", "evidence_ids": ["d1"]}],
            "inferences": [{"text": "表示名変更の可能性があります。", "evidence_ids": ["d1"]}],
            "uncertainties": ["運用影響は未確認です。"],
            "recommended_review": {"text": "公式CSVと変更手順を確認してください。", "evidence_ids": ["d1"]},
            "related_context_to_check": [{"text": "支払基金資料", "evidence_ids": ["d1"]}],
            "risk_label": "medium",
        }
        opener = RecordingOpener(output)
        provider = GeminiLLMProvider(api_key="secret-key", opener=opener, retry_count=0)
        result = provider.interpret_master_diff({"diff_id": "d1", "summary": {}, "changes": []})
        self.assertEqual("CSV差分の確認が必要です。", result["summary_for_humans"])
        request, timeout = opener.requests[0]
        self.assertEqual(20, timeout)
        self.assertIn("generateContent", request.full_url)
        self.assertIn("gemini-3.6-flash", request.full_url)
        self.assertNotIn("secret-key", request.full_url)
        body = json.loads(request.data.decode("utf-8"))
        response_format = body["generationConfig"]["responseFormat"]["text"]
        self.assertEqual("application/json", response_format["mimeType"])
        self.assertIn("schema", response_format)

    def test_llm_export_payloads_disabled_without_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(tmpdir)
            status, interpretations = build_llm_export_payloads(store, enable_llm=False)
        self.assertFalse(status["enabled"])
        self.assertEqual("disabled", status["status"])
        self.assertEqual([], interpretations["interpretations"])

    def test_llm_export_selects_changed_diffs_before_applying_cap(self):
        class MockProvider:
            model = "mock-gemini"

            def __init__(self):
                self.seen = []

            def interpret_master_diff(self, diff_detail):
                self.seen.append(diff_detail["diff_id"])
                return {
                    "summary_for_humans": f"{diff_detail['diff_id']} の差分です。",
                    "key_points": [{"text": "変更があります。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "fact_basis": [{"text": "変更ありdiff", "evidence_ids": [diff_detail["diff_id"]]}],
                    "inferences": [{"text": "確認対象です。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "uncertainties": [],
                    "recommended_review": {"text": "CSV差分を確認してください。", "evidence_ids": [diff_detail["diff_id"]]},
                    "related_context_to_check": [{"text": "公式CSV", "evidence_ids": [diff_detail["new_source_url"]]}],
                    "risk_label": "needs_review",
                }

        provider = MockProvider()
        details = {
            "unchanged-1": {"diff_id": "unchanged-1", "has_changes": False, "new_source_url": "https://example.test/1.csv", "summary": {}, "changes": []},
            "unchanged-2": {"diff_id": "unchanged-2", "has_changes": False, "new_source_url": "https://example.test/2.csv", "summary": {}, "changes": []},
            "changed-1": {"diff_id": "changed-1", "has_changes": True, "new_source_url": "https://example.test/3.csv", "summary": {"modified_row_count": 1}, "changes": []},
        }
        with patch("chitan_watch.llm.build_master_diffs_payload", return_value=({"diffs": []}, details)):
            status, interpretations = build_llm_export_payloads(object(), enable_llm=True, provider=provider, max_diffs=1)
        self.assertEqual("success", status["status"])
        self.assertEqual(1, status["request_count"])
        self.assertEqual(["changed-1"], provider.seen)
        self.assertEqual("changed-1", interpretations["interpretations"][0]["target_id"])

    def test_llm_export_interprets_latest_no_change_diff_when_no_changed_diff_exists(self):
        class MockProvider:
            model = "mock-gemini"

            def __init__(self):
                self.seen = []

            def interpret_master_diff(self, diff_detail):
                self.seen.append(diff_detail["diff_id"])
                return {
                    "summary_for_humans": "最新観測ではCSV内容差分はありません。",
                    "key_points": [{"text": "行差分は0件です。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "fact_basis": [{"text": "決定論的diffで変更なしです。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "inferences": [{"text": "今回のRSSでは新規の制度差分通知は不要です。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "uncertainties": [],
                    "recommended_review": {"text": "基準日と公式CSV URLだけ確認してください。", "evidence_ids": [diff_detail["new_source_url"]]},
                    "related_context_to_check": [{"text": "公式CSV", "evidence_ids": [diff_detail["new_source_url"]]}],
                    "risk_label": "low",
                }

        provider = MockProvider()
        details = {
            "unchanged-latest": {"diff_id": "unchanged-latest", "has_changes": False, "new_source_url": "https://example.test/latest.csv", "summary": {"modified_row_count": 0}, "changes": []},
            "unchanged-older": {"diff_id": "unchanged-older", "has_changes": False, "new_source_url": "https://example.test/older.csv", "summary": {"modified_row_count": 0}, "changes": []},
        }
        with patch("chitan_watch.llm.build_master_diffs_payload", return_value=({"diffs": []}, details)):
            status, interpretations = build_llm_export_payloads(object(), enable_llm=True, provider=provider, max_diffs=5)
        self.assertEqual("success", status["status"])
        self.assertEqual(1, status["request_count"])
        self.assertEqual(["unchanged-latest"], provider.seen)
        self.assertEqual("low", interpretations["interpretations"][0]["output"]["risk_label"])

    def test_llm_export_payloads_with_mock_provider(self):
        class MockProvider:
            model = "mock-gemini"

            def interpret_master_diff(self, diff_detail):
                return {
                    "summary_for_humans": f"{diff_detail['diff_id']} の差分です。",
                    "key_points": [{"text": "追加・削除・変更があります。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "fact_basis": [{"text": diff_detail["diff_id"], "evidence_ids": [diff_detail["diff_id"]]}],
                    "inferences": [{"text": "確認対象です。", "evidence_ids": [diff_detail["diff_id"]]}],
                    "uncertainties": ["影響範囲は未確認です。"],
                    "recommended_review": {"text": "CSV差分を確認してください。", "evidence_ids": [diff_detail["diff_id"]]},
                    "related_context_to_check": [{"text": "新旧CSVの公式URL", "evidence_ids": [diff_detail.get("new_source_url") or diff_detail["diff_id"]]}],
                    "risk_label": "needs_review",
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(tmpdir)
            status, interpretations = build_llm_export_payloads(store, enable_llm=True, provider=MockProvider())
        self.assertTrue(status["enabled"])
        self.assertEqual("success", status["status"])
        self.assertEqual(1, status["request_count"])
        self.assertEqual(1, len(interpretations["interpretations"]))
        self.assertEqual("success", interpretations["interpretations"][0]["status"])


if __name__ == "__main__":
    unittest.main()
