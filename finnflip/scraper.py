"""Avgrenset innhenting av offentlig HTML. Ingen innlogging eller skjulte API-er."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Comment
from pydantic import Field, field_validator

from .models import Candidate, Config, Family, Model, Product, Reference, utcnow
from .sources import SourceAdapter, bounded_read
from .storage import Store

ITEM_PATH = re.compile(r"^/recommerce/forsale/item/(\d+)/?$")
OSLO = ZoneInfo("Europe/Oslo")
PARSER_VERSION = "1.2.0"


class SourceBlocked(ValueError):
    pass


class PageRemoved(ValueError):
    pass


def validate_public_url(url: str, search: bool = False) -> str:
    parsed = urlsplit(url)
    valid_path = (
        parsed.path.rstrip("/") == "/recommerce/forsale/search"
        if search
        else bool(ITEM_PATH.fullmatch(parsed.path))
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"www.finn.no", "finn.no"}
        or parsed.port not in {None, 443}
        or parsed.username
        or parsed.password
        or not valid_path
    ):
        raise ValueError("Bruk en offentlig HTTPS FINN Torget-søke- eller annonselenke")
    return url


class SearchSpec(Model):
    name: str = Field(min_length=1, max_length=80)
    family: Family
    url: str
    limit: int | None = Field(default=None, ge=1, le=20)

    @field_validator("url")
    @classmethod
    def search_url(cls, value):
        return validate_public_url(value, search=True)


class ScrapeConfig(Model):
    searches: list[SearchSpec] = Field(min_length=1, max_length=6)
    items_per_search: int = Field(default=8, ge=1, le=20)
    min_interval_seconds: int = Field(default=600, ge=300, le=86400)
    request_delay_seconds: float = Field(default=2, ge=1, le=30)
    detail_refresh_minutes: int = Field(default=120, ge=10, le=1440)
    timeout_seconds: int = Field(default=20, ge=5, le=45)


def load_scrape_config(path: Path) -> ScrapeConfig:
    return ScrapeConfig.model_validate_json(bounded_read(path))


def visible_text(node) -> str:
    if node is None:
        return ""
    # FINN uses declarative shadow DOM: BS4 classifies text there as TemplateString.
    # get_text() drops it. Scoped traversal includes visible template text but not scripts/comments.
    return " ".join(
        str(s).strip()
        for s in node.find_all(string=True)
        if not isinstance(s, Comment) and s.parent.name not in {"script", "style"} and str(s).strip()
    )


@dataclass
class SearchCard:
    id: str
    url: str
    title: str
    price: Decimal | None
    location: str
    promoted: bool = False


def parse_price(value: str) -> Decimal | None:
    value = value.replace("\xa0", " ").strip()
    if value.casefold() in {"gis bort", "gratis"}:
        return Decimal(0)
    match = re.fullmatch(r"\s*([\d .]+)(?:,([0-9]{1,2}))?\s*(?:kr|nok)?\s*", value, re.I)
    if not match:
        return None
    digits = re.sub(r"[ .]", "", match[1])
    return Decimal(digits + ("." + match[2] if match[2] else "")) if digits else None


def parse_search(html: str, base_url: str) -> list[SearchCard]:
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    seen = set()
    for node in soup.select("article.sf-search-ad"):
        anchor = node.select_one("a.sf-search-ad-link[href]")
        heading = node.select_one("h2")
        if anchor is None or heading is None:
            continue
        url = urljoin(base_url, anchor["href"]).split("?")[0].split("#")[0]
        try:
            validate_public_url(url)
        except ValueError:
            continue
        id_ = ITEM_PATH.fullmatch(urlsplit(url).path)[1]
        if id_ in seen:
            continue
        seen.add(id_)
        spans = [visible_text(s) for s in node.select("span")]
        price_text = next(
            (
                t
                for t in spans
                if re.fullmatch(r"[\d\s.,]+\s*kr", t, re.I) or t.casefold() in {"gis bort", "gratis"}
            ),
            "",
        )
        place = node.select_one("span.whitespace-nowrap.truncate")
        cards.append(
            SearchCard(
                id_,
                url,
                visible_text(heading)[:250],
                parse_price(price_text),
                visible_text(place) or "ukjent",
                "betalt plassering" in visible_text(node).casefold(),
            )
        )
    if not cards:
        text = visible_text(soup)
        if re.search(r"\b0 (?:treff|resultater)\b", text):
            return []
        raise ValueError(
            "Søkesiden ga ingen gjenkjennelige annonsekort. Markup kan være endret; ingenting importert."
        )
    return cards


def accessory_title(title: str) -> bool:
    text = re.sub(r"^[^\w]+", "", title.casefold())
    return bool(
        re.search(r"\bipad\b", text)
        or re.search(
            r"^(?:(?:garmin|apple)\s+)?(?:sett med.*reimer|(?:klokke)?reimer?\b|(?:ekstra lang )?ladekab|fri frakt.*ladekab|usb[- ]c til magsafe|ladere?\s+til)",
            text,
        )
    )


def product_facts(text: str, family: Family, cfg: Config) -> tuple[Product, list[str]]:
    text = text.casefold().replace("fēnix", "fenix").replace("fénix", "fenix")
    notes = []
    if family == "macbook":
        headline, separator, body = text.partition("\n")
        if separator:
            # Comparisons and the seller's replacement computer describe other products.
            # Keep the advertised product's statements, including genuine contradictions.
            sentences = re.split(r"(?<=[.!?])\s+", body)
            comparison = r"standardmodellen|standard modellen|til sammenligning|sammenlignet med|gjennom jobben|oppgradert til|bytter til"
            text = headline + "\n" + " ".join(s for s in sentences if not re.search(comparison, s))
        generations = set(re.findall(r"\bm([1-9])\b", text))
        generation = next(iter(generations)) if len(generations) == 1 else None
        model = (
            f"MacBook Air M{generation}"
            if generation and re.search(r"\bair\b", text)
            else "MacBook Air (uavklart)"
        )
        if re.search(r"\b(?:macbook\s+pro|m[1-9]\s+(?:pro|max|ultra))\b", text):
            model = "MacBook (annen modell)"
        ram = {int(v) for v in re.findall(r"\b(8|16|24|32|64)\s*gb\s*(?:ram|minne|memory|unified)", text)}
        ram.update(
            int(v) for v in re.findall(r"(?:ram|minne|memory)\s*[:=]?\s*(8|16|24|32|64)\s*(?:gb)?\b", text)
        )
        # Explicit small GB capacities on an Apple-chip Air refer to memory; storage
        # is parsed separately. Multiple distinct capacities still cause abstention.
        if generation in {"1", "2"} and model == f"MacBook Air M{generation}":
            ram.update(int(v) for v in re.findall(r"\b(8|16|24|32|64)\s*gb\b", text))
        pairs = re.findall(r"\b(8|16|24|32|64)\s*(?:gb)?\s*/\s*(256|512|1024|2048)\s*(?:gb)?\b", text)
        ram.update(int(a) for a, _ in pairs)
        ssds = {int(v) for v in re.findall(r"\b(256|512|1024|2048)\s*gb\b", text)}
        ssds.update(int(b) for _, b in pairs)
        ssds.update(int(v) * 1024 for v in re.findall(r"\b(1|2)\s*tb\b", text))
        sizes = {int(v) for v in re.findall(r"\b(13|15)(?:[.,]\d+)?\s*(?:[\"”″'’‘]|tomm|inch)", text)}
        if re.search(r"\b15(?:[.,]\d+)?\s*(?:[\"”″'’‘]|tomm|inch)", text):
            sizes.add(15)
        year = (
            "2020"
            if generation == "1" and re.search(r"\b2020\b", text)
            else "2022"
            if generation == "2" and re.search(r"\b2022\b", text)
            else None
        )
        variant = f"13-inch {year}" if sizes == {13} and year else None
        # Apple documents one M1 Air generation: 2020, 13-inch. RAM/SSD must still be stated.
        if (
            generation == "1"
            and model == "MacBook Air M1"
            and re.search(r"\bmacbook\s+air\b", text)
            and 15 not in sizes
        ):
            variant = "13-inch 2020"
        p = Product(
            family=family,
            brand="Apple",
            model=model,
            variant=variant,
            ram_gb=next(iter(ram)) if len(ram) == 1 else None,
            ssd_gb=next(iter(ssds)) if len(ssds) == 1 else None,
        )
        if len(ram) != 1:
            notes.append("RAM mangler eller er tvetydig i annonseteksten")
        if len(ssds) != 1:
            notes.append("SSD mangler eller er tvetydig i annonseteksten")
        if not variant:
            notes.append("Skjermstørrelse/årsvariant må avklares")
    else:
        found = re.findall(r"\b(?:forerunner\s*(?:955|965)|fenix\s*7(?:s|x)?)(?:\s+pro)?\b", text)
        names = {re.sub(r"\s+", " ", value) for value in found}
        model = next(iter(names)) if len(names) == 1 else "Garmin (uavklart)"
        if model.startswith("fenix"):
            model = model.replace("fenix", "fēnix").replace("7s", "7S").replace("7x", "7X")
        elif model.startswith("forerunner"):
            model = model.replace("forerunner", "Forerunner")
        if re.search(r"\b(?:solar|sapphire|safir)\b", text):
            variant = "Solar/Sapphire (må avklares)"
        else:
            variant = (
                "standard"
                if re.search(r"\b(?:standard|standardmodell|ikke solar|non[- ]solar)\b", text)
                else None
            )
        sizes = {int(v) for v in re.findall(r"\b(\d{2})\s*mm\b", text)}
        p = Product(
            family=family,
            brand="Garmin",
            model=model,
            variant=variant,
            size_mm=next(iter(sizes)) if len(sizes) == 1 else None,
        )
        if not variant:
            notes.append("Garmin-variant må avklares; standard antas ikke fra fravær av Solar")
        if p.size_mm is None:
            notes.append("Eksakt klokkestørrelse mangler")
    return p, notes


def price_meaning(text: str) -> str:
    text = text.casefold()
    for kind, pattern in [
        ("installment", r"delbetaling|avdrag|/mnd|kr\s*(?:pr\.?|per)\s*m[åa]ned"),
        ("wanted", r"ønskes kjøpt|\bwtb\b"),
        ("from", r"\bfra\s+\d+\s*(?:kr|,-)"),
        ("component", r"kun (?:lader|skjerm|reim)|selges som deler"),
        ("bundle", r"pakkepris|\bbundle\b|selges samlet|\bpakke\b"),
    ]:
        if re.search(pattern, text):
            return kind
    return "unit"


def parse_detail(
    html: str,
    card: SearchCard,
    family: Family,
    cfg: Config,
    received_at: datetime,
    seller_type: str = "unknown",
) -> tuple[Candidate, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    product = None
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(tag.string or tag.get_text())
            values = obj if isinstance(obj, list) else obj.get("@graph", [obj])
            product = next(
                (
                    v
                    for v in values
                    if isinstance(v, dict) and v.get("@type") == "Product" and str(v.get("sku")) == card.id
                ),
                None,
            )
            if product:
                break
        except (ValueError, AttributeError):
            continue
    if not product:
        raise ValueError("Annonsesiden mangler gjenkjennelig produktinformasjon")
    offers = product.get("offers", {})
    if not isinstance(offers, dict):
        raise ValueError("Uventet prisformat på annonsesiden")
    if offers.get("priceCurrency") != "NOK":
        raise ValueError("Pris mangler eller har annen valuta enn NOK")
    price = parse_price(str(offers.get("price", "")))
    if price is None:
        raise ValueError("Kan ikke tolke enhetspris på annonsesiden")
    title = visible_text(soup.select_one('[data-testid="object-title"]')) or product.get("name", card.title)
    description = visible_text(soup.select_one('[data-testid="description"] .whitespace-pre-wrap'))
    text = title + "\n" + description
    facts, notes = product_facts(text, family, cfg)
    condition = "unknown"
    for para in soup.select("p"):
        value = visible_text(para)
        if value.startswith("Tilstand"):
            lower = value.casefold()
            condition = (
                "damaged"
                if "må fikses" in lower
                else "fair"
                if "godt brukt" in lower
                else "excellent"
                if "som ny" in lower or "helt ny" in lower
                else "good"
                if "pent brukt" in lower
                else "unknown"
            )
            break
    info = visible_text(soup.select_one('[data-testid="object-info"]'))
    updated = re.search(r"Sist endret\s*:\s*(\d{2}\.\d{2}\.\d{4})\s+kl\.\s*(\d{2}:\d{2})", info)
    updated_at = (
        datetime.strptime(" ".join(updated.groups()), "%d.%m.%Y %H:%M").replace(tzinfo=OSLO)
        if updated
        else None
    )
    published_at = None
    if product.get("datePublished"):
        try:
            parsed = datetime.fromisoformat(product["datePublished"].replace("Z", "+00:00"))
            if parsed.tzinfo and parsed <= received_at:
                published_at = parsed
        except (ValueError, TypeError):
            pass
    flags = []
    if re.search(
        r"\b(?:defekt|knust|vannskad\w*|skjermsprekk|activation lock|icloud[- ]?l[åa]s|mdm[- ]?l[åa]s)\b",
        text,
        re.I,
    ):
        flags.append("Mulig alvorlig skade eller lås omtalt; må kontrolleres")
    if card.price is not None and card.price != price:
        notes.append("Pris endret mellom søk og annonseside; bruker prisen fra annonsesiden")
    availability = (
        "removed"
        if any(
            value in str(offers.get("availability", ""))
            for value in ["OutOfStock", "Discontinued", "SoldOut"]
        )
        else "active"
    )
    return Candidate(
        id=card.id,
        source="finn_public",
        entity_id=f"finn-item-{card.id}",
        url=card.url,
        title=title[:250],
        product=facts,
        price=price,
        condition=condition,
        demo=False,
        location=card.location[:100],
        received_at=received_at,
        published_at=published_at,
        updated_at=updated_at,
        seller_type=seller_type,
        availability=availability,
        price_meaning=price_meaning(text),
        risk_flags=flags,
        shipping_possible=soup.select_one('[data-testid="ship-it-badge"]') is not None,
    ), notes


class PublicHTMLClient:
    def __init__(self, options: ScrapeConfig):
        self.options = options
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "FinnFlippemaskin/0.2 (local public-page analysis)", "Accept": "text/html"}
        )
        self.last_request = None
        self.requests = 0

    def get(self, url: str) -> str:
        validate_public_url(url, search=urlsplit(url).path.rstrip("/") == "/recommerce/forsale/search")
        for _ in range(4):
            if self.last_request is not None:
                delay = self.options.request_delay_seconds - (time.monotonic() - self.last_request)
                if delay > 0:
                    time.sleep(delay)
            self.last_request = time.monotonic()
            self.requests += 1
            with self.session.get(
                url, timeout=(10, self.options.timeout_seconds), stream=True, allow_redirects=False
            ) as response:
                if response.status_code in {401, 403, 429}:
                    raise SourceBlocked(
                        f"FINN svarte HTTP {response.status_code}; innhenting stoppet, ny prøve tidligst om én time"
                    )
                if response.status_code in {404, 410} and ITEM_PATH.fullmatch(urlsplit(url).path):
                    raise PageRemoved("Annonsen er ikke lenger offentlig tilgjengelig; oppgjør er ukjent")
                if response.is_redirect:
                    target = urljoin(url, response.headers.get("Location", ""))
                    try:
                        validate_public_url(
                            target, search=urlsplit(target).path.rstrip("/") == "/recommerce/forsale/search"
                        )
                    except ValueError:
                        raise SourceBlocked(
                            "FINN videresendte til innlogging eller en annen side; innhenting stoppet"
                        ) from None
                    url = target
                    continue
                response.raise_for_status()
                if "text/html" not in response.headers.get("Content-Type", ""):
                    raise ValueError("Forventet offentlig HTML fra FINN")
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > 5 * 1024 * 1024:
                        raise ValueError("FINN-siden overskrider 5 MiB")
                html = body.decode("utf-8", errors="replace")
                if re.search(r"<title>[^<]*(?:captcha|access denied|just a moment)", html, re.I):
                    raise SourceBlocked("FINN viser en tilgangs-/verifiseringsside; innhenting stoppet")
                return html
        raise ValueError("For mange videresendinger fra FINN")

    def close(self):
        self.session.close()


class PublicFinnAdapter(SourceAdapter):
    def __init__(self, store: Store, cfg: Config, options: ScrapeConfig, client=None):
        self.store, self.cfg, self.options = store, cfg, options
        self.client = client or PublicHTMLClient(options)
        self.references = []
        self.report = {
            "candidates": 0,
            "references": 0,
            "requests": 0,
            "cache_hits": 0,
            "errors": [],
            "searches": [],
            "skipped_accessories": 0,
        }

    def load(self, kind: str):
        if kind == "references":
            return self.references, self.provenance()
        if kind != "candidates":
            raise ValueError("Ukjent importtype")
        existing = {f"{c.source}:{c.id}": c for c in self.store.observations("candidates")}
        metadata = self.store.live_items()
        candidates = []
        seen = set()
        for search in self.options.searches:
            html = self.client.get(search.url)
            cards = parse_search(html, search.url)
            self.report["skipped_accessories"] += sum(accessory_title(c.title) for c in cards)
            cards = [c for c in cards if not c.promoted and not accessory_title(c.title)][
                : search.limit or self.options.items_per_search
            ]
            self.report["searches"].append({"name": search.name, "url": search.url, "cards": len(cards)})
            for card in cards:
                if card.id in seen:
                    continue
                seen.add(card.id)
                key = f"finn_public:{card.id}"
                old, meta = existing.get(key), metadata.get(key, {})
                checked = meta.get("detail_checked_at")
                now = utcnow()
                try:
                    if (
                        old
                        and old.availability == "active"
                        and card.price == old.price
                        and checked
                        and meta.get("parser_version") == PARSER_VERSION
                        and now - datetime.fromisoformat(checked)
                        < timedelta(minutes=self.options.detail_refresh_minutes)
                        and not meta.get("last_error")
                    ):
                        candidate = old
                        notes = meta.get("notes", [])
                        self.report["cache_hits"] += 1
                        checked_at = None
                    else:
                        received = old.received_at if old else now
                        detail = self.client.get(card.url)
                        query = parse_qs(urlsplit(search.url).query)
                        # Verified through FINN's visible Privat/forhandler filter on 19 Oct 2026.
                        seller = "private" if query.get("dealer_segment") == ["1"] else "unknown"
                        candidate, notes = parse_detail(
                            detail, card, search.family, self.cfg, received, seller
                        )
                        checked_at = utcnow()
                    candidates.append(candidate)
                    self.store.see_live_item(
                        key,
                        search.name,
                        notes,
                        checked_at,
                        parser_version=PARSER_VERSION if checked_at else None,
                    )
                    if (
                        candidate.availability == "active"
                        and candidate.condition not in {"unknown", "damaged"}
                        and candidate.price_meaning == "unit"
                    ):
                        self.references.append(
                            Reference(
                                **{
                                    k: getattr(candidate, k)
                                    for k in [
                                        "id",
                                        "source",
                                        "entity_id",
                                        "url",
                                        "title",
                                        "product",
                                        "price",
                                        "currency",
                                        "condition",
                                        "demo",
                                    ]
                                },
                                kind="asking",
                                seller_type=candidate.seller_type,
                                observed_at=now,
                                known_at=now,
                                documentation="Offentlig FINN-annonse: prisantydning observert ved innhenting, ikke bekreftet oppgjør.",
                            )
                        )
                except PageRemoved:
                    if old:
                        candidates.append(old.model_copy(update={"availability": "removed"}))
                    self.store.see_live_item(
                        key,
                        search.name,
                        ["Annonsen er borte; faktisk salg/oppgjør er ukjent"],
                        None,
                        "removed",
                    )
                except SourceBlocked:
                    raise
                except (ValueError, requests.RequestException) as exc:
                    self.report["errors"].append({"id": card.id, "error": type(exc).__name__})
                    self.store.see_live_item(
                        key,
                        search.name,
                        ["Kunne ikke lese produktfakta fra annonsen"],
                        None,
                        type(exc).__name__,
                    )
        self.report.update(
            candidates=len(candidates), references=len(self.references), requests=self.client.requests
        )
        return candidates, self.provenance()

    def provenance(self):
        return {
            "type": "PUBLIC_FINN_HTML",
            "parser_version": PARSER_VERSION,
            "authority": "Anders ba uttrykkelig om nettskraping 19. oktober 2026. Dette er ikke en FINN-avtale.",
            "searches": [s.model_dump(mode="json") for s in self.options.searches],
            "report": self.report,
        }


def scrape_once(store: Store, cfg: Config, options: ScrapeConfig, client=None) -> dict:
    run_id = store.reserve_scrape(options.min_interval_seconds)
    adapter = PublicFinnAdapter(store, cfg, options, client)
    try:
        candidates, provenance = adapter.load("candidates")
        refs, _ = adapter.load("references")
        removed_ids = {c.id for c in candidates if c.availability == "removed"}
        refs.extend(
            r.model_copy(update={"availability": "removed", "known_at": utcnow()})
            for r in store.observations("references")
            if r.source == "finn_public" and r.id in removed_ids
        )
        adapter.report["candidate_revisions"] = store.import_rows("candidates", candidates, provenance)
        adapter.report["reference_revisions"] = store.import_rows("references", refs, provenance)
        from .notifications import export_drafts, prepare_outbox
        from .service import run_analysis

        assessments = run_analysis(store, cfg)
        adapter.report["drafts"] = prepare_outbox(store, assessments, cfg)
        export_drafts(store, store.path.parent / "drafts")
        store.finish_scrape(run_id, "partial" if adapter.report["errors"] else "ok", adapter.report)
        return adapter.report
    except (ValueError, requests.RequestException) as exc:
        adapter.report["error"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        adapter.report["requests"] = adapter.client.requests
        store.finish_scrape(run_id, "blocked" if isinstance(exc, SourceBlocked) else "failed", adapter.report)
        raise
    except KeyboardInterrupt:
        store.finish_scrape(
            run_id, "stopped", {"error": "Stoppet av bruker", "requests": adapter.client.requests}
        )
        raise
    finally:
        adapter.client.close()
