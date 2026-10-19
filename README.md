# FINN-flippemaskin

Lokal MVP for å teste om brukte varer kan videreselges med overskudd etter kostnader, risiko og tidsbruk. Python, SQLite, Pydantic og Streamlit. Ingen AI-nøkkel eller betalt tjeneste kreves.

**Status:** Innhenting fra offentlige FINN-søke- og annonsesider er implementert. Ekte annonser holdes atskilt fra syntetisk demo. Faktisk e-postlevering og lønnsomhet er ikke verifisert. Ingen selgere kontaktes.

Anders har bedt om å gå videre med nettskraping når standard-API-et ikke dekker behovet. Dette erstatter den tidligere prosjektføringen mot skraping. Det foreligger fortsatt ingen FINN-tilgangsavtale. Se [datatilgang og kildevalg](docs/DATA_ACCESS.md).

## Start

Kjør fra prosjektmappen (Python 3.12 eller nyere):

```bash
bash scripts/setup.sh
.venv/bin/python -m streamlit run app.py
```

Åpne http://127.0.0.1:8501. På denne Mac-en kan du også dobbeltklikke **Start flippemaskin.command** etter oppsett. Stopp med Ctrl+C i terminalen. Serveren bindes bare til din maskin.

Trykk **Hent fra FINN nå** for ekte annonser. Fire produktsøk henter inntil åtte annonser hver, og et målrettet MacBook Air M1/256-søk henter inntil 20 for å bygge sammenlignbart prisgrunnlag. Overlapp dedupliseres. Alle søk bruker nyeste først og private selgere. Startsøket er landsdekkende; legg inn FINN-søke-URL-er med ønskede områdefiltre i `scrape.json`. Et søk kan ha sin egen `limit` (maks 20). Konfigurert Oslo-radius i økonomidelen beregner ikke geografisk avstand automatisk. Manglende variant, tilstand eller prisgrunnlag gir fortsatt U.

Innhenting fra terminal:

```bash
.venv/bin/python -m finnflip.cli scrape
# Valgfri løpende innhenting hvert tiende minutt mens terminalen kjører:
.venv/bin/python -m finnflip.cli scrape --watch
```

Standard er to sekunder mellom sideforespørsler, minst ti minutter mellom kjøringer og to timers gjenbruk av uendrede detaljsider. Prisendringer i søket utløser ny detaljlesing. Nyeste sortering, private-filter og HTML-format ble kontrollert mot offentlige sider 19. oktober 2026. Ingen innlogging, skjulte API-er, proxyrotasjon eller CAPTCHA-omgåelse brukes. HTTP 401/403/429 eller verifiseringsside stopper innhentingen, med minst én times pause etter blokkering.

Dette er periodisk innhenting, ikke en garantert sanntidsfeed. Visningen viser siste innhenting og sist sett. Ukjent publiseringstid erstattes ikke med søkets relative klokkeslett eller «sist endret». `--watch` installerer ingen bakgrunnstjeneste; stopp med Ctrl+C og oppdater appen for nye resultater.

## Positive treff og morgenkjøring

Oversikten viser som standard **bare økonomisk overskudd større enn 0 kr**, etter direkte kostnader, risikoreserve, tidsverdi og øvrige driftskostnader. Null, underskudd og ukjent anslag skjules. Tidligere kjøpte, avviste eller avsluttede kandidater skjules også. Avkryssingen «Kun positive økonomiske anslag» kan slås av for å undersøke hele grunnlaget; historikken bevares.

Morgenjobben kjører i denne Codex-chatten **hver dag kl. 08:00 Europe/Oslo**. Den bruker:

```bash
.venv/bin/python -m finnflip.cli morning
```

Kommandoen henter dagens søk, vurderer på nytt og skriver `data/morning-report.json`. Bare ekte, aktive FINN-annonser sett i siste kjøring, med nylig kontrollert detaljside, uten lesefeil og med positivt økonomisk anslag kan komme med. Klasse A/B er ikke et tilleggskrav: en C/D-kandidat med positivt anslag kan fortsatt ha viktige kontrollpunkter.

Chatten varsler om nye positive treff, med pris, videresalgsanslag, kontantgevinst, økonomisk overskudd, annonse og kontrollpunkter. Vanlige kjøringer uten nye treff gir ingen melding. Samme fysiske vare varsles igjen bare når en lavere pris forbedrer økonomisk anslag med minst 250 kr siden forrige varsel. `data/morning-notifications.json` husker rapporterte treff; `ack-morning` brukes av chatten når den rapporterer mulighetene. Å generere en rapport alene kvitterer ingenting. Ingen selgere kontaktes eller e-post sendes av morgenjobben.

Maskinen må være på, ha nett og ha Codex-appen kjørende for lokal planlagt kjøring, jf. [OpenAI Docs om planlagte oppgaver](https://learn.chatgpt.com/docs/automations?surface=app). Jobben kan administreres fra planlagte oppgaver i appen. Streamlit trenger ikke kjøre under innhentingen; last inn siden på nytt for å se oppdaterte resultater.

Oppsettet bruker eksisterende Python 3.12+ eller Codex sin medfølgende Python dersom den finnes. Systemets gamle Python 3.9 støttes ikke. `requirements.lock.txt` låser det testede miljøet; `pyproject.toml` dokumenterer kompatible hovedversjoner. Python 3.12 er valgt fordi den låste NumPy-versjonen krever dette.

## Dette virker

- JSON/CSV-import med validering og dokumentert rettighetsgrunnlag for egne data; eksplisitt demokilde.
- Offentlig FINN-HTML via `PublicFinnAdapter`, filtrerte søk, produktfakta, prisantydninger, kildehistorikk og ny innhenting fra app/CLI.
- Åtte eksakte MacBook Air-/Garmin-grupper, 56 uavhengige syntetiske referanser og elleve kandidater.
- Prisgrunnlag per variant, tilstand og kildetype; ferskhet, duplikater og historisk tilgjengelig informasjon kontrolleres.
- Konservativt prisanslag, kostnader, tidsverdi, risikoreserve, maksimal kjøpspris, stresscenario og forklarbar score.
- Første konkrete live-vurderinger: [åtte MacBook-annonser med beregnet kontantgevinst og økonomisk overskudd](docs/LIVE_ASSESSMENTS.md). Alle åtte har negativt anslag med daværende priser og pilotparametere; dette er ikke dokumentasjon på realiserte handler.
- Oversikt med filtre, kontrollpunkter, referanser, historikk og nedlastbar vurdering med fullstendig konfigurasjon.
- Lokale tekst-/HTML-utkast; eget A-varsel og B-samlerapport, deduplisering og pause ved endringer.
- Tilbakemeldinger, handelslogg, faktiske oppgjør og separat usolgt lager. CSV sammenligner motoren med faste modellgrenser.

Demoen demonstrerer en attraktiv A-kandidat, en billig vare som gir underskudd etter kostnader, uavklart RAM/variant, for få referanser, uavklart aktiveringslås, delbetaling og pakkepris. Demonstrerte oppgjør er fortsatt oppdiktede.

## Kommandoer

```bash
# Import, vurdering og utkast i ett steg; kan gjentas uten nye duplikater.
.venv/bin/python -m finnflip.cli demo
.venv/bin/python -m finnflip.cli list

# Endre config.json og beregn på nytt uten å endre kode.
.venv/bin/python -m finnflip.cli assess
.venv/bin/python -m finnflip.cli drafts

# Registrer oppdiktede utfall for å prøve handelsloggen.
.venv/bin/python -m finnflip.cli feedback fixtures/feedback.json
.venv/bin/python -m finnflip.cli trade fixtures/trade-sold.json
.venv/bin/python -m finnflip.cli trade fixtures/trade-inventory.json
.venv/bin/python -m finnflip.cli report

# Tester og statisk kontroll.
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check finnflip app.py scripts tests
```

Data lagres i `data/finnflip.sqlite`, utkast i `data/drafts/` og rapport i `data/comparison.csv`. Databasen opprettes automatisk. Den opprinnelige prosjektplanen er bevart. Ingen personnavn, telefon eller hjemmeadresser er del av skjemaet. Dokumentasjonsfelt kan likevel inneholde personopplysninger hvis de legges inn manuelt: hold dem til nødvendige produktfakta og kildebevis.

Alle CLI-kommandoer kan bruke en separat database og konfigurasjon:

```bash
.venv/bin/python -m finnflip.cli --db data/experiment.sqlite --config docs/config.example.json demo
```

Streamlit bruker prosjektets `config.json` og `data/finnflip.sqlite`. Endre terskler, timeverdi, radius eller kapitalramme der, og trykk «Beregn på nytt». `capital_limit: null` betyr at Anders ennå ikke har fastsatt en ramme. Angitt kapitalramme gjelder objektets kjøpspris + direkte kostnader i denne MVP-en; vurder også samlet lager før nye kjøp.

## Egne data

Les [datatilgang](docs/DATA_ACCESS.md) og [dataskjema](docs/SCHEMA.md) først. FINN-adapteren leser bare annonselenker funnet i konfigurerte offentlige FINN-søk. Vilkårlige lenker fra CSV/JSON åpnes ikke automatisk. Reelle og syntetiske referanser blandes ikke.

```bash
.venv/bin/python -m finnflip.cli import references /absolutt/sti/references.json --rights-file /absolutt/sti/references.rights.json
.venv/bin/python -m finnflip.cli import candidates /absolutt/sti/candidates.csv --rights-file /absolutt/sti/candidates.rights.json
.venv/bin/python -m finnflip.cli assess
.venv/bin/python -m finnflip.cli drafts
```

Rettighetsmanifestet må dokumentere hvem som avklarte bruken, når, grunnlaget og tillatte formål, og knyttes med SHA-256 til både den eksakte datafilen og et lokalt bevisdokument. Dette er en sporbar kontroll, ikke en automatisk juridisk godkjenning. Ingen forhåndsutfylt rettighet for FINN-data følger med.

Historisk vurdering bruker bare data som faktisk var importert og kjent på tidspunktet:

```bash
.venv/bin/python -m finnflip.cli assess --at 2026-10-19T16:00:00+02:00
```

Dette lager en ny vurderingskjøring med valgt konfigurasjon; tidligere vurderinger bevares i databasen. Oversikten viser siste kjøring. Kjør `assess` uten `--at` for å gå tilbake til nåtid. Gamle demoreferanser blir etter hvert for gamle med vilje; endring av ferskhetskravet er et eksplisitt eksperiment, ikke oppdaterte markedsdata.

## Videre validering og aktive varsler

1. Følg opp datatilgang med FINN ved videre drift. Avtalte API-feeds er fortsatt ikke implementert; `LicensedFeedAdapter` er en separat plassholder. Nettskraperen er ikke bevis på at FINN har godkjent bruken.
2. Samle reelle sammenlignbare referanser og kontroller eksakte varianter. Kalibrer antatt salgsrabatt, score, kostnader og terskler. Frys en konfigurasjon før en fremoverskuende pilot.
3. Avklar kapitalramme, samlet lager, praktisk kontroll og relevant skatte-/MVA-behandling før handel. Beregninger er før inntektsskatt; MVA er uavklart.
4. Prøv e-postutkastene før SMTP aktiveres. Se [arkitektur og drift](docs/ARCHITECTURE.md) for eksplisitt SMTP-oppsett og feilhåndtering. Demo sendes aldri gjennom SMTP.

Løsningen er beregnet på én eier lokalt, med morgenkjøring planlagt i Codex. Verifisert avkastning og målt presisjon krever faktiske etiketter og gjennomførte handler.

Se også [score og økonomi](docs/SCORING.md), [dataskjema](docs/SCHEMA.md), [datatilgang](docs/DATA_ACCESS.md) og [valideringsrapport](docs/VALIDATION.md).
