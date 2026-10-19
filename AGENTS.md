# FINN-flippemaskin

## Les først

Les `START_HER_GITHUB_OG_CODEX_CLOUD.md`, `README.md` og ved behov `docs/SCORING.md`, `docs/DATA_ACCESS.md` og `docs/SCHEMA.md`. Dette er en lokal Python-/Streamlit-pilot, klargjort for videre arbeid i Codex Cloud.

Brukerens gjeldende valg er offentlige FINN-søke- og annonsesider. Dette erstatter den opprinnelige prosjektplanens forbud mot implementering av skraping; se merknaden øverst i planen. Det finnes ingen FINN-tilgangsavtale eller implementert lisensiert API-feed.

## Bevar dette

- Standardvisning og morgenrapport skal bare vise økonomisk overskudd strengt større enn 0 kr, etter kostnader, risikoreserve, tidsverdi og øvrige driftskostnader. Positiv kontantgevinst alene er utilstrekkelig. Null/ukjent/negativt anslag skal ikke varsles som mulighet.
- Eksakt variant, tilstand og minst konfigurert antall uavhengige sammenlignbare referanser kreves. Ikke endre kostnader, rabatt, modellmatch eller minimumskrav for å produsere positive treff.
- Hold demo og ekte data atskilt. Demo og automatiserte tester er syntetiske; ikke presenter disse som faktiske markedsmuligheter. Aktive annonsepriser er ikke bekreftede salgsoppgjør.
- Respekter scraperens pauser og stopp ved tilgangsblokkering. Ingen innlogging, skjulte API-er, proxyrotasjon eller CAPTCHA-omgåelse.
- Ingen automatiske kjøp eller kontakt med selgere. E-post er `DRY_RUN`; ikke aktiver sending uten brukerens instruksjon. Morgenrapporten sender ingen e-post.
- Database, varslingsstatus og utkast under `data/`, miljøfiler og hemmeligheter skal ikke inn i Git. Gamle negative vurderinger skal bevares som historikk lokalt.

## Oppsett og kjøring

Python 3.12 eller nyere. Kjør fra repositoriets rot:

```bash
bash scripts/setup.sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check finnflip app.py scripts tests
```

For forhåndsvisning i skyens tilgjengelige portvisning:

```bash
bash scripts/start_cloud.sh
```

For ekte data når nettverk til FINN er konfigurert:

```bash
.venv/bin/python -m finnflip.cli morning
```

Vent til kommandoen fullføres. Les den nye `data/morning-report.json` bare dersom denne kjøringen lyktes. Rapporter `new_opportunities` med lenke, pris, videresalgsanslag, kontantgevinst, økonomisk overskudd, sikkerhet og kontrollpunkter. Kvitter med `ack-morning` bare når treffene faktisk rapporteres. Ved feil skal gamle rapporter ikke presenteres som nye.

Ingen OpenAI API-nøkkel kreves av programmet. Installer aldri API-avhengigheter eller be om API-nøkkel bare fordi prosjektet brukes i Codex.

## Sky og planlagt drift

ZIP-pakken inneholder ingen installert skyplan, SQLite-database eller overført lokal Codex-automasjon. Hver ny skyoppgave har sitt eget arbeidsområde; den eksisterende oppgaven beholder sin egen tilstand. Ikke anta at `data/` deles mellom nye oppgaver eller følger Git automatisk. Varig lagring, gjentatt kjøring og varslingslevering må konfigureres og verifiseres før daglig drift kan hevdes aktiv. Behold den eksisterende lokale planen til brukeren ber om å bytte eller stoppe den.
