from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .models import ChangeBundle, RawChange


def build_change_bundle(master_changes: tuple[RawChange, ...], source_ids: tuple[str, ...] = ("ssk-chitan",), errors: tuple[str, ...] = ()) -> ChangeBundle:
    return ChangeBundle(
        run_id=f"run_{uuid4().hex}",
        detected_at=datetime.now(timezone.utc).isoformat(),
        source_ids=source_ids,
        master_changes=master_changes,
        errors=errors,
    )
