"""Positive live opportunities and durable notification acknowledgements."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .models import Assessment, utcnow
from .notifications import suppression_keys
from .sources import bounded_read
from .storage import Store


def has_positive_economics(a: Assessment) -> bool:
    return a.economic_profit is not None and a.economic_profit > 0 and a.candidate.availability == "active"


def write_report(path: Path, report: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def morning_report(store: Store, detail_refresh_minutes: int = 120) -> dict:
    run = store.latest_scrape()
    if not run or run["state"] not in {"ok", "partial"}:
        raise ValueError("Morgenrapport krever en fullført FINN-innhenting")
    started = datetime.fromisoformat(run["started_at"])
    cutoff = started - timedelta(minutes=detail_refresh_minutes)
    metadata, suppressed = store.live_items(), suppression_keys(store)
    state_file = store.path.parent / "morning-notifications.json"
    previous = json.loads(bounded_read(state_file)) if state_file.exists() else {}
    opportunities, new, entities = [], [], set()
    assessments = sorted(store.assessments(), key=lambda a: a.economic_profit or Decimal(0), reverse=True)
    for a in assessments:
        c, meta = a.candidate, metadata.get(a.candidate_key, {})
        if (
            not has_positive_economics(a)
            or c.demo
            or c.source != "finn_public"
            or a.candidate_key in suppressed
            or a.evaluated_at < started
            or not meta.get("seen_at")
            or datetime.fromisoformat(meta["seen_at"]) < started
            or meta.get("last_error")
            or not meta.get("detail_checked_at")
            or datetime.fromisoformat(meta["detail_checked_at"]) < cutoff
            or c.entity_id in entities
        ):
            continue
        entities.add(c.entity_id)
        row = {
            "candidate_key": a.candidate_key,
            "entity_id": c.entity_id,
            "title": c.title,
            "url": c.url,
            "price": str(c.price),
            "resale_low": str(a.resale_low),
            "resale_high": str(a.resale_high),
            "cash_gain": str(a.cash_gain),
            "economic_profit": str(a.economic_profit),
            "grade": a.grade,
            "confidence": a.confidence,
            "controls": a.controls,
            "reference_count": len(a.references),
            "evaluated_at": a.evaluated_at.isoformat(),
        }
        opportunities.append(row)
        old = previous.get(c.entity_id)
        # Repeat only after a lower asking price raises profit by at least NOK 250.
        if old is None or (
            c.price < Decimal(old["price"]) and a.economic_profit >= Decimal(old["economic_profit"]) + 250
        ):
            new.append(row)
    return {
        "generated_at": utcnow().isoformat(),
        "scrape_run_id": run["id"],
        "scrape_started_at": run["started_at"],
        "scrape_state": run["state"],
        "candidates_fetched": run["report"].get("candidates", 0),
        "errors": run["report"].get("errors", []),
        "opportunities": opportunities,
        "new_opportunities": new,
    }


def acknowledge_report(directory: Path):
    """Called by the scheduled chat only when it is reporting these opportunities."""
    report = json.loads(bounded_read(directory / "morning-report.json"))
    state_file = directory / "morning-notifications.json"
    previous = json.loads(bounded_read(state_file)) if state_file.exists() else {}
    for row in report["new_opportunities"]:
        previous[row["entity_id"]] = {
            "price": row["price"],
            "economic_profit": row["economic_profit"],
            "reported_at": utcnow().isoformat(),
        }
    write_report(state_file, previous)
