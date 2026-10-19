"""Reproduser syntetiske fixtures. Ingen priser er hentet fra markedet."""

import csv
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AT = datetime(2026, 10, 19, 8, tzinfo=timezone.utc)


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


catalog = [
    (
        "air-m1-8-256",
        "MacBook Air M1 · 8/256",
        "macbook",
        "Apple",
        "MacBook Air M1",
        "13-inch 2020",
        8,
        256,
        None,
        4000,
        6500,
    ),
    (
        "air-m1-16-256",
        "MacBook Air M1 · 16/256",
        "macbook",
        "Apple",
        "MacBook Air M1",
        "13-inch 2020",
        16,
        256,
        None,
        4800,
        7400,
    ),
    (
        "air-m2-8-256",
        "MacBook Air M2 · 8/256",
        "macbook",
        "Apple",
        "MacBook Air M2",
        "13-inch 2022",
        8,
        256,
        None,
        5500,
        8500,
    ),
    (
        "air-m2-16-512",
        "MacBook Air M2 · 16/512",
        "macbook",
        "Apple",
        "MacBook Air M2",
        "13-inch 2022",
        16,
        512,
        None,
        7000,
        11000,
    ),
    (
        "forerunner-955",
        "Garmin Forerunner 955 · standard 46 mm",
        "garmin",
        "Garmin",
        "Forerunner 955",
        "standard",
        None,
        None,
        46,
        1600,
        3200,
    ),
    (
        "forerunner-965",
        "Garmin Forerunner 965 · standard 47 mm",
        "garmin",
        "Garmin",
        "Forerunner 965",
        "standard",
        None,
        None,
        47,
        2300,
        4200,
    ),
    (
        "fenix7-47",
        "Garmin fēnix 7 · standard 47 mm",
        "garmin",
        "Garmin",
        "fēnix 7",
        "standard",
        None,
        None,
        47,
        2000,
        3800,
    ),
    (
        "fenix7s-42",
        "Garmin fēnix 7S · standard 42 mm",
        "garmin",
        "Garmin",
        "fēnix 7S",
        "standard",
        None,
        None,
        42,
        1900,
        3600,
    ),
]
items = []
for id_, label, family, brand, model, variant, ram, ssd, size, limit, _ in catalog:
    items.append(
        {
            "id": id_,
            "label": label,
            "product": {
                "family": family,
                "brand": brand,
                "model": model,
                "variant": variant,
                "ram_gb": ram,
                "ssd_gb": ssd,
                "size_mm": size,
            },
            "baseline_limit": str(limit),
        }
    )

config = {
    "version": "pilot-2026-10-19-v1",
    "location": "Oslo",
    "radius_km": "40",
    "allow_shipping": False,
    "capital_limit": None,
    "hourly_value": "300",
    "min_roi": "0.20",
    "min_references": 5,
    "asking_discount": "0.10",
    "mail": {"mode": "DRY_RUN", "cooldown_hours": 24, "score_improvement": 10},
    "catalog": items,
    "niches": {
        "macbook": {
            "min_gain": "1000",
            "gain_target": "3000",
            "roi_target": "0.50",
            "freshness_days": 60,
            "liquidity_target_days": 14,
            "feasibility_target_hours": "2",
            "defaults": {
                "transport": "150",
                "fees": "100",
                "packaging": "50",
                "risk_reserve": "300",
                "hours": "2",
                "overhead": "100",
                "capital_cost": "30",
            },
        },
        "garmin": {
            "min_gain": "500",
            "gain_target": "1500",
            "roi_target": "0.50",
            "freshness_days": 45,
            "liquidity_target_days": 14,
            "feasibility_target_hours": "1.5",
            "defaults": {
                "transport": "80",
                "fees": "70",
                "packaging": "30",
                "risk_reserve": "150",
                "hours": "1.5",
                "overhead": "50",
                "capital_cost": "10",
            },
        },
    },
}
save("config.json", config)
save("docs/config.example.json", config)
refs = []
for item, spec in zip(items, catalog):
    for i in range(7):
        day = AT - timedelta(days=3 + i * 2)
        kind = "transaction" if item["id"].startswith("air-") else "asking"
        refs.append(
            {
                "id": f"ref-{item['id']}-{i}",
                "source": "demo",
                "entity_id": f"demo-item-{item['id']}-{i}",
                "url": f"https://example.invalid/references/{item['id']}/{i}",
                "title": f"DEMO {item['label']} referanse {i}",
                "product": item["product"],
                "price": str(spec[-1] + 200 * i),
                "condition": "good",
                "demo": True,
                "kind": kind,
                "observed_at": day.isoformat(),
                "known_at": day.isoformat(),
                "documentation": "Syntetisk referanse med oppdiktet oppgjør."
                if kind == "transaction"
                else "Syntetisk aktiv annonsepris. Ikke et kjent oppgjør.",
                "days_to_sell": 5 + i if kind == "transaction" else None,
            }
        )
save("fixtures/references.json", refs)


def candidate(id_, idx, price, label):
    return {
        "id": id_,
        "source": "demo",
        "entity_id": f"demo-candidate-{id_}",
        "url": f"https://example.invalid/candidates/{id_}",
        "title": f"DEMO {label}",
        "product": deepcopy(items[idx]["product"]),
        "price": str(price),
        "condition": "good",
        "demo": True,
        "location": "Oslo",
        "distance_km": "8",
        "distance_origin": "Oslo",
        "price_meaning": "unit",
        "received_at": (AT - timedelta(minutes=10)).isoformat(),
        "published_at": (AT - timedelta(minutes=30)).isoformat(),
        "activation_lock": "cleared",
        "mdm": "cleared",
        "inspected": True,
    }


candidates = [
    candidate("attractive", 0, 2400, "Air M1 8/256 · attraktiv etter kostnader"),
    candidate("cost-trap", 1, 4200, "Air M1 16/256 · billig før kostnader"),
    candidate("wrong-config", 0, 2200, "Air M1 · ukjent RAM"),
    candidate("insufficient", 7, 1200, "fēnix 7S · for få referanser i riktig tilstand"),
    candidate("lock-risk", 2, 2500, "Air M2 · uavklart aktiveringslås"),
    candidate("garmin-interesting", 4, 900, "Forerunner 955 · kun annonsepriser"),
    candidate("installments", 3, 299, "Air M2 · 299 kr/mnd delbetaling"),
    candidate("bundle", 5, 1500, "Forerunner 965 pakkepris for deler"),
    candidate("weak", 6, 3500, "fēnix 7 · for liten margin"),
    candidate("garmin-c", 5, 2800, "Forerunner 965 · overvåk"),
    candidate("variant-mismatch", 6, 1700, "fēnix 7 Solar · uten katalogmatch"),
]
candidates[1]["costs"] = {
    "transport": "400",
    "fees": "150",
    "repair": "1800",
    "risk_reserve": "300",
    "hours": "4",
    "overhead": "100",
    "capital_cost": "50",
}
candidates[2]["product"]["ram_gb"] = None
candidates[3]["condition"] = "fair"
candidates[4]["activation_lock"] = "unknown"
candidates[4]["inspected"] = False
candidates[5]["published_at"] = None
candidates[6]["price_meaning"] = "installment"
candidates[7]["price_meaning"] = "bundle"
candidates[10]["product"]["variant"] = "Solar"
save("fixtures/candidates.json", candidates)
with (ROOT / "fixtures/candidates.csv").open("w", encoding="utf-8", newline="") as file:
    columns = sorted({key for row in candidates for key in row})
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    for row in candidates:
        writer.writerow(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else ""
                if value is None
                else str(value).lower()
                if isinstance(value, bool)
                else value
                for key, value in row.items()
            }
        )
save(
    "fixtures/feedback.json",
    {
        "candidate_key": "demo:attractive",
        "status": "sold",
        "usable": True,
        "review_minutes": "20",
        "demo": True,
    },
)
save(
    "fixtures/trade-sold.json",
    {
        "candidate_key": "demo:attractive",
        "bought_at": "2026-10-19T10:00:00+02:00",
        "purchase": "2400",
        "costs": {
            "transport": "150",
            "fees": "100",
            "packaging": "50",
            "hours": "2",
            "overhead": "100",
            "capital_cost": "30",
        },
        "hourly_value": "300",
        "status": "sold",
        "sale": "6500",
        "closed_at": "2026-10-19T12:00:00+02:00",
        "demo": True,
    },
)
save(
    "fixtures/trade-inventory.json",
    {
        "candidate_key": "demo:garmin-interesting",
        "bought_at": "2026-10-19T10:00:00+02:00",
        "purchase": "900",
        "costs": {"transport": "80", "hours": "0.5"},
        "hourly_value": "300",
        "status": "inventory",
        "inventory_value": "2200",
        "demo": True,
    },
)
print(f"DEMO: {len(items)} eksakte grupper, {len(refs)} referanser, {len(candidates)} kandidater")
