from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Family = Literal["macbook", "garmin"]
Grade = Literal["A", "B", "C", "D", "U"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fingerprint(value) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Product(Model):
    family: Family
    brand: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=100)
    variant: str | None = Field(default=None, max_length=100)
    ram_gb: int | None = Field(default=None, gt=0, le=256)
    ssd_gb: int | None = Field(default=None, gt=0, le=16384)
    size_mm: int | None = Field(default=None, ge=20, le=70)


class Costs(Model):
    transport: Money = Decimal(0)
    shipping: Money = Decimal(0)
    packaging: Money = Decimal(0)
    fees: Money = Decimal(0)
    accessories: Money = Decimal(0)
    repair: Money = Decimal(0)
    risk_reserve: Money = Decimal(0)
    hours: Decimal = Field(default=Decimal(1), ge=0, le=1000)
    overhead: Money = Decimal(0)
    capital_cost: Money = Decimal(0)

    @property
    def direct(self) -> Decimal:
        return sum((self.transport, self.shipping, self.packaging, self.fees, self.accessories, self.repair))


class Observation(Model):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    source: str = Field(min_length=1, max_length=80, pattern=r"^[\w.-]+$")
    entity_id: str = Field(min_length=1, max_length=160)
    url: str = Field(max_length=1500)
    title: str = Field(min_length=1, max_length=250)
    product: Product
    price: Money
    currency: Literal["NOK"] = "NOK"
    condition: Literal["excellent", "good", "fair", "damaged", "unknown"] = "unknown"
    demo: bool = False

    @field_validator("url")
    @classmethod
    def safe_url(cls, value):
        url = urlsplit(value)
        if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
            raise ValueError("URL må være en HTTP(S)-lenke uten påloggingsinformasjon")
        if any(ord(c) < 32 for c in value):
            raise ValueError("Kontrolltegn i URL")
        return value

    @model_validator(mode="after")
    def demo_domain(self):
        host = urlsplit(self.url).hostname
        if self.demo and not (host == "example.invalid" or host.endswith(".example.invalid")):
            raise ValueError("Demo må bruke example.invalid")
        return self


class Candidate(Observation):
    location: str = Field(default="ukjent", max_length=100)
    distance_km: Decimal | None = Field(default=None, ge=0, le=30000)
    distance_origin: str | None = Field(default=None, max_length=100)
    shipping_possible: bool = False
    published_at: datetime | None = None
    received_at: datetime
    updated_at: datetime | None = None
    seller_type: Literal["private", "dealer", "unknown"] = "unknown"
    availability: Literal["active", "removed", "unknown"] = "active"
    price_meaning: Literal["unit", "installment", "component", "from", "wanted", "bundle", "unknown"] = (
        "unknown"
    )
    price_note: str = Field(default="", max_length=500)
    risk_flags: list[str] = Field(default_factory=list, max_length=30)
    activation_lock: Literal["cleared", "unknown", "locked"] = "unknown"
    mdm: Literal["cleared", "unknown", "locked"] = "unknown"
    inspected: bool = False
    costs: Costs | None = None

    @field_validator("published_at", "received_at", "updated_at")
    @classmethod
    def aware_time(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("Tidspunkt må ha tidssone")
        return value

    @field_validator("risk_flags")
    @classmethod
    def bounded_flags(cls, value):
        if any(len(flag) > 100 for flag in value):
            raise ValueError("Risikoflagg kan ha høyst 100 tegn")
        return value

    @model_validator(mode="after")
    def chronology(self):
        if self.published_at and self.published_at > self.received_at:
            raise ValueError("Publisering kan ikke være etter mottak")
        return self


class Reference(Observation):
    kind: Literal["asking", "human_estimate", "transaction"]
    seller_type: Literal["private", "dealer", "unknown"] = "private"
    availability: Literal["active", "removed", "unknown"] = "active"
    observed_at: datetime
    known_at: datetime
    documentation: str = Field(min_length=5, max_length=1500)
    days_to_sell: int | None = Field(default=None, ge=0, le=1000)

    @field_validator("observed_at", "known_at")
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None:
            raise ValueError("Tidspunkt må ha tidssone")
        return value

    @model_validator(mode="after")
    def chronology(self):
        if self.known_at < self.observed_at:
            raise ValueError("Referansen kan ikke være kjent før observasjonen")
        if self.days_to_sell is not None and self.kind != "transaction":
            raise ValueError("Dokumentert salgstid krever bekreftet transaksjon")
        return self


class CatalogItem(Model):
    id: str = Field(pattern=r"^[\w.-]+$")
    label: str
    product: Product
    baseline_limit: Money


class Niche(Model):
    min_gain: Money
    gain_target: Decimal = Field(gt=0)
    roi_target: Decimal = Field(gt=0)
    freshness_days: int = Field(ge=1, le=3650)
    liquidity_target_days: int = Field(gt=0)
    feasibility_target_hours: Decimal = Field(gt=0)
    defaults: Costs


class MailConfig(Model):
    mode: Literal["DRY_RUN", "SMTP"] = "DRY_RUN"
    owner_address: str | None = None
    from_address: str | None = None
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    cooldown_hours: int = Field(default=24, ge=0)
    score_improvement: int = Field(default=10, ge=1, le=100)


class Config(Model):
    version: str
    location: str = "Oslo"
    radius_km: Decimal = Field(default=Decimal(40), gt=0)
    allow_shipping: bool = False
    capital_limit: Money | None = None
    hourly_value: Money = Decimal(300)
    min_roi: Decimal = Field(default=Decimal("0.20"), ge=0)
    min_references: int = Field(default=5, ge=5)
    asking_discount: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    niches: dict[Family, Niche]
    catalog: list[CatalogItem] = Field(min_length=1, max_length=100)
    mail: MailConfig = Field(default_factory=MailConfig)

    @model_validator(mode="after")
    def complete(self):
        if set(self.niches) != {"macbook", "garmin"}:
            raise ValueError("Konfigurasjonen må ha begge produktfamilier")
        ids = [c.id for c in self.catalog]
        products = [fingerprint(c.product) for c in self.catalog]
        if len(set(ids)) != len(ids) or len(set(products)) != len(products):
            raise ValueError("Duplikater i produktkatalogen")
        return self


class Assessment(Model):
    candidate_key: str
    candidate: Candidate
    evaluated_at: datetime
    config_hash: str
    config_snapshot: dict
    calculation_version: str = "1.0.0"
    reference_ids: list[str] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    product_id: str | None = None
    grade: Grade = "U"
    status: str = "INSUFFICIENT_DATA"
    score: Decimal | None = None
    components: dict[str, Decimal] = Field(default_factory=dict)
    confidence: str = "utilstrekkelig"
    reasons: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    reference_stats: dict = Field(default_factory=dict)
    resale_low: Decimal | None = None
    resale_high: Decimal | None = None
    cash_gain: Decimal | None = None
    economic_profit: Decimal | None = None
    roi: Decimal | None = None
    max_purchase: Decimal | None = None
    max_purchase_economic: Decimal | None = None
    economic_at_max_purchase: Decimal | None = None
    stress_profit: Decimal | None = None
    costs: Costs | None = None
    baseline_selected: bool = False


FeedbackStatus = Literal[
    "irrelevant", "wrong_model", "gone", "investigated", "bought", "sold", "returned", "loss"
]


class Feedback(Model):
    candidate_key: str
    status: FeedbackStatus
    usable: bool | None = None
    review_minutes: Decimal = Field(default=Decimal(0), ge=0, le=10000)
    at: datetime = Field(default_factory=utcnow)
    demo: bool = False

    @field_validator("at")
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None:
            raise ValueError("Tidspunkt må ha tidssone")
        return value


class Trade(Model):
    candidate_key: str
    bought_at: datetime
    purchase: Money
    costs: Costs
    hourly_value: Money
    status: Literal["inventory", "sold", "returned", "loss"] = "inventory"
    sale: Money | None = None
    closed_at: datetime | None = None
    inventory_value: Money | None = None
    demo: bool = False

    @field_validator("bought_at", "closed_at")
    @classmethod
    def aware_time(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("Tidspunkt må ha tidssone")
        return value

    @model_validator(mode="after")
    def complete(self):
        if self.status != "inventory" and (self.sale is None or self.closed_at is None):
            raise ValueError("Avsluttet handel må ha faktisk oppgjør og dato (også tap/retur)")
        if self.status == "inventory" and (self.sale is not None or self.closed_at is not None):
            raise ValueError("Lagerført handel kan ikke ha registrert oppgjør")
        if self.closed_at and self.closed_at < self.bought_at:
            raise ValueError("Avslutning kan ikke være før kjøp")
        return self

    def result(self) -> dict:
        cash = money(self.sale - self.purchase - self.costs.direct) if self.sale is not None else None
        return {
            "status": self.status,
            "demo": self.demo,
            "cash_gain": cash,
            "economic_profit": money(
                cash - self.costs.hours * self.hourly_value - self.costs.overhead - self.costs.capital_cost
            )
            if cash is not None
            else None,
            "capital_bound": self.purchase + self.costs.direct if self.status == "inventory" else Decimal(0),
            "inventory_value": self.inventory_value if self.status == "inventory" else None,
        }
