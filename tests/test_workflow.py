import csv
import hashlib
import io
import json
import smtplib
from datetime import timedelta
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from finnflip.engine import evaluate
from finnflip.models import Candidate, Feedback, Trade
from finnflip.notifications import prepare_outbox, render_mail, send_outbox
from finnflip.service import ROOT, comparison_csv, load_demo, run_analysis
from finnflip.sources import MAX_BYTES, DemoAdapter, LicensedFeedAdapter, LocalFileAdapter, parse_rows


def test_import_idempotency_price_history_and_reversion(store, candidates, at):
    c = candidates["attractive"]
    assert store.import_rows("candidates", [c], {}, at) == 1
    assert store.import_rows("candidates", [c], {}, at) == 0
    changed = c.model_copy(update={"price": D(2200)})
    assert store.import_rows("candidates", [changed], {}, at + timedelta(hours=1)) == 1
    assert store.import_rows("candidates", [c], {}, at + timedelta(hours=2)) == 1
    assert len(store.history("demo:attractive")) == 3
    assert store.observations("candidates", at + timedelta(minutes=90))[0].price == 2200
    assert store.observations("candidates", at - timedelta(seconds=1)) == []


def test_import_time_prevents_backdated_knowledge(store, candidates, refs, cfg, at):
    store.import_rows("candidates", [candidates["attractive"]], {}, at)
    store.import_rows("references", refs, {}, at + timedelta(hours=1))
    assert run_analysis(store, cfg, at)[0].grade == "U"
    a = run_analysis(store, cfg, at + timedelta(hours=2))[0]
    assert a.grade == "A"
    assert all(r.known_at >= at + timedelta(hours=1) for r in a.references)
    assert a.config_snapshot == cfg.model_dump(mode="json")
    assert evaluate(a.candidate, a.references, cfg, a.evaluated_at).model_dump() == a.model_dump()


def test_demo_workflow_twice_does_not_duplicate(store, cfg):
    first = load_demo(store, cfg)
    assert first == {"references": 56, "candidates": 11, "drafts": 2}
    second = load_demo(store, cfg)
    assert second == {"references": 0, "candidates": 0, "drafts": 0}
    assert len(store.outbox()) == 2
    assert {row["category"] for row in store.outbox()} == {"A", "B"}
    assert all("DEMO" in row["subject"] for row in store.outbox())


def test_alert_cooldown_price_changes_and_relisting(store, candidates, refs, cfg, at):
    a = evaluate(candidates["attractive"], refs, cfg, at)
    assert prepare_outbox(store, [a], cfg, at) == 1
    assert prepare_outbox(store, [a], cfg, at + timedelta(days=3)) == 0
    changed = a.model_copy(deep=True)
    changed.candidate.price -= 100
    assert prepare_outbox(store, [changed], cfg, at + timedelta(hours=1)) == 0
    assert prepare_outbox(store, [changed], cfg, at + timedelta(days=1)) == 1
    changed.candidate.id = "reposted"
    changed.candidate_key = "demo:reposted"
    assert prepare_outbox(store, [changed], cfg, at + timedelta(days=3)) == 0


def test_mail_escapes_html_and_unknown_publication(candidates, refs, cfg, at):
    c = candidates["attractive"].model_copy(
        update={"title": '<script>alert("x")</script>\nSubject: bad', "published_at": None}
    )
    a = evaluate(c, refs, cfg, at)
    subject, text, html = render_mail([a], "A")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "\n" not in subject
    assert "Annonsealder: ukjent" in text


def test_dry_run_and_live_placeholder_block_network(store, cfg):
    with pytest.raises(PermissionError):
        send_outbox(store, cfg)
    with pytest.raises(PermissionError):
        LicensedFeedAdapter().load("candidates")
    with pytest.raises(NotImplementedError):
        LicensedFeedAdapter(ROOT / "fake", {"enabled": True}).load("candidates")


def test_csv_json_equivalent_and_oversize_rejected():
    csv = parse_rows((ROOT / "fixtures/candidates.csv").read_bytes(), ".csv", "candidates")
    json_rows, _ = DemoAdapter(ROOT / "fixtures").load("candidates")
    assert [x.model_dump() for x in csv] == [x.model_dump() for x in json_rows]
    with pytest.raises(ValueError, match="5 MiB"):
        parse_rows(b"x" * (MAX_BYTES + 1), ".json", "candidates")


def test_real_import_requires_file_bound_rights(tmp_path, candidates, at):
    c = candidates["attractive"].model_copy(update={"demo": False})
    file, evidence, manifest = tmp_path / "data.json", tmp_path / "basis.txt", tmp_path / "rights.json"
    file.write_text(json.dumps([c.model_dump(mode="json")]))
    evidence.write_text("TEST ONLY: self-authored structured observations and permission for local analysis.")
    raw = {
        "approved_by": "Test User",
        "approved_at": at.isoformat(),
        "basis": "TEST self authored facts with local analysis permission",
        "purposes": ["analysis", "storage", "drafts"],
        "input_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        "evidence_file": "basis.txt",
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    manifest.write_text(json.dumps(raw))
    rows, _ = LocalFileAdapter(file, manifest).load("candidates")
    assert len(rows) == 1 and not rows[0].demo
    file.write_text("[]")
    with pytest.raises(ValueError, match="annen datafil"):
        LocalFileAdapter(file, manifest).load("candidates")


def test_reject_personal_fields_javascript_and_naive_times(candidates):
    raw = candidates["attractive"].model_dump(mode="json")
    for key, value in [
        ("seller_phone", "123"),
        ("url", "javascript:alert(1)"),
        ("received_at", "2026-10-19T00:00:00"),
    ]:
        with pytest.raises(ValidationError):
            Candidate.model_validate({**raw, key: value})


def test_trade_actuals_separate_from_estimates_feedback_and_inventory(store, cfg):
    load_demo(store, cfg)
    f = Feedback.model_validate_json((ROOT / "fixtures/feedback.json").read_bytes())
    store.feedback(f)
    sold = Trade.model_validate_json((ROOT / "fixtures/trade-sold.json").read_bytes())
    inventory = Trade.model_validate_json((ROOT / "fixtures/trade-inventory.json").read_bytes())
    store.save_trade(sold)
    store.save_trade(inventory)
    assert sold.result()["cash_gain"] == 3800
    assert sold.result()["economic_profit"] == 3070
    assert inventory.result()["cash_gain"] is None and inventory.result()["capital_bound"] == 980
    assert len(store.trades()) == 2
    store.save_trade(sold)
    assert len(store.trades()) == 2
    csv = comparison_csv(store)
    assert "measured_cash_gain" in csv and "3800.00" in csv
    with pytest.raises(ValueError, match="Demo"):
        store.feedback(f.model_copy(update={"demo": False}))


class FakeSMTP:
    fail_on = None
    delivered = []

    def __init__(self, *args, **kwargs):
        if self.fail_on == "connect":
            raise OSError("fake credential must not persist")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def starttls(self, **kwargs):
        pass

    def send_message(self, msg, to_addrs):
        if self.fail_on == "send":
            raise smtplib.SMTPServerDisconnected("fake credential must not persist")
        self.delivered.append(to_addrs)


@pytest.mark.parametrize("fail_on,expected", [(None, "sent"), ("connect", "failed"), ("send", "uncertain")])
def test_smtp_partial_failure_and_explicit_owner(
    store, cfg, candidates, refs, at, monkeypatch, fail_on, expected
):
    c = candidates["attractive"].model_copy(update={"demo": False})
    real_refs = [r.model_copy(update={"demo": False}) for r in refs]
    store.import_rows("candidates", [c], {}, at)
    store.import_rows("references", real_refs, {}, at)
    a = evaluate(c, real_refs, cfg, at)
    prepare_outbox(store, [a], cfg, at)
    cfg.mail.mode = "SMTP"
    cfg.mail.smtp_host = "mail.example.invalid"
    cfg.mail.owner_address = "owner@example.invalid"
    cfg.mail.from_address = "app@example.invalid"
    FakeSMTP.fail_on = fail_on
    FakeSMTP.delivered = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    send_outbox(store, cfg)
    row = store.outbox()[0]
    assert row["state"] == expected
    assert "fake credential" not in (row["error"] or "")
    if expected == "sent":
        assert FakeSMTP.delivered == [["owner@example.invalid"]]
    if expected in {"sent", "uncertain"}:
        send_outbox(store, cfg)
        assert store.outbox()[0]["attempts"] == 1


def test_pending_alert_removed_after_gone_or_downgraded(store, candidates, refs, cfg, at):
    a = evaluate(candidates["attractive"], refs, cfg, at)
    store.import_rows("candidates", [a.candidate], {}, at)
    prepare_outbox(store, [a], cfg, at)
    store.feedback(Feedback(candidate_key=a.candidate_key, status="gone", demo=True))
    assert prepare_outbox(store, [a], cfg, at + timedelta(days=2)) == 0
    assert store.outbox()[0]["state"] == "superseded"


def test_demo_never_sent_even_with_smtp_enabled(store, cfg, monkeypatch):
    load_demo(store, cfg)
    cfg.mail.mode = "SMTP"
    cfg.mail.smtp_host = "mail.example.invalid"
    cfg.mail.owner_address = "owner@example.invalid"
    cfg.mail.from_address = "app@example.invalid"

    def forbidden(*args, **kwargs):
        raise AssertionError("Ingen nettverkskontakt for demo")

    monkeypatch.setattr(smtplib, "SMTP", forbidden)
    assert send_outbox(store, cfg) == {"sent": 0, "failed": 0}


def test_baseline_comparison_has_equal_volumes_without_invented_labels(store, cfg):
    load_demo(store, cfg)
    rows = list(csv.DictReader(io.StringIO(comparison_csv(store))))
    assert sum(r["engine_matched_volume"] == "True" for r in rows) == sum(
        r["baseline_matched_volume"] == "True" for r in rows
    )
    assert all(r["usable_after_control"] == "" and r["measured_cash_gain"] == "" for r in rows)
    assert all(r["engine_rank"] == "" for r in rows if r["grade"] == "U")
