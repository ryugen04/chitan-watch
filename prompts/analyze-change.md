# Analyze ChangeBundle

You receive a deterministic ChangeBundle. Do not invent RawChanges, identities, dates, or source URLs.

Return structured JSON with:

- events
- summary
- effective_from, or null when unresolved
- severity_reasoning
- vendor_impacts
- evidence with evidence_level
- needs_review
- review_reason

Separate CONFIRMED, CORROBORATED, INFERRED, and UNRESOLVED statements.
