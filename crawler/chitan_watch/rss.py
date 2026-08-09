from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from xml.etree import ElementTree as ET

from .local_store import DEFAULT_STORE_DIR, LocalRunStore

DEFAULT_FEED_TITLE = "Chitan Watch Changes"
DEFAULT_FEED_DESCRIPTION = "地単公費マスターの検知済み変更イベント"
DEFAULT_SITE_URL = "http://127.0.0.1:8765"


@dataclass(frozen=True)
class RssFeedOptions:
    title: str = DEFAULT_FEED_TITLE
    description: str = DEFAULT_FEED_DESCRIPTION
    site_url: str = DEFAULT_SITE_URL
    feed_path: str = "/rss.xml"
    max_items: int = 50
    replay_latest_item: bool = False
    replay_nonce: str | None = None
    replay_detected_at: str | None = None
    replay_label: str = "Manual delivery replay"


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _rfc2822(value: str | None) -> str:
    return format_datetime(_parse_datetime(value))


def _absolute_url(site_url: str, path: str) -> str:
    return site_url.rstrip("/") + "/" + path.lstrip("/")


def _change_link(site_url: str, change_id: str) -> str:
    return _absolute_url(site_url, f"#change-detail/{quote(change_id)}")


def _text(parent: ET.Element, tag: str, value: object | None) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = "" if value is None else str(value)
    return child


def _event_sort_key(event: dict) -> tuple[str, str]:
    return (str(event.get("detected_at") or ""), str(event.get("id") or ""))


def _item_description(event: dict) -> str:
    impacts = ", ".join(event.get("vendor_impacts") or ()) or "none"
    categories = ", ".join(event.get("change_categories") or ()) or "none"
    evidence = event.get("evidence") or []
    evidence_lines = []
    for item in evidence[:5]:
        field = item.get("field") or item.get("type") or "evidence"
        before = item.get("before")
        after = item.get("after")
        level = item.get("evidence_level") or ""
        if before is not None or after is not None:
            evidence_lines.append(f"{field}: {before} -> {after} ({level})")
        else:
            evidence_lines.append(f"{field}: {item.get('description', '')} ({level})")
    replay_label = event.get("rss_replay_label")
    parts = []
    if replay_label:
        parts.append(f"<p><strong>{escape(str(replay_label))}:</strong> Existing real detected data replayed for delivery verification.</p>")
    parts.extend([
        f"<p>{escape(str(event.get('summary') or ''))}</p>",
        f"<p><strong>Severity:</strong> {escape(str(event.get('severity') or ''))}</p>",
        f"<p><strong>Categories:</strong> {escape(categories)}</p>",
        f"<p><strong>Vendor impacts:</strong> {escape(impacts)}</p>",
    ])
    if evidence_lines:
        parts.append("<ul>" + "".join(f"<li>{escape(line)}</li>" for line in evidence_lines) + "</ul>")
    if event.get("review_required"):
        parts.append("<p><strong>Admin Review required.</strong></p>")
    return "".join(parts)



def _replay_latest_event(events: list[dict], options: RssFeedOptions) -> list[dict]:
    if not options.replay_latest_item or not events:
        return events
    latest = sorted(events, key=_event_sort_key, reverse=True)[0]
    original_id = str(latest.get("id") or "change")
    nonce = options.replay_nonce or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    replay = dict(latest)
    replay["id"] = f"{original_id}:replay:{nonce}"
    replay["rss_link_id"] = original_id
    replay["detected_at"] = options.replay_detected_at or datetime.now(timezone.utc).isoformat()
    replay["rss_replay_label"] = options.replay_label
    replay["change_categories"] = tuple(latest.get("change_categories") or ()) + ("manual-replay",)
    return [replay, *events]


def rss_xml_from_events(events: Iterable[dict], options: RssFeedOptions = RssFeedOptions()) -> str:
    event_items = _replay_latest_event([dict(event) for event in events], options)
    sorted_events = sorted(event_items, key=_event_sort_key, reverse=True)[: options.max_items]
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    _text(channel, "title", options.title)
    _text(channel, "link", options.site_url)
    _text(channel, "description", options.description)
    _text(channel, "language", "ja")
    _text(channel, "lastBuildDate", _rfc2822(sorted_events[0].get("detected_at") if sorted_events else None))
    _text(channel, "generator", "chitan-watch")
    _text(channel, "ttl", "60")

    for event in sorted_events:
        item = ET.SubElement(channel, "item")
        program = event.get("program") or {}
        jurisdiction = event.get("jurisdiction") or {}
        title = f"[{event.get('severity', 'INFO')}] {program.get('name') or '地単公費マスター'}"
        if event.get("rss_replay_label"):
            title = f"{event.get('rss_replay_label')}: {title}"
        place = "-".join(part for part in (jurisdiction.get("prefecture_code"), jurisdiction.get("municipality_code")) if part)
        if place:
            title = f"{title} / {place}"
        link_id = str(event.get("rss_link_id") or event.get("id") or "change")
        link = _change_link(options.site_url, link_id)
        _text(item, "title", title)
        _text(item, "link", link)
        guid = _text(item, "guid", str(event.get("id") or link))
        guid.set("isPermaLink", "false")
        _text(item, "pubDate", _rfc2822(event.get("detected_at")))
        _text(item, "description", _item_description(event))
        _text(item, "author", "noreply@chitan-watch.local (Chitan Watch)")
        for category in event.get("change_categories") or ():
            _text(item, "category", category)
        _text(item, "category", f"severity:{event.get('severity', 'INFO')}")
        if event.get("review_required"):
            _text(item, "category", "review-required")
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ET.tostring(rss, encoding="unicode", short_empty_elements=False) + "\n"


def rss_xml_from_store(store: LocalRunStore, options: RssFeedOptions = RssFeedOptions()) -> str:
    events = []
    for run_id in reversed(store.list_run_ids()):
        bundle = store.load_run_change_events_json(run_id)
        for event in bundle.get("events", []):
            item = dict(event)
            item["run_id"] = run_id
            events.append(item)
    return rss_xml_from_events(events, options=options)


def rss_xml_from_store_path(store_dir: str | Path = DEFAULT_STORE_DIR, options: RssFeedOptions = RssFeedOptions()) -> str:
    return rss_xml_from_store(LocalRunStore(store_dir), options=options)
