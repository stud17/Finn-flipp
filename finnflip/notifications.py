from __future__ import annotations

import html
import json
import os
import re
import smtplib
import ssl
from datetime import datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path

from .models import Assessment, Config, fingerprint, utcnow
from .storage import Store

TERMINAL_STATUSES = {"irrelevant", "wrong_model", "gone", "bought", "sold", "returned", "loss"}


def suppression_keys(store: Store) -> set[str]:
    latest = {f.candidate_key: f for f in store.feedback_rows()}
    blocked = {key for key, f in latest.items() if f.status in TERMINAL_STATUSES} | {
        t.candidate_key for t in store.trades()
    }
    candidates = store.observations("candidates")
    entities = {(c.demo, c.entity_id) for c in candidates if f"{c.source}:{c.id}" in blocked}
    return blocked | {f"{c.source}:{c.id}" for c in candidates if (c.demo, c.entity_id) in entities}


def reconcile_pending(store: Store, assessments: list[Assessment]):
    """Refresh pending drafts with current facts, cancel rows that no longer qualify."""
    current = {a.candidate_key: a for a in assessments}
    suppressed = suppression_keys(store)
    with store.connect() as db:
        for row in db.execute("SELECT * FROM outbox WHERE state IN ('draft','failed')").fetchall():
            old = json.loads(row["assessments"])
            items = [
                current[a["candidate_key"]]
                for a in old
                if a["candidate_key"] in current
                and a["candidate_key"] not in suppressed
                and current[a["candidate_key"]].grade == row["category"]
                and current[a["candidate_key"]].candidate.price == Decimal(a["candidate"]["price"])
            ]
            if not items:
                db.execute("UPDATE outbox SET state='superseded' WHERE id=?", (row["id"],))
                continue
            subject, text, body = render_mail(items, row["category"])
            db.execute(
                "UPDATE outbox SET subject=?,text_body=?,html_body=?,assessments=? WHERE id=?",
                (subject, text, body, json.dumps([a.model_dump(mode="json") for a in items]), row["id"]),
            )


def render_mail(assessments: list[Assessment], category: str) -> tuple[str, str, str]:
    first = assessments[0]
    demo = "[DEMO]" if first.candidate.demo else ""
    if category == "A":
        subject = f"{demo}[FINN FLIPP][A][{first.score}/100] {first.candidate.title} – anslått kontantgevinst {first.cash_gain} kr"
    else:
        subject = f"{demo}[FINN FLIPP][B] Samlerapport – {len(assessments)} interessante kandidater"
    subject = re.sub(r"[\r\n]", " ", subject)
    parts = [
        "DEMO – syntetiske priser og varer; ingen faktisk annonse eller handel."
        if first.candidate.demo
        else "Muligheter til manuell kontroll. Ingen kjøpsinstruksjon."
    ]
    for a in assessments:
        c = a.candidate
        age = (
            f"{max(0, (a.evaluated_at - c.published_at).total_seconds() / 3600):.1f} timer"
            if c.published_at
            else "ukjent"
        )
        parts.append(
            "\n".join(
                [
                    f"\n{c.title} | {a.grade} | {a.score}/100 | {a.product_id}",
                    c.url,
                    f"Annonsert: {c.price} NOK. Modell: {c.product.model}; variant: {c.product.variant}; RAM/SSD: {c.product.ram_gb}/{c.product.ssd_gb}; størrelse: {c.product.size_mm}.",
                    f"Anslått videresalg: {a.resale_low}–{a.resale_high} kr. Vurderingssikkerhet: {a.confidence}.",
                    f"Kontantgevinst: {a.cash_gain} kr. Økonomisk overskudd: {a.economic_profit} kr.",
                    f"Maks kjøpspris (gevinst og ROI): {a.max_purchase} kr; økonomisk overskudd da: {a.economic_at_max_purchase} kr.",
                    f"Maks kjøpspris med positivt økonomisk overskudd: {a.max_purchase_economic} kr.",
                    f"10 % lavere videresalg: økonomisk overskudd {a.stress_profit} kr.",
                    f"Direkte kostnader: {a.costs.direct}; risikoreserve: {a.costs.risk_reserve}; timer: {a.costs.hours}.",
                    f"Annonsealder: {age}. Publisert: {c.published_at or 'ukjent'}. Mottatt: {c.received_at.isoformat()}. Vurdert: {a.evaluated_at.isoformat()}.",
                    "Hvorfor: " + " ".join(a.reasons),
                    "Kontrollpunkter: "
                    + (
                        " ".join(a.controls)
                        or "Gjenta kontroll av identitet, eierskap, funksjon og tilstand ved kjøp."
                    ),
                    "Antakelser: " + " ".join(a.assumptions),
                    f"Referanser (alder/spredning): {json.dumps(a.reference_stats, ensure_ascii=False)}",
                    *[
                        f"- {r.source}:{r.id} | {r.kind} | {r.price} kr | {r.observed_at.isoformat()} | {r.url} | {r.documentation}"
                        for r in a.references
                    ],
                    f"Konfigurasjon: {a.config_hash}; beregning: {a.calculation_version}",
                ]
            )
        )
    text = "\n\n".join(parts)
    body = "<!doctype html><html lang='nb'><meta charset='utf-8'><body><h1>FINN-flippemaskin</h1>"
    body += (
        "<pre style='white-space:pre-wrap;font-family:system-ui;line-height:1.5'>"
        + html.escape(text)
        + "</pre></body></html>"
    )
    return subject, text, body


def prepare_outbox(
    store: Store, assessments: list[Assessment], cfg: Config, at: datetime | None = None
) -> int:
    at = at or utcnow()
    count = 0
    reconcile_pending(store, assessments)
    suppressed = suppression_keys(store)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        eligible = []
        entities = set()
        for a in assessments:
            if a.grade not in {"A", "B"} or a.candidate_key in suppressed:
                continue
            entity = f"{'demo' if a.candidate.demo else 'real'}:{a.candidate.entity_id}"
            if entity in entities:
                continue
            entities.add(entity)
            last = db.execute(
                "SELECT * FROM alert_events WHERE entity_key=? ORDER BY id DESC LIMIT 1", (entity,)
            ).fetchone()
            if last:
                price_changed = Decimal(last["price"]) != a.candidate.price
                better = a.score - Decimal(last["score"]) >= cfg.mail.score_improvement or (
                    a.grade == "A" and last["grade"] != "A"
                )
                if not (price_changed or better):
                    continue
                if at - datetime.fromisoformat(last["created_at"]) < timedelta(hours=cfg.mail.cooldown_hours):
                    continue
            eligible.append((a, entity))
        groups = [[row] for row in eligible if row[0].grade == "A"]
        for demo in (False, True):
            batch = [row for row in eligible if row[0].grade == "B" and row[0].candidate.demo == demo]
            if batch:
                groups.append(batch)
        for group in groups:
            items = [a for a, _ in group]
            category = items[0].grade
            subject, text, body = render_mail(items, category)
            dedup = fingerprint(
                [
                    [(a.candidate_key, str(a.candidate.price), str(a.score), a.grade) for a in items],
                    at.isoformat(),
                ]
            )
            cursor = db.execute(
                "INSERT INTO outbox(dedup_key,category,created_at,subject,text_body,html_body,assessments) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    dedup,
                    category,
                    at.isoformat(),
                    subject,
                    text,
                    body,
                    json.dumps([a.model_dump(mode="json") for a in items]),
                ),
            )
            for a, entity in group:
                db.execute(
                    "INSERT INTO alert_events(entity_key,candidate_key,created_at,outbox_id,price,score,grade) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        entity,
                        a.candidate_key,
                        at.isoformat(),
                        cursor.lastrowid,
                        str(a.candidate.price),
                        str(a.score),
                        a.grade,
                    ),
                )
            count += 1
    return count


def export_drafts(store: Store, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    for row in store.outbox():
        stem = directory / f"{row['id']:04d}-{row['category']}"
        stem.with_suffix(".txt").write_text(row["subject"] + "\n\n" + row["text_body"], encoding="utf-8")
        stem.with_suffix(".html").write_text(row["html_body"], encoding="utf-8")


def send_outbox(store: Store, cfg: Config) -> dict:
    if cfg.mail.mode != "SMTP":
        raise PermissionError("DRY_RUN: ingen e-post sendes. Aktiver SMTP eksplisitt i konfigurasjonen.")
    mail = cfg.mail
    address = re.compile(r"^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$")
    if not mail.smtp_host or not all(
        address.fullmatch(x or "") for x in (mail.owner_address, mail.from_address)
    ):
        raise ValueError("SMTP krever vert, avsender og angitt eieradresse")
    # Re-evaluate with current references and config immediately before sending.
    from .service import run_analysis

    reconcile_pending(store, run_analysis(store, cfg))
    result = {"sent": 0, "failed": 0}
    for row in store.outbox()[::-1]:
        if row["state"] not in {"draft", "failed"}:
            continue
        # Never send synthetic examples through a real transport.
        if any(a["candidate"]["demo"] for a in json.loads(row["assessments"])):
            continue
        with store.connect() as db:
            claimed = db.execute(
                "UPDATE outbox SET state='sending',attempts=attempts+1,error=NULL "
                "WHERE id=? AND state IN ('draft','failed')",
                (row["id"],),
            ).rowcount
        if not claimed:
            continue
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = row["subject"], mail.from_address, mail.owner_address
        msg["Message-ID"] = f"<{row['dedup_key']}@finnflip.local>"
        msg.set_content(row["text_body"])
        msg.add_alternative(row["html_body"], subtype="html")
        state, error = "failed", None
        delivering = False
        try:
            with smtplib.SMTP(mail.smtp_host, mail.smtp_port, timeout=20) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                username, password = (
                    os.environ.get("FINNFLIP_SMTP_USER"),
                    os.environ.get("FINNFLIP_SMTP_PASSWORD"),
                )
                if username and password:
                    smtp.login(username, password)
                delivering = True
                smtp.send_message(msg, to_addrs=[mail.owner_address])
            state = "sent"
            result["sent"] += 1
        except (OSError, smtplib.SMTPException) as exc:
            # SMTP error strings may contain server responses or account details: don't persist them.
            state = "uncertain" if delivering else "failed"
            error = type(exc).__name__
            result["failed"] += 1
        with store.connect() as db:
            db.execute("UPDATE outbox SET state=?,error=? WHERE id=?", (state, error, row["id"]))
    return result
