from datetime import timedelta
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from finnflip.engine import canonical_url, classify, economics, evaluate, quantile, relevant_references
from finnflip.models import Candidate, Costs, money


def test_document_economics(cfg):
    costs = Costs(transport=D(400), risk_reserve=D(300), hours=D(2), overhead=D(100))
    result = economics(D(6000), D(4000), costs, cfg, D(1000))
    assert result["cash_gain"] == D(1300)
    assert result["economic_profit"] == D(600)
    assert result["roi"] == D(1300) / D(4400)
    assert result["max_purchase"] == D(4300)
    assert result["stress_profit"] == 0


@pytest.mark.parametrize(
    "resale,purchase,direct,reserve", [(6000, 4000, 400, 300), (999, 50, 123, 50), (7000, 2000, 0, 300)]
)
def test_max_price_obeys_both_limits(cfg, resale, purchase, direct, reserve):
    costs = Costs(transport=D(direct), risk_reserve=D(reserve), hours=D(0))
    min_gain = D(50)
    result = economics(D(resale), D(purchase), costs, cfg, min_gain)
    limit = result["max_purchase"]
    gain = D(resale) - limit - D(direct) - D(reserve)
    assert gain >= min_gain
    assert gain / (limit + D(direct)) >= cfg.min_roi


def test_no_feasible_price_is_not_zero(cfg):
    result = economics(D(100), D(10), Costs(transport=D(500)), cfg, D(1000))
    assert result["max_purchase"] is None
    assert result["economic_at_max_purchase"] is None
    assert result["max_purchase_economic"] is None


def test_decimal_rounding_and_zero_denominator(cfg):
    assert money(D("10.005")) == D("10.01")
    assert quantile([D(100), D(101), D(102), D(103), D(104), D(105)], D("0.25")) == D("101.25")
    with pytest.raises(ValueError, match="positivt"):
        economics(D(100), D(0), Costs(), cfg, D(0))


@pytest.mark.parametrize(
    "id_,grade",
    [
        ("attractive", "A"),
        ("cost-trap", "D"),
        ("wrong-config", "U"),
        ("insufficient", "U"),
        ("lock-risk", "B"),
        ("garmin-interesting", "B"),
        ("installments", "U"),
        ("bundle", "U"),
        ("variant-mismatch", "U"),
    ],
)
def test_required_demo_cases(candidates, refs, cfg, at, id_, grade):
    a = evaluate(candidates[id_], refs, cfg, at)
    assert a.grade == grade
    if grade == "U":
        assert a.cash_gain is None and a.score is None and a.resale_low is None


@pytest.mark.parametrize(
    "note",
    [
        "299 kr/mnd",
        "delbetaling",
        "kun lader",
        "fra 1000 kr",
        "ønskes kjøpt",
        "pakkepris",
        "bundle",
        "pakke med to klokker",
    ],
)
def test_price_words_override_unit_claim(candidates, refs, cfg, at, note):
    c = candidates["attractive"].model_copy(update={"price_note": note})
    assert evaluate(c, refs, cfg, at).status == "MANUAL_REVIEW"


@pytest.mark.parametrize("field,value", [("ram_gb", 16), ("ssd_gb", 512), ("variant", None)])
def test_matching_never_borrows_wrong_configuration(candidates, refs, cfg, at, field, value):
    c = candidates["attractive"].model_copy(deep=True)
    setattr(c.product, field, value)
    a = evaluate(c, refs[:7], cfg, at)
    assert a.grade == "U"


def test_garmin_size_mismatch(candidates, refs, cfg, at):
    c = candidates["garmin-interesting"].model_copy(deep=True)
    c.product.size_mm = 42
    assert evaluate(c, refs, cfg, at).grade == "U"


def test_url_dedup_keeps_ad_identity_query_parameters():
    one = "https://example.invalid/ad.html?finnkode=123&utm_source=mail#fragment"
    two = "https://example.invalid/ad.html?finnkode=456"
    assert canonical_url(one) == "https://example.invalid/ad.html?finnkode=123"
    assert canonical_url(one) != canonical_url(two)


def test_active_prices_never_a(candidates, refs, cfg, at):
    asking = [r.model_copy(update={"kind": "asking", "days_to_sell": None}) for r in refs]
    a = evaluate(candidates["attractive"], asking, cfg, at)
    assert a.confidence == "middels" and a.grade != "A"
    assert a.components["liquidity"] == 0


def test_human_estimates_explicit(candidates, refs, cfg, at):
    estimates = [r.model_copy(update={"kind": "human_estimate", "days_to_sell": None}) for r in refs]
    a = evaluate(candidates["attractive"], estimates, cfg, at)
    assert any("menneskelige anslag" in x for x in a.assumptions)
    assert a.components["liquidity"] == 0


def test_mixed_evidence_not_pooled(candidates, refs, cfg, at):
    mixed = [
        r.model_copy(update={"kind": "asking" if i < 3 else "transaction", "days_to_sell": None})
        for i, r in enumerate(refs[:7])
    ]
    a = evaluate(candidates["attractive"], mixed, cfg, at)
    assert a.grade == "U" and a.cash_gain is None


@pytest.mark.parametrize(
    "change",
    [
        {"activation_lock": "unknown"},
        {"mdm": "unknown"},
        {"inspected": False},
        {"risk_flags": ["severe_damage"]},
        {"distance_km": D(100)},
        {"distance_origin": "Bergen"},
    ],
)
def test_unresolved_controls_block_a(candidates, refs, cfg, at, change):
    a = evaluate(candidates["attractive"].model_copy(update=change), refs, cfg, at)
    assert a.grade != "A" and a.controls


def test_historical_freshness_and_future_information(candidates, refs, cfg, at):
    c = candidates["attractive"]
    invalid = [r.model_copy(update={"known_at": at + timedelta(seconds=1)}) for r in refs]
    assert evaluate(c, invalid, cfg, at).grade == "U"
    invalid = [r.model_copy(update={"observed_at": at + timedelta(seconds=1)}) for r in refs]
    assert evaluate(c, invalid, cfg, at).grade == "U"
    invalid = [r.model_copy(update={"observed_at": at - timedelta(days=61)}) for r in refs]
    assert evaluate(c, invalid, cfg, at).grade == "U"


def test_dedup_self_relisting_and_transitive_links(candidates, refs, cfg, at):
    c = candidates["attractive"]
    one = refs[0]
    duplicates = [
        one.model_copy(update={"id": f"copy-{i}", "url": f"https://example.invalid/copy/{i}"})
        for i in range(9)
    ]
    assert len(relevant_references(c, duplicates, cfg, at)) == 1
    duplicates[0].entity_id = c.entity_id
    duplicates[0].url = duplicates[1].url
    assert len(relevant_references(c, duplicates, cfg, at)) == 0
    self_ref = one.model_copy(update={"id": c.id, "entity_id": "different", "url": c.url})
    assert relevant_references(c, [self_ref], cfg, at) == []


def test_dealers_and_demo_real_are_separated(candidates, refs, cfg, at):
    c = candidates["attractive"]
    assert evaluate(c, [r.model_copy(update={"seller_type": "dealer"}) for r in refs], cfg, at).grade == "U"
    assert evaluate(c.model_copy(update={"demo": False}), refs, cfg, at).grade == "U"


@pytest.mark.parametrize(
    "score,grade",
    [(D("49.99"), "D"), (D(50), "C"), (D("64.99"), "C"), (D(65), "B"), (D("79.99"), "B"), (D(80), "A")],
)
def test_score_boundaries(score, grade):
    assert classify(score, True, True, D(0)) == grade
    assert classify(score, False, True, D(0)) == "D"


def test_stress_blocks_a_and_thresholds_configurable(candidates, refs, cfg, at):
    c = candidates["attractive"].model_copy(deep=True)
    c.costs = Costs(transport=D(300), risk_reserve=D(300), hours=D(11), overhead=D(100))
    cfg.niches["macbook"].feasibility_target_hours = D(20)
    a = evaluate(c, refs, cfg, at)
    assert a.score >= 80 and a.economic_profit > 0 and a.stress_profit < 0 and a.grade == "B"
    cfg.niches["macbook"].min_gain = D(10000)
    assert evaluate(c, refs, cfg, at).grade == "D"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1.005"])
def test_invalid_money_rejected(candidates, value):
    raw = candidates["attractive"].model_dump(mode="json")
    raw["price"] = value
    with pytest.raises(ValidationError):
        Candidate.model_validate(raw)
