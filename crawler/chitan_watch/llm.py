from __future__ import annotations

from typing import Protocol

from .models import ChangeBundle


class LLMProvider(Protocol):
    """Boundary for post-detection interpretation only."""

    def analyze_change_bundle(self, bundle: ChangeBundle) -> dict:
        """Return validated structured output for ChangeEvent candidates."""

    def research_change(self, event_candidate: dict) -> dict:
        """Find additional official evidence after deterministic detection."""

    def generate_report(self, event: dict) -> str:
        """Generate a human-readable report with fact/inference separation."""


class DisabledLLMProvider:
    def analyze_change_bundle(self, bundle: ChangeBundle) -> dict:
        return {"events": [], "needs_review": True, "review_reason": "LLM_PROVIDER_DISABLED"}

    def research_change(self, event_candidate: dict) -> dict:
        return {"evidence": [], "needs_review": True, "review_reason": "LLM_PROVIDER_DISABLED"}

    def generate_report(self, event: dict) -> str:
        return "LLM provider is disabled. Deterministic evidence is still available."
