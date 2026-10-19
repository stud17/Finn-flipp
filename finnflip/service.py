from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from .engine import evaluate
from .models import Config, utcnow
from .notifications import export_drafts, prepare_outbox
from .sources import DemoAdapter, SourceAdapter, bounded_read
from .storage import Store

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path | None = None) -> Config:
    return Config.model_validate_json(bounded_read(path or ROOT / "config.json"))


def import_source(store: Store, adapter: SourceAdapter, kind: str) -> int:
    rows, provenance = adapter.load(kind)
    return store.import_rows(kind, rows, provenance)


def run_analysis(store: Store, cfg: Config, at: datetime | None = None):
    at = at or utcnow()
    if at.tzinfo is None:
        raise ValueError("Vurderingstidspunkt må ha tidssone")
    references = store.observations("references", at)
    assessments = [evaluate(c, references, cfg, at) for c in store.observations("candidates", at)]
    store.save_assessments(assessments)
    return sorted(assessments, key=lambda a: (a.score is not None, a.score or 0), reverse=True)


def load_demo(store: Store, cfg: Config):
    adapter = DemoAdapter(ROOT / "fixtures")
    counts = {kind: import_source(store, adapter, kind) for kind in ("references", "candidates")}
    assessments = run_analysis(store, cfg)
    counts["drafts"] = prepare_outbox(store, assessments, cfg)
    export_drafts(store, store.path.parent / "drafts")
    return counts


def csv_safe(value):
    # Avoid interpreting imported titles as spreadsheet formulas in exported reports.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def comparison_csv(store: Store) -> str:
    rows = store.feedback_rows()
    latest = {f.candidate_key: f for f in rows}
    assessments = store.assessments()
    ordered = sorted(assessments, key=lambda a: a.score if a.score is not None else -1, reverse=True)
    # Rank demo and real candidates separately. Match comparison volumes within each cohort.
    config_by_a = {a.candidate_key: Config.model_validate(a.config_snapshot) for a in assessments}
    baseline = [a for a in assessments if a.baseline_selected]

    def baseline_ratio(a):
        item = next(x for x in config_by_a[a.candidate_key].catalog if x.id == a.product_id)
        return a.candidate.price / max(item.baseline_limit, 1)

    baseline.sort(key=baseline_ratio)
    engine_ranks, baseline_ranks, volumes = {}, {}, {}
    for demo in (False, True):
        engine_cohort = [a for a in ordered if a.candidate.demo == demo and a.score is not None]
        baseline_cohort = [a for a in baseline if a.candidate.demo == demo]
        engine_ranks.update({a.candidate_key: rank for rank, a in enumerate(engine_cohort, 1)})
        baseline_ranks.update({a.candidate_key: rank for rank, a in enumerate(baseline_cohort, 1)})
        volumes[demo] = min(10, len(engine_cohort), len(baseline_cohort))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "candidate_key",
            "demo",
            "title",
            "engine_rank",
            "engine_top10",
            "baseline_selected",
            "baseline_rank",
            "baseline_top10",
            "matched_volume",
            "engine_matched_volume",
            "baseline_matched_volume",
            "grade",
            "score",
            "label",
            "usable_after_control",
            "review_minutes",
            "estimated_cash_gain",
            "estimated_economic_profit",
            "measured_cash_gain",
            "measured_economic_profit",
        ]
    )
    trades = {t.candidate_key: t for t in store.trades()}
    for a in ordered:
        f = latest.get(a.candidate_key)
        trade = trades.get(a.candidate_key)
        real = trade.result() if trade else {}
        rank = engine_ranks.get(a.candidate_key)
        baseline_rank = baseline_ranks.get(a.candidate_key)
        volume = volumes[a.candidate.demo]
        writer.writerow(
            [
                csv_safe(x)
                for x in [
                    a.candidate_key,
                    a.candidate.demo,
                    a.candidate.title,
                    rank,
                    rank is not None and rank <= 10,
                    a.baseline_selected,
                    baseline_rank,
                    baseline_rank is not None and baseline_rank <= 10,
                    volume,
                    rank is not None and rank <= volume,
                    baseline_rank is not None and baseline_rank <= volume,
                    a.grade,
                    a.score,
                    f.status if f else "",
                    f.usable if f else "",
                    sum(x.review_minutes for x in rows if x.candidate_key == a.candidate_key) if f else "",
                    a.cash_gain,
                    a.economic_profit,
                    real.get("cash_gain", ""),
                    real.get("economic_profit", ""),
                ]
            ]
        )
    return output.getvalue()
