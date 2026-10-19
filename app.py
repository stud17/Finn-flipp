"""Start med: .venv/bin/python -m streamlit run app.py"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import streamlit as st
from pydantic import ValidationError

from finnflip.engine import WEIGHTS
from finnflip.models import Costs, Feedback, Trade
from finnflip.morning import has_positive_economics
from finnflip.notifications import export_drafts, prepare_outbox, reconcile_pending, suppression_keys
from finnflip.scraper import accessory_title, load_scrape_config, scrape_once
from finnflip.service import ROOT, comparison_csv, load_config, load_demo, run_analysis
from finnflip.storage import Store

st.set_page_config(page_title="FINN · Flippemaskin", page_icon="↗", layout="wide")
cfg = load_config()
store = Store(ROOT / "data/finnflip.sqlite")
live_items = store.live_items()
oslo = ZoneInfo("Europe/Oslo")
STATUS_LABELS = {
    "irrelevant": "Uinteressant",
    "wrong_model": "Feil modell",
    "gone": "Allerede borte",
    "investigated": "Undersøkt",
    "bought": "Kjøpt",
    "sold": "Solgt",
    "returned": "Returnert",
    "loss": "Tap",
    "inventory": "På lager",
}


def nok(value):
    return f"{value:,.0f} kr".replace(",", " ") if value is not None else "Kan ikke vurderes"


def stamp(value):
    return value.astimezone(oslo).strftime("%d.%m.%Y %H:%M") if value else "ukjent"


def record_safely(action):
    try:
        action()
        st.success("Lagret lokalt")
    except (ValueError, ValidationError):
        st.error("Kontroller feltene. Avsluttet handel må ha faktisk oppgjør og en dato etter kjøpet.")


with st.sidebar:
    st.markdown("### FINN / Flippemaskin")
    st.caption("LOKAL PILOT · OFFENTLIGE FINN-SIDER")
    st.write(f"{cfg.location} · {cfg.radius_km} km")
    st.caption(f"Timeverdi {cfg.hourly_value} kr · min. ROI {cfg.min_roi:.0%}")
    st.caption(
        f"Kapitalramme: {nok(cfg.capital_limit) if cfg.capital_limit is not None else 'ikke fastsatt'}"
    )
    if st.button("Last inn demo", width="stretch"):
        load_demo(store, cfg)
        st.rerun()
    if st.button("Beregn på nytt", width="stretch"):
        run_analysis(store, cfg)
        st.rerun()
    if st.button("Hent fra FINN nå", width="stretch", type="primary"):
        import requests

        try:
            with st.spinner("Henter offentlige søkesider og produktopplysninger …"):
                report = scrape_once(store, cfg, load_scrape_config(ROOT / "scrape.json"))
            st.session_state["scrape_message"] = (
                f"Hentet {report['candidates']} annonser fra FINN. {len(report['errors'])} annonser kunne ikke leses."
            )
        except (ValueError, requests.RequestException) as exc:
            st.session_state["scrape_error"] = (
                str(exc) if isinstance(exc, ValueError) else "Nettverksfeil ved innhenting. Prøv senere."
            )
        st.rerun()
    st.divider()
    positive_only = st.checkbox("Kun positive økonomiske anslag", value=True)
    st.caption("Overskudd etter kostnader, risikoreserve og tidsbruk må være større enn 0 kr.")
    family = st.selectbox("Produktfamilie", ["Alle", "macbook", "garmin"])
    grades = st.multiselect("Klasse", ["A", "B", "C", "D", "U"], default=["A", "B", "C", "D", "U"])
    origin = st.selectbox("Datagrunnlag", ["Alle", "Demo", "Egne data", "FINN"], index=3 if live_items else 0)
    state = st.selectbox(
        "Oppfølgingsstatus",
        [
            "Alle",
            "Ubehandlet",
            "irrelevant",
            "wrong_model",
            "gone",
            "investigated",
            "bought",
            "sold",
            "returned",
            "loss",
        ],
        format_func=lambda value: STATUS_LABELS.get(value, value),
    )
    st.divider()
    st.caption(
        "FINN hentes fra offentlige sider. Oppdater med knappen over. Planlagt kjøring settes opp for miljøet som brukes."
    )

st.title("Finn muligheter. Regn på hele handelen.")
st.caption("Prisestimat → kostnader og tidsbruk → kontroll → registrert utfall")
if "scrape_message" in st.session_state:
    st.success(st.session_state.pop("scrape_message"))
if "scrape_error" in st.session_state:
    st.warning(st.session_state.pop("scrape_error"))
last_scrape = store.latest_scrape()
if last_scrape:
    last_report = last_scrape["report"]
    st.caption(
        f"Siste FINN-innhenting: {stamp(datetime.fromisoformat(last_scrape['started_at']))} · {last_report.get('candidates', 0)} annonser · status {last_scrape['state']}"
    )
    if last_scrape["state"] in {"blocked", "failed", "partial"}:
        st.warning(last_report.get("error") or "Enkelte annonser kunne ikke leses. Tidligere data er bevart.")
all_assessments = store.assessments()
if not all_assessments:
    st.info("Velg «Hent fra FINN nå» for ekte annonser, eller «Last inn demo» for syntetiske eksempler.")
    st.stop()
feedback = {f.candidate_key: f for f in store.feedback_rows()}
suppressed = suppression_keys(store)
assessments = [
    a
    for a in all_assessments
    if (family == "Alle" or a.candidate.product.family == family)
    and a.grade in grades
    and (
        origin == "Alle"
        or (
            origin == "FINN"
            and a.candidate.source == "finn_public"
            and not accessory_title(a.candidate.title)
        )
        or (origin == "Demo" and a.candidate.demo)
        or (origin == "Egne data" and not a.candidate.demo)
    )
    and (
        state == "Alle"
        or (state == "Ubehandlet" and a.candidate_key not in feedback)
        or (a.candidate_key in feedback and feedback[a.candidate_key].status == state)
    )
]
checked_count = len(assessments)
valued_count = sum(a.economic_profit is not None for a in assessments)
if positive_only:
    assessments = [a for a in assessments if has_positive_economics(a) and a.candidate_key not in suppressed]
    assessments.sort(key=lambda a: a.economic_profit, reverse=True)
if any(a.candidate.demo for a in assessments):
    st.warning(
        "DEMO er syntetiske data. Resultatene dokumenterer programfunksjon; markedsmulighet og lønnsomhet er utestet."
    )
cols = st.columns(4)
cols[0].metric("Positive muligheter" if positive_only else "Kandidater i utvalget", len(assessments))
cols[1].metric(
    "Annonser vurdert" if positive_only else "Med gevinstestimat",
    checked_count if positive_only else sum(a.cash_gain is not None for a in assessments),
)
if positive_only:
    cols[2].metric("Med økonomisk prisanslag", valued_count)
    cols[3].metric("Beste økonomiske anslag", nok(assessments[0].economic_profit) if assessments else "—")
else:
    cols[2].metric(
        "Positivt økonomisk anslag",
        sum(a.economic_profit is not None and a.economic_profit > 0 for a in assessments),
    )
    cols[3].metric("Krever avklaring · U", sum(a.grade == "U" for a in assessments))
if origin == "FINN":
    st.caption(
        "Gjenkjent tilbehør er skjult i FINN-visningen. Velg «Alle» for også å se tidligere tilbehørstreff. Manglende modellfakta og svakt prisgrunnlag gir U, uten påstått gevinst."
    )
overview, mailbox, journal, settings = st.tabs(
    ["Muligheter", "E-postutkast", "Handelslogg og læring", "Forutsetninger"]
)
with overview:
    if not assessments:
        st.info(
            "Ingen annonser med positivt økonomisk anslag nå. Annonser med underskudd eller utilstrekkelig prisgrunnlag er skjult."
            if positive_only
            else "Ingen kandidater matcher filtrene."
        )
    first_valued_key = next((a.candidate_key for a in assessments if a.cash_gain is not None), None)
    for a in assessments:
        c = a.candidate
        title = c.title.removeprefix("DEMO ") if c.demo else c.title
        with st.expander(
            f"{a.grade} · {'DEMO · ' if c.demo else 'FINN · ' if c.source == 'finn_public' else ''}{title} · {nok(c.price)} · score {a.score if a.score is not None else '—'}",
            expanded=a.grade == "A" or a.candidate_key == first_valued_key,
        ):
            st.write(f"**{a.product_id or 'Variant uavklart'}** · {c.location} · sikkerhet: {a.confidence}")
            if c.source == "finn_public":
                st.caption(
                    f"Leste produktfakta: {c.product.model} · variant {c.product.variant or 'ukjent'} · "
                    + (
                        f"RAM {c.product.ram_gb or 'ukjent'} GB · SSD {c.product.ssd_gb or 'ukjent'} GB"
                        if c.product.family == "macbook"
                        else f"størrelse {c.product.size_mm or 'ukjent'} mm"
                    )
                )
            if a.candidate_key in feedback:
                st.caption(
                    f"Registrert oppfølging: {STATUS_LABELS[feedback[a.candidate_key].status]}. Tallene under er den lagrede vurderingen."
                )
            st.link_button("Åpne annonselenke manuelt", c.url)
            x, y, z = st.columns(3)
            x.metric("Anslått kontantgevinst", nok(a.cash_gain))
            y.metric("Økonomisk overskudd", nok(a.economic_profit))
            z.metric("10 % lavere videresalg", nok(a.stress_profit))
            if a.resale_low is not None:
                st.write(
                    f"Anslått videresalgsintervall: **{nok(a.resale_low)} – {nok(a.resale_high)}** · avkastning {a.roi:.1%}"
                )
                st.write(
                    f"Maks kjøpspris for gevinst og avkastning: **{nok(a.max_purchase)}**; økonomisk overskudd da {nok(a.economic_at_max_purchase)}."
                )
                st.caption(f"Maks kjøpspris med positivt økonomisk overskudd: {nok(a.max_purchase_economic)}")
            for reason in a.reasons:
                st.write(reason)
            meta = live_items.get(a.candidate_key)
            if meta:
                for note in meta["notes"]:
                    st.caption(note)
                st.caption(
                    f"Sist sett i FINN-søket: {stamp(datetime.fromisoformat(meta['seen_at']))} · sist endret hos FINN: {stamp(c.updated_at)}"
                )
            for control in a.controls:
                st.warning(control)
            st.caption(
                f"Publisert {stamp(c.published_at)} · mottatt {stamp(c.received_at)} · vurdert {stamp(a.evaluated_at)}"
            )
            st.caption(
                "Annonsealder: "
                + (
                    f"{(a.evaluated_at - c.published_at).total_seconds() / 3600:.1f} timer"
                    if c.published_at
                    else "ukjent"
                )
            )
            detail, refs, history, followup = st.tabs(
                ["Beregning", "Referanser", "Historikk", "Registrer oppfølging"]
            )
            with detail:
                st.write("Antakelser")
                for assumption in a.assumptions:
                    st.write("• " + assumption)
                if a.costs:
                    st.json(a.costs.model_dump(mode="json"))
                if a.components:
                    st.dataframe(
                        [
                            {
                                "Del": k,
                                "Delscore": float(v),
                                "Vekt": f"{WEIGHTS[k]:.0%}",
                                "Bidrag": float(v * WEIGHTS[k]),
                            }
                            for k, v in a.components.items()
                        ],
                        hide_index=True,
                    )
                st.caption(f"Beregning {a.calculation_version} · konfigurasjon {a.config_hash[:12]}")
                st.download_button(
                    "Last ned etterprøvbar vurdering",
                    a.model_dump_json(indent=2),
                    file_name=f"assessment-{c.source}-{c.id}.json",
                    key=f"download-{a.candidate_key}",
                )
            with refs:
                st.json(a.reference_stats)
                st.dataframe(
                    [
                        {
                            "ID": f"{r.source}:{r.id}",
                            "Type": r.kind,
                            "Pris NOK": float(r.price),
                            "Observert": stamp(r.observed_at),
                            "Kjent": stamp(r.known_at),
                            "Dokumentasjon": r.documentation,
                            "Lenke": r.url,
                        }
                        for r in a.references
                    ],
                    hide_index=True,
                )
            with history:
                st.dataframe(
                    [
                        {
                            "Revisjon": h["revision"],
                            "Registrert": h["recorded_at"],
                            "Annonsert pris": h["candidate"]["price"],
                        }
                        for h in store.history(a.candidate_key)
                    ],
                    hide_index=True,
                )
            with followup:
                with st.form(f"feedback-{a.candidate_key}"):
                    status = st.selectbox(
                        "Utfall",
                        [
                            "investigated",
                            "irrelevant",
                            "wrong_model",
                            "gone",
                            "bought",
                            "sold",
                            "returned",
                            "loss",
                        ],
                        format_func=lambda value: STATUS_LABELS[value],
                    )
                    usable = st.selectbox("Brukbar etter kontroll?", ["Ikke vurdert", "Ja", "Nei"])
                    minutes = st.number_input(
                        "Minutter brukt ved denne oppfølgingen", min_value=0.0, value=0.0, step=1.0
                    )
                    if st.form_submit_button("Lagre tilbakemelding"):
                        record_safely(
                            lambda: store.feedback(
                                Feedback(
                                    candidate_key=a.candidate_key,
                                    status=status,
                                    usable={"Ikke vurdert": None, "Ja": True, "Nei": False}[usable],
                                    review_minutes=Decimal(str(minutes)),
                                    demo=c.demo,
                                )
                            )
                        )

with mailbox:
    st.write("A får eget prioritert utkast. B samles i én rapport. U sendes ikke som kupp.")
    if st.button("Lag nye e-postutkast"):
        n = prepare_outbox(store, run_analysis(store, cfg), cfg)
        export_drafts(store, ROOT / "data/drafts")
        st.session_state["drafts_created"] = n
        st.rerun()
    if "drafts_created" in st.session_state:
        st.success(f"{st.session_state.pop('drafts_created')} nye utkast. Ingen e-post er sendt.")
    reconcile_pending(store, all_assessments)
    for row in store.outbox():
        with st.expander(f"{row['state']} · {row['subject']}"):
            st.text(row["text_body"])
            st.download_button(
                "Last ned HTML",
                row["html_body"],
                file_name=f"draft-{row['id']}.html",
                mime="text/html",
                key=f"mail-{row['id']}",
            )
            st.caption(f"Forsøk {row['attempts']} · feiltype {row['error'] or 'ingen'}")

with journal:
    st.write("Beregnet gevinst ligger i vurderingene. Faktiske oppgjør og usolgt lager vises her separat.")
    trades = store.trades()
    for demo in (False, True):
        subset = [t for t in trades if t.demo == demo]
        st.markdown("**DEMO-handler**" if demo else "**Faktiske handler**")
        if not subset:
            st.caption("Ingen handler registrert. Ingen realisert fortjeneste er målt.")
        else:
            st.dataframe(
                [
                    {
                        "Kandidat": t.candidate_key,
                        "Status": STATUS_LABELS[t.status],
                        "Realisert kontantgevinst": nok(t.result()["cash_gain"])
                        if t.sale is not None
                        else "Ikke realisert",
                        "Økonomisk resultat": nok(t.result()["economic_profit"])
                        if t.sale is not None
                        else "Ikke realisert",
                        "Kapital bundet": nok(t.result()["capital_bound"]),
                        "Forsiktig lagerverdi": nok(t.inventory_value)
                        if t.status == "inventory" and t.inventory_value is not None
                        else "—",
                    }
                    for t in subset
                ],
                hide_index=True,
            )
            st.caption(
                f"Realisert økonomisk resultat: {nok(sum((t.result()['economic_profit'] or Decimal(0)) for t in subset))} · kapital bundet: {nok(sum(t.result()['capital_bound'] for t in subset))}"
            )
    keys = [a.candidate_key for a in all_assessments]
    with st.form("trade"):
        st.write("Registrer eller oppdater én handel per kandidat")
        key = st.selectbox("Kandidat", keys)
        trade_status = st.selectbox(
            "Lagerstatus",
            ["inventory", "sold", "returned", "loss"],
            format_func=lambda value: STATUS_LABELS[value],
        )
        x, y, z = st.columns(3)
        purchase = x.number_input("Faktisk kjøpspris", min_value=0.0, step=100.0)
        sale = y.number_input("Faktisk oppgjør ved avslutning (0 ved fullt tap)", min_value=0.0, step=100.0)
        direct = z.number_input("Samlede faktiske direkte kostnader", min_value=0.0, step=10.0)
        x, y, z = st.columns(3)
        hours = x.number_input("Faktiske arbeidstimer", min_value=0.0, step=0.25)
        overhead = y.number_input("Fordelt drift", min_value=0.0, step=10.0)
        capital_cost = z.number_input("Faktisk kapitalkostnad", min_value=0.0, step=10.0)
        inventory_value = st.number_input("Forsiktig lagerverdi (0 hvis ukjent)", min_value=0.0, step=100.0)
        x, y = st.columns(2)
        bought_date = x.date_input("Kjøpsdato")
        closed_date = y.date_input("Avslutningsdato")
        confirmed = st.checkbox(
            "Jeg har kontrollert beløpene. Dette erstatter eventuell tidligere registrering for kandidaten."
        )
        if st.form_submit_button("Lagre handel"):
            if not confirmed:
                st.error("Kontroller og bekreft beløpene før lagring.")
            else:
                candidate = next(a.candidate for a in all_assessments if a.candidate_key == key)
                record_safely(
                    lambda: store.save_trade(
                        Trade(
                            candidate_key=key,
                            bought_at=datetime.combine(bought_date, time(), oslo),
                            purchase=Decimal(str(purchase)),
                            costs=Costs(
                                transport=Decimal(str(direct)),
                                hours=Decimal(str(hours)),
                                overhead=Decimal(str(overhead)),
                                capital_cost=Decimal(str(capital_cost)),
                            ),
                            hourly_value=cfg.hourly_value,
                            status=trade_status,
                            sale=Decimal(str(sale)) if trade_status != "inventory" else None,
                            closed_at=datetime.combine(closed_date, time(), oslo)
                            if trade_status != "inventory"
                            else None,
                            inventory_value=Decimal(str(inventory_value)) or None,
                            demo=candidate.demo,
                        )
                    )
                )
    st.divider()
    st.caption(
        "Baseline: faste prisgrenser per eksakt variant, med samme inndata. CSV inneholder rangering, menneskelige etiketter og kontrolltid når de finnes. Tomme etiketter er ikke målt nøyaktighet."
    )
    st.download_button(
        "Last ned sammenligning (CSV)",
        comparison_csv(store).encode("utf-8-sig"),
        "comparison.csv",
        "text/csv",
    )

with settings:
    st.write("Endre config.json og trykk «Beregn på nytt». Verdiene er foreløpige pilotparametere.")
    st.json(cfg.model_dump(mode="json"))
    st.caption(
        "Eksakt samme tilstand og variant kreves. Forhandlerpriser brukes ikke. Annonsepriser og oppgjør blandes ikke. Alle beløp før inntektsskatt; MVA-behandling er uavklart."
    )
    st.write(
        "FINN-innhenting styres av scrape.json. Legg inn offentlige søke-URL-er med ønskede modell- og områdefiltre. Standardoppsettet søker landsdekkende; avstand er ikke automatisk kontrollert. Andre lokale data kan importeres via CLI."
    )
