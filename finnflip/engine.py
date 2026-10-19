from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from statistics import median
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Assessment, Candidate, Config, Costs, Product, Reference, fingerprint, money

D = Decimal
WEIGHTS = {
    "cash_gain": D("0.35"),
    "roi": D("0.20"),
    "evidence": D("0.20"),
    "liquidity": D("0.15"),
    "feasibility": D("0.10"),
}


def candidate_key(c: Candidate) -> str:
    return f"{c.source}:{c.id}"


def normalized_product(p: Product) -> tuple:
    return (
        p.family,
        p.brand.casefold(),
        p.model.casefold(),
        (p.variant or "").casefold(),
        p.ram_gb,
        p.ssd_gb,
        p.size_mm,
    )


def match_product(c: Candidate, cfg: Config):
    p = c.product
    if not p.variant or (p.family == "macbook" and (not p.ram_gb or not p.ssd_gb)):
        return None
    if p.family == "garmin" and not p.size_mm:
        return None
    return next(
        (item for item in cfg.catalog if normalized_product(item.product) == normalized_product(p)), None
    )


def ambiguous_price(c: Candidate) -> bool:
    text = f"{c.title} {c.price_note}".casefold()
    pattern = r"delbetaling|avdrag|pr\.?\s*m[åa]ned|per m[åa]ned|/mnd|ønskes kjøpt|\bwtb\b|\bfra\s+\d|pakkepris|kun (?:skjerm|lader|reim)|\bbundle\b|\bpakke\b"
    return c.price_meaning != "unit" or bool(re.search(pattern, text))


def canonical_url(url: str) -> str:
    p = urlsplit(url)
    query = sorted(
        (key, value)
        for key, value in parse_qsl(p.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    )
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(query), ""))


def relevant_references(
    c: Candidate, references: list[Reference], cfg: Config, at: datetime
) -> list[Reference]:
    oldest = at - timedelta(days=cfg.niches[c.product.family].freshness_days)
    eligible = [
        r
        for r in references
        if r.demo == c.demo
        and r.seller_type == "private"
        and (r.kind != "asking" or r.availability == "active")
        and normalized_product(r.product) == normalized_product(c.product)
        and r.condition == c.condition
        and r.condition not in {"damaged", "unknown"}
        and oldest <= r.observed_at <= at
        and r.known_at <= at
        and r.price > 0
    ]
    # Union identity signals: a relisting or a transitive chain must only count once.
    rows = [c] + sorted(eligible, key=lambda r: (r.observed_at, r.id), reverse=True)
    parent = list(range(len(rows)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        signals = [f"entity:{row.entity_id}", f"ad:{row.source}:{row.id}", f"url:{canonical_url(row.url)}"]
        for signal in signals:
            if signal in seen:
                parent[root(i)] = root(seen[signal])
            else:
                seen[signal] = i
    candidate_group = root(0)
    picked = set()
    result = []
    for i, row in enumerate(rows[1:], 1):
        group = root(i)
        if group != candidate_group and group not in picked:
            result.append(row)
            picked.add(group)
    return result


def quantile(prices: list[Decimal], fraction: Decimal) -> Decimal:
    ordered = sorted(prices)
    index = D(len(ordered) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return money(ordered[low] + (ordered[high] - ordered[low]) * (index - low))


def economics(resale: Decimal, purchase: Decimal, costs: Costs, cfg: Config, min_gain: Decimal) -> dict:
    invested = purchase + costs.direct
    if invested <= 0:
        raise ValueError("Innkjøp + direkte kostnader må være positivt")
    cash = money(resale - invested - costs.risk_reserve)
    time_and_ops = costs.hours * cfg.hourly_value + costs.overhead + costs.capital_cost
    # Floor the limit: rounding up could violate the requested minimum.
    max_price = min(
        resale - costs.direct - costs.risk_reserve - min_gain,
        (resale - costs.risk_reserve) / (1 + cfg.min_roi) - costs.direct,
    )
    max_price = max_price.quantize(D("0.01"), rounding=ROUND_FLOOR) if max_price >= 0 else None
    economic_cap = (resale - costs.direct - costs.risk_reserve - time_and_ops - D("0.01")).quantize(
        D("0.01"), rounding=ROUND_FLOOR
    )
    economic_cap = economic_cap if economic_cap >= 0 else None
    return {
        "cash_gain": cash,
        "economic_profit": money(cash - time_and_ops),
        "roi": cash / invested,
        "max_purchase": max_price,
        "max_purchase_economic": economic_cap,
        "economic_at_max_purchase": money(
            resale - max_price - costs.direct - costs.risk_reserve - time_and_ops
        )
        if max_price is not None
        else None,
        "stress_profit": money(money(resale * D("0.90")) - invested - costs.risk_reserve - time_and_ops),
    }


def classify(score: Decimal, economic_ok: bool, a_eligible: bool, stress_profit: Decimal) -> str:
    if not economic_ok:
        return "D"
    if score >= 80:
        return "A" if a_eligible and stress_profit >= 0 else "B"
    return "B" if score >= 65 else "C" if score >= 50 else "D"


def scaled(value: Decimal, target: Decimal) -> Decimal:
    return max(D(0), min(D(100), D(100) * value / target))


def evaluate(c: Candidate, references: list[Reference], cfg: Config, at: datetime) -> Assessment:
    if at.tzinfo is None:
        raise ValueError("Vurderingstidspunkt må ha tidssone")
    a = Assessment(
        candidate_key=candidate_key(c),
        candidate=c,
        evaluated_at=at,
        config_hash=fingerprint(cfg),
        config_snapshot=cfg.model_dump(mode="json"),
    )
    a.assumptions = [
        "Alle beløp før inntektsskatt. MVA-behandling er uavklart.",
        "Risikoreserven dekker usikre tap, ikke allerede budsjettert reparasjon.",
    ]
    item = match_product(c, cfg)
    if c.availability != "active":
        a.reasons = ["Annonsen er fjernet eller tilgjengeligheten er uavklart; ingen aktiv kjøpsmulighet."]
        return a
    if not item:
        a.status = "MANUAL_REVIEW"
        a.reasons = ["Eksakt modell/konfigurasjon mangler eller finnes ikke i katalogen. Ikke gjett variant."]
        return a
    a.product_id = item.id
    if ambiguous_price(c):
        a.status = "MANUAL_REVIEW"
        a.reasons = ["Prisbetydning må avklares: delbetaling, komponent, fra-pris, kjøpsønske eller pakke."]
        return a
    if c.received_at > at or c.price <= 0 or c.condition in {"unknown", "damaged"}:
        a.reasons = ["Ugyldig pris/tidspunkt eller tilstand som krever særskilt avklaring."]
        return a
    a.baseline_selected = c.price <= item.baseline_limit
    refs = relevant_references(c, references, cfg, at)
    a.references = refs
    a.reference_ids = [f"{r.source}:{r.id}" for r in refs]
    ages = [(at - r.observed_at).total_seconds() / 86400 for r in refs]
    a.reference_stats = {
        "count": len(refs),
        "oldest_days": round(max(ages), 1) if ages else None,
        "newest_days": round(min(ages), 1) if ages else None,
        "price_min": str(min(r.price for r in refs)) if refs else None,
        "price_max": str(max(r.price for r in refs)) if refs else None,
        "kinds": {
            kind: sum(r.kind == kind for r in refs) for kind in ("asking", "human_estimate", "transaction")
        },
    }
    if len(refs) < cfg.min_references:
        a.reasons = [
            f"Bare {len(refs)} uavhengige, ferske og eksakt sammenlignbare referanser; krever {cfg.min_references}."
        ]
        return a
    # Never pool asking prices and final prices. Prefer a complete transaction cohort.
    cohort = []
    selected_kind = "asking"
    for kind in ("transaction", "human_estimate", "asking"):
        subset = [r for r in refs if r.kind == kind]
        if len(subset) >= cfg.min_references:
            cohort, selected_kind = subset, kind
            break
    if not cohort:
        a.reasons = ["Ingen kildetype har nok referanser alene; annonsepris og oppgjør blandes ikke."]
        return a
    a.reference_stats["valuation_kind"] = selected_kind
    a.reference_stats["valuation_ids"] = [f"{r.source}:{r.id}" for r in cohort]
    prices = [r.price for r in cohort]
    discount = 1 - cfg.asking_discount if selected_kind == "asking" else D(1)
    a.resale_low = money(quantile(prices, D("0.25")) * discount)
    a.resale_high = money(quantile(prices, D("0.75")) * discount)
    a.confidence = "middels" if selected_kind == "asking" else "sterkt"
    if selected_kind == "asking":
        a.assumptions.append(
            f"Nedre kvartil annonsepris med {cfg.asking_discount * 100}% antatt salgsrabatt; ikke validert salgspris."
        )
    elif selected_kind == "human_estimate":
        a.assumptions.append("Prisgrunnlaget er menneskelige anslag, ikke bekreftede transaksjoner.")
    else:
        a.assumptions.append(
            "Nedre kvartil av dokumenterte oppgjør; fremtidig videresalg er fortsatt et estimat."
        )
    niche = cfg.niches[c.product.family]
    a.costs = c.costs or niche.defaults
    a.assumptions.append(
        "Kostnader: " + ("registrert for objektet." if c.costs else "konfigurerte pilotanslag.")
    )
    for name, value in economics(a.resale_low, c.price, a.costs, cfg, niche.min_gain).items():
        setattr(a, name, value)
    if c.product.family == "macbook":
        if c.activation_lock != "cleared":
            a.controls.append("Aktiveringslås må være kontrollert og fjernet.")
        if c.mdm != "cleared":
            a.controls.append("Organisasjonsadministrering/MDM må avklares.")
    if c.risk_flags:
        a.controls.extend(f"Uavklart risiko: {flag}" for flag in c.risk_flags)
    if not c.inspected:
        a.controls.append(
            "Funksjon, batteri og tilstand må kontrolleres; fravær av feiltekst er ikke en kontroll."
        )
    local = c.distance_km is not None and c.distance_origin == cfg.location and c.distance_km <= cfg.radius_km
    if not local and not (cfg.allow_shipping and c.shipping_possible):
        a.controls.append(
            "Avstand/transport utenfor valgt område eller ikke avklart mot konfigurert utgangspunkt."
        )
    if cfg.capital_limit is not None and c.price + a.costs.direct > cfg.capital_limit:
        a.controls.append("Kapitalbehov for objektet overstiger konfigurert kapitalramme.")
    evidence = (
        D(100) if selected_kind == "transaction" else D(85) if selected_kind == "human_estimate" else D(55)
    )
    durations = [D(r.days_to_sell) for r in cohort if r.days_to_sell is not None]
    liquidity = (
        scaled(D(niche.liquidity_target_days), max(D(1), D(median(durations))))
        if len(durations) >= 3
        else D(0)
    )
    if len(durations) < 3:
        a.assumptions.append(
            "Omsettelighet ukjent: færre enn tre dokumenterte salgstider; delscore 0, ingen salgssannsynlighet."
        )
    feasibility = (
        scaled(niche.feasibility_target_hours, max(D("0.01"), a.costs.hours)) if not a.controls else D(25)
    )
    a.components = {
        "cash_gain": scaled(a.cash_gain, niche.gain_target),
        "roi": scaled(a.roi, niche.roi_target),
        "evidence": evidence,
        "liquidity": liquidity,
        "feasibility": feasibility,
    }
    # Classify using the displayed score; no hidden rounding boundary.
    a.score = money(sum(a.components[k] * WEIGHTS[k] for k in WEIGHTS))
    economic_ok = a.cash_gain >= niche.min_gain and a.roi >= cfg.min_roi and a.economic_profit > 0
    a.grade = classify(a.score, economic_ok, a.confidence == "sterkt" and not a.controls, a.stress_profit)
    a.status = "EVALUATED"
    a.reasons = [
        f"{selected_kind}: nedre kvartil av {len(cohort)} uavhengige referanser.",
        f"Kontantgevinst {a.cash_gain} kr; avkastning {a.roi:.1%}; økonomisk overskudd {a.economic_profit} kr.",
    ]
    if not economic_ok:
        a.reasons.append("Økonomiske minstekrav ikke oppfylt.")
        if a.max_purchase is not None and c.price > a.max_purchase > 0:
            a.status = "NEGOTIATION_OPPORTUNITY"
            a.reasons.append(
                "Forhandlingsmulighet: krever lavere kjøpspris; ikke et kupp til annonsert pris."
            )
    if a.score >= 80 and a.grade == "B":
        a.reasons.append("A blokkert av datagrunnlag, kontrollpunkter eller negativt 10 %-scenario.")
    return a
