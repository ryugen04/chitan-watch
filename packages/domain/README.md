# Domain Package

This folder contains shared domain contracts that should remain stable across crawler, API, and Web UI implementations.

The important boundary is:

```text
Official Snapshot -> RawChange -> ChangeBundle -> ChangeEvent -> Report/Notification
```

LLM-generated data can enrich ChangeEvent and reports, but must never overwrite RawChange.
