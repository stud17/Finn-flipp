from datetime import timedelta
from decimal import Decimal

import pytest

from finnflip.models import Feedback
from finnflip.morning import acknowledge_report, has_positive_economics, morning_report, write_report
from finnflip.service import run_analysis


def live_opportunity(store, cfg, candidates, refs, at):
    c = candidates["attractive"].model_copy(
        update={
            "source": "finn_public",
            "demo": False,
            "url": "https://www.finn.no/recommerce/forsale/item/123",
        }
    )
    real_refs = [
        r.model_copy(
            update={
                "source": "test",
                "demo": False,
                "url": f"https://www.finn.no/recommerce/forsale/item/{1000 + i}",
            }
        )
        for i, r in enumerate(refs)
    ]
    store.import_rows("references", real_refs, {}, at)
    store.import_rows("candidates", [c], {}, at)
    a = run_analysis(store, cfg, at)[0]
    assert a.economic_profit > 0
    # Grade D can still have positive profit but miss another threshold: do not filter it out.
    a.grade = "D"
    store.save_assessments([a])
    run_id = store.reserve_scrape(600, at)
    store.finish_scrape(run_id, "ok", {"candidates": 1, "errors": []})
    store.see_live_item(a.candidate_key, "test", [], at)
    return a


@pytest.mark.parametrize("profit", [None, Decimal("-1"), Decimal("0"), Decimal("0.01")])
def test_strict_economic_filter(store, cfg, candidates, refs, at, profit):
    a = live_opportunity(store, cfg, candidates, refs, at)
    a.cash_gain = Decimal("1000")
    a.economic_profit = profit
    assert has_positive_economics(a) == (profit is not None and profit > 0)
    a.candidate.availability = "removed"
    assert not has_positive_economics(a)


def test_morning_only_fresh_real_positives_and_acknowledgement(store, cfg, candidates, refs, at):
    a = live_opportunity(store, cfg, candidates, refs, at)
    first = morning_report(store)
    assert [x["candidate_key"] for x in first["new_opportunities"]] == [a.candidate_key]
    assert first["new_opportunities"][0]["grade"] == "D"
    # Merely generating or retrying a report must not swallow an undelivered notification.
    assert morning_report(store)["new_opportunities"] == first["new_opportunities"]
    write_report(store.path.parent / "morning-report.json", first)
    acknowledge_report(store.path.parent)
    assert morning_report(store)["new_opportunities"] == []
    assert len(morning_report(store)["opportunities"]) == 1
    a.candidate.price -= 100
    a.economic_profit += 100
    store.save_assessments([a])
    assert morning_report(store)["new_opportunities"] == []
    a.candidate.price -= 150
    a.economic_profit += 150
    store.save_assessments([a])
    assert len(morning_report(store)["new_opportunities"]) == 1


@pytest.mark.parametrize("issue", ["stale", "error", "unseen", "demo", "nonpositive", "suppressed"])
def test_morning_excludes_unusable_or_old_opportunities(store, cfg, candidates, refs, at, issue):
    a = live_opportunity(store, cfg, candidates, refs, at)
    if issue == "stale":
        store.see_live_item(a.candidate_key, "test", [], at - timedelta(days=1))
    elif issue == "error":
        store.see_live_item(a.candidate_key, "test", [], None, "read failed")
    elif issue == "unseen":
        with store.connect() as db:
            db.execute("UPDATE live_items SET seen_at=?", ((at - timedelta(days=1)).isoformat(),))
    elif issue == "demo":
        a.candidate = candidates["attractive"]
        store.save_assessments([a])
    elif issue == "nonpositive":
        a.economic_profit = Decimal("0")
        store.save_assessments([a])
    else:
        store.feedback(Feedback(candidate_key=a.candidate_key, status="bought", demo=False))
    assert morning_report(store)["opportunities"] == []


def test_failed_scrape_cannot_produce_morning_opportunities(store, at):
    run_id = store.reserve_scrape(600, at)
    store.finish_scrape(run_id, "blocked", {"error": "blocked"})
    with pytest.raises(ValueError, match="fullført"):
        morning_report(store)
