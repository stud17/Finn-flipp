import json
from datetime import timedelta
from decimal import Decimal

import pytest
import requests

from finnflip.engine import evaluate
from finnflip.scraper import (
    PublicFinnAdapter,
    PublicHTMLClient,
    ScrapeConfig,
    SourceBlocked,
    parse_detail,
    parse_price,
    parse_search,
    price_meaning,
    product_facts,
    scrape_once,
    validate_public_url,
)

URL = "https://www.finn.no/recommerce/forsale/search?q=macbook%20air%20m1&sort=PUBLISHED_DESC"
ITEM = "https://www.finn.no/recommerce/forsale/item/123"


def search_html(price="3 000 kr", title="MacBook Air M1", promoted=False):
    return f'''<html><article class="sf-search-ad"><a class="sf-search-ad-link" href="{ITEM}"></a>
    <h2>{title}</h2><span>{price}</span><span class="whitespace-nowrap truncate">Oslo</span>
    {"<b>Betalt plassering</b>" if promoted else ""}</article></html>'''


def detail_html(
    description="MacBook Air M1 2020 13 inch 8GB RAM 256GB SSD",
    condition="Pent brukt - I god stand",
    availability="InStock",
):
    product = {
        "@type": "Product",
        "sku": "123",
        "name": "MacBook Air M1",
        "offers": {
            "price": "3000",
            "priceCurrency": "NOK",
            "availability": f"https://schema.org/{availability}",
        },
    }
    return f"""<html><script type="application/ld+json">{json.dumps(product)}</script>
    <template shadowrootmode="open"><h1 data-testid="object-title">MacBook Air M1</h1>
    <section data-testid="description"><div class="whitespace-pre-wrap"><p>{description}</p></div></section>
    <p>Tilstand: <b>{condition}</b></p><section data-testid="object-info"><p>Sist endret: 19.10.2026 kl. 12:00</p></section>
    <section>Selgernavn: MUST_NOT_STORE, telefon: 99999999, gateadresse: MUST_NOT_STORE</section></template></html>"""


@pytest.fixture
def options():
    return ScrapeConfig(searches=[{"name": "MacBook", "family": "macbook", "url": URL}], items_per_search=2)


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.requests = 0
        self.closed = False

    def get(self, url):
        self.requests += 1
        result = self.pages[url]
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


def test_search_parser_uses_visible_card_fields_and_promotions():
    cards = parse_search(search_html(promoted=True), "https://www.finn.no")
    assert len(cards) == 1
    assert cards[0].price == 3000 and cards[0].id == "123"
    assert cards[0].location == "Oslo" and cards[0].promoted
    with pytest.raises(ValueError, match="Markup"):
        parse_search("<html>changed layout</html>", URL)
    assert parse_search("<html>0 treff</html>", URL) == []


@pytest.mark.parametrize(
    "text,value",
    [
        ("6 500 kr", "6500"),
        ("6 500 kr", "6500"),
        ("1.500,50 kr", "1500.50"),
        ("Gratis", "0"),
        ("fra 500 kr", None),
    ],
)
def test_prices_are_not_guessed(text, value):
    assert parse_price(text) == (Decimal(value) if value is not None else None)


def test_declarative_shadow_dom_and_data_minimization(cfg, at):
    card = parse_search(search_html(), URL)[0]
    c, notes = parse_detail(detail_html(), card, "macbook", cfg, at)
    assert c.title == "MacBook Air M1" and c.price == 3000
    assert c.product.ram_gb == 8 and c.product.ssd_gb == 256 and c.product.variant == "13-inch 2020"
    assert c.condition == "good" and c.published_at is None and c.updated_at is not None
    assert c.seller_type == "unknown" and not c.inspected and c.activation_lock == "unknown"
    assert "MUST_NOT_STORE" not in c.model_dump_json() and "99999999" not in c.model_dump_json()
    assert not notes


def test_missing_and_contradictory_ram_size_and_variant(cfg, at):
    c, _ = parse_detail(
        detail_html(description="MacBook Air M1 2020 13 inch 256GB SSD"),
        parse_search(search_html(), URL)[0],
        "macbook",
        cfg,
        at,
    )
    assert c.product.ram_gb is None
    assert evaluate(c, [], cfg, at).grade == "U"
    product, _ = product_facts("MacBook Air M2 2022 15 inch 8GB RAM 256GB SSD", "macbook", cfg)
    assert product.variant is None
    product, _ = product_facts("MacBook Air M1 2020 13 inch 8GB RAM eller 16GB RAM 256GB SSD", "macbook", cfg)
    assert product.ram_gb is None
    product, _ = product_facts("Garmin Forerunner 955 Solar 46mm", "garmin", cfg)
    assert product.variant != "standard"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.finn.no/recommerce/forsale/item/123",
        "https://www.finn.no.evil.invalid/recommerce/forsale/item/123",
        "https://localhost/recommerce/forsale/item/123",
        "https://www.finn.no/api/",
        "https://user:password@www.finn.no/recommerce/forsale/item/123",
    ],
)
def test_only_public_finn_pages_allowed(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_scrape_integration_and_caching(store, cfg, options, at, monkeypatch):
    import finnflip.scraper

    monkeypatch.setattr(finnflip.scraper, "utcnow", lambda: at)
    client = FakeClient({URL: search_html(), ITEM: detail_html()})
    report = scrape_once(store, cfg, options, client)
    assert report["candidates"] == 1 and report["requests"] == 2 and report["errors"] == []
    assert client.closed and store.latest_scrape()["state"] == "ok"
    c = store.observations("candidates", at)[0]
    assert c.source == "finn_public" and not c.demo
    assert store.observations("references", at)[0].kind == "asking"
    with pytest.raises(ValueError, match="Vent"):
        scrape_once(store, cfg, options, FakeClient({}))
    adapter = PublicFinnAdapter(store, cfg, options, FakeClient({URL: search_html()}))
    rows, _ = adapter.load("candidates")
    assert adapter.report["cache_hits"] == 1 and rows[0].received_at == c.received_at
    assert adapter.client.requests == 1


def test_price_change_refreshes_detail_and_preserves_first_receipt(store, cfg, options, at, monkeypatch):
    import finnflip.scraper

    monkeypatch.setattr(finnflip.scraper, "utcnow", lambda: at)
    first = PublicFinnAdapter(store, cfg, options, FakeClient({URL: search_html(), ITEM: detail_html()}))
    rows, _ = first.load("candidates")
    store.import_rows("candidates", rows, {}, at)
    changed = detail_html().replace('"3000"', '"2500"')
    second = PublicFinnAdapter(
        store, cfg, options, FakeClient({URL: search_html(price="2500 kr"), ITEM: changed})
    )
    rows, _ = second.load("candidates")
    assert rows[0].price == 2500 and rows[0].received_at == at
    assert second.client.requests == 2


def test_source_blocks_have_backoff_and_never_attempt_another_route(store, cfg, options, at, monkeypatch):
    import finnflip.scraper

    monkeypatch.setattr(finnflip.scraper, "utcnow", lambda: at)
    blocked = FakeClient({URL: SourceBlocked("HTTP 429")})
    with pytest.raises(SourceBlocked):
        scrape_once(store, cfg, options, blocked)
    assert blocked.requests == 1 and blocked.closed and store.latest_scrape()["state"] == "blocked"
    assert store.observations("candidates", at) == []
    with pytest.raises(ValueError, match="Vent"):
        store.reserve_scrape(300, at + timedelta(minutes=10))


def test_removed_is_never_a_confirmed_sale(cfg, at):
    c, _ = parse_detail(
        detail_html(availability="SoldOut"), parse_search(search_html(), URL)[0], "macbook", cfg, at
    )
    assert c.availability == "removed"
    assert evaluate(c, [], cfg, at).cash_gain is None


def test_accessory_filter_keeps_watch_with_included_cable():
    from finnflip.scraper import accessory_title

    assert accessory_title("🔌⚡ Ladekabler til Garmin – USB-A og USB-C")
    assert accessory_title("Klokkereimer til Garmin Fenix 26 mm - Flere farger")
    assert accessory_title("Apple iPad Air M2")
    assert not accessory_title("Garmin Fenix 7 med ladekabel")


def test_removed_asking_references_not_used(candidates, refs, cfg, at):
    removed = [
        r.model_copy(update={"kind": "asking", "availability": "removed", "days_to_sell": None}) for r in refs
    ]
    assert evaluate(candidates["attractive"], removed, cfg, at).grade == "U"


def test_removed_listing_retires_old_asking_reference(store, cfg, options, at, monkeypatch):
    import finnflip.scraper
    from finnflip.models import Reference

    monkeypatch.setattr(finnflip.scraper, "utcnow", lambda: at)
    card = parse_search(search_html(), URL)[0]
    c, _ = parse_detail(detail_html(), card, "macbook", cfg, at)
    raw = {
        k: getattr(c, k)
        for k in ["id", "source", "entity_id", "url", "title", "product", "price", "condition", "demo"]
    }
    r = Reference(
        **raw,
        kind="asking",
        seller_type="private",
        observed_at=at,
        known_at=at,
        documentation="Test observed asking price",
    )
    store.import_rows("candidates", [c], {}, at)
    store.import_rows("references", [r], {}, at)
    scrape_once(
        store, cfg, options, FakeClient({URL: search_html(), ITEM: detail_html(availability="SoldOut")})
    )
    assert store.observations("references", at)[0].availability == "removed"
    assert store.observations("candidates", at)[0].availability == "removed"


class Response:
    def __init__(self, status=200, body=b"<html></html>", headers=None):
        self.status_code, self.body = status, body
        self.headers = headers or {"Content-Type": "text/html"}
        self.is_redirect = status in {301, 302, 307, 308}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, size):
        return iter([self.body])

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


@pytest.mark.parametrize(
    "response",
    [
        Response(status=403),
        Response(status=429),
        Response(status=302, headers={"Location": "https://login.example.invalid"}),
        Response(body=b"<title>Just a moment</title>"),
    ],
)
def test_transport_stops_at_blocks_or_login(options, monkeypatch, response):
    client = PublicHTMLClient(options)
    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: response)
    with pytest.raises(SourceBlocked):
        client.get(URL)
    assert client.requests == 1
    client.close()


def test_price_meaning_specifics():
    assert price_meaning("MacBook fra 299 kr/mnd delbetaling") == "installment"
    assert price_meaning("Pakke med to MacBook selges samlet") == "bundle"


def test_other_computers_in_description_do_not_override_advertised_configuration(cfg):
    text = "MacBook Air 13’ M2 2022 16/512GB\nSelger min MacBook Air M2 med 16 GB RAM og 512 GB SSD. Denne er bedre enn standardmodellen med 8 GB RAM. Jeg har nylig fått en MacBook med M5 gjennom jobben."
    p, _ = product_facts(text, "macbook", cfg)
    assert p.model == "MacBook Air M2" and p.ram_gb == 16 and p.ssd_gb == 512 and p.variant == "13-inch 2022"
    p, _ = product_facts("MacBook Air M1 8GB 256GB\nMaskinen har 16GB RAM og 256GB SSD.", "macbook", cfg)
    assert p.ram_gb is None


def test_explicit_memory_without_ram_label(cfg):
    p, _ = product_facts("MacBook Air M1 8GB 256GB", "macbook", cfg)
    assert p.ram_gb == 8 and p.ssd_gb == 256 and p.variant == "13-inch 2020"
    p, _ = product_facts("MacBook Air M1 256GB", "macbook", cfg)
    assert p.ram_gb is None
