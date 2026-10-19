# Arkitektur og drift

## Lokal flyt

```text
SourceAdapter → Pydantic → SQLite-observasjoner med revisjoner
             → eksakt produktmatch → relevante referanser
             → verdsettelse → økonomi → score og kontrollpunkter
             → lagret vurderingssnapshot → Streamlit / CLI
             → outbox → lokale tekst-/HTML-utkast
             → manuell oppfølging → handelslogg → sammenlignings-CSV
```

`models.py` definerer inn- og utdata. `sources.py` leser lokale filer og dokumenterer kilden. `scraper.py` implementerer `PublicFinnAdapter`, en requests-/BeautifulSoup-klient for offentlige FINN-sider. Den bruker synlige kort og produktets JSON-LD i levert HTML; ingen separate skjulte dataendepunkter kalles. `engine.py` er deterministisk og gjør ingen I/O. `storage.py` eier SQLite-skjema og transaksjoner. `service.py` koordinerer flyten, `notifications.py` eier utkast/SMTP, og `cli.py` og `app.py` er brukergrensesnitt.

SQLite har WAL, fremmednøkler og 15 sekunders låseventing. Import validerer hele filen før én transaksjon lagrer radene. Stabil nøkkel er kilde+annonse-ID. Identisk gjenimport lager ikke ny revisjon. Prisendring og retur til en tidligere pris bevares som nye revisjoner.

Referanser har både observert og kjent tidspunkt. Databasens faktiske importtid er en ytterligere grense: en nylig importert, tilbakedatert referanse kan aldri dukke opp i en tidligere vurdering. Tidligere referanserevisjoner bevares. Vurderingen lagrer alle referansesnapshots, kandidat, konfigurasjonsinnhold, SHA-256 av konfigurasjonen, beregningsversjon og tidspunkt. Referanser og filtre kan dermed rekonstrueres. Siste kjøring vises; tidligere vurderinger ligger i databasen.

## Utviklingsvalg

- Python 3.12+; lokalt verifisert med medfølgende Python 3.12.14. Den låste NumPy-versjonen krever minst Python 3.12.
- Pydantic 2, Streamlit 1 og pytest. Låste testversjoner ligger i `requirements.lock.txt`.
- JSON-konfigurasjon fremfor databaseadministrasjon eller skytjeneste. Åtte eksplisitte produktgrupper fremfor tekstanalyse med AI.
- Eksakt tilstand kreves; ingen skjult kvalitetsjustering. Kildetyper verdsettes hver for seg.
- Demo er statiske observasjoner fra oktober 2026. De eldes og blir bevisst ugyldige etter ferskhetsgrensen. `scripts/generate_demo.py` regenererer samme syntetiske fixtures og standardkonfigurasjon; scriptet **overskriver config.json**, så bruk det bare ved bevisst tilbakestilling av demoressursene.
- Ingen autentisering, offentlig server, installert scheduler eller kontooppkobling er nødvendig. Offentlige FINN-sider kan leses på forespørsel; CLI `scrape --watch` gjentar ved konfigurert intervall mens prosessen kjører.

Primærdokumentasjon kontrollert 19. oktober 2026: [Pydantic](https://docs.pydantic.dev/latest/), [Streamlit installasjon](https://docs.streamlit.io/get-started/installation), [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) og [pytest](https://docs.pytest.org/en/stable/getting-started.html). Installerte versjoner ble kontrollert mot offisiell pakkeindeks. Ingen FINN-API eller AI-API brukes.

Nettskraperen bygger på [Requests](https://requests.readthedocs.io/en/latest/user/quickstart/) og [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/). FINNs annonsesider bruker også deklarativ Shadow DOM. Parseren inkluderer derfor relevante `TemplateString`-tekster i avgrensede produktfelt; standard `get_text()` alene kan gi tomme verdier. MacBook Air M1 kobles til 13-tommersfamilien fra 2020 med kilde i [Apples spesifikasjon](https://support.apple.com/en-us/111883); RAM/SSD krever fremdeles eksplisitte annonsefakta.

`scrape_runs` reserverer en kjøring i en SQLite-transaksjon og lagrer status/antall/feil. `live_items` lagrer sist sett, sist detaljkontrollert og parser-versjon, slik at en ny parser ikke blindt bruker gammel normalisering. Uendret pris bruker mellomlagrede detaljer i to timer; endret kortpris eller parser-versjon leser detaljene på nytt. Skraperen lagrer ikke rå HTML eller hele beskrivelsen. Gamle vurderinger og prisrevisjoner bevares. Referanser som konstateres fjernet, trekkes ut av aktivt annonseprisgrunnlag ved ny revisjon.

## Outbox og e-post

`DRY_RUN` er standard. Utkast lagres først i SQLite, så i `data/drafts/`. A oppretter et eget utkast, B én samlerapport per demo-/reell kategori. U, C og D varsles ikke. HTML bygges med escaping av hele det ubetrodde tekstinnholdet. Emner får fjernet linjeskift. Kandidatlenker blir aldri hentet automatisk.

Hver fysisk vare har en varslingshistorikk basert på `entity_id`. Uendret pris og score gir ikke nye utkast. Prisendring, overgang til A eller minst konfigurert scoreforbedring kan gi nytt utkast etter `cooldown_hours`. Reservasjon av utkast og varslingshendelser gjøres i en SQLite-transaksjon med skrivelås. Pending utkast oppdateres med gjeldende vurderingsdetaljer; utdaterte priser eller bortfalte klasser blir `superseded`. Tilbakemelding som uinteressant, feil modell, borte, kjøpt, solgt, returnert eller tap stopper videre varsling for registrert kandidat. En registrert handel stopper også varsling.

Tilstander:

| Tilstand | Betydning | Automatisk nytt sendeforsøk |
|---|---|---|
| `draft` | Klart lokalt utkast | Ja, bare ved eksplisitt `send` og aktiv SMTP |
| `sending` | En prosess har reservert sendingen | Nei |
| `sent` | SMTP-kallet returnerte uten feil | Nei |
| `failed` | Feil før levering ble forsøkt | Ja, ved neste eksplisitte `send` |
| `uncertain` | Feil mens levering kan ha skjedd | Nei; undersøk transporten manuelt |
| `superseded` | Ikke lenger relevant etter ny vurdering/oppfølging | Nei |

Ved krasj kan en rad bli stående i `sending`. Ikke nullstill automatisk: undersøk om meldingen nådde frem. SMTP gir ingen absolutt garanti mot duplikater eller for faktisk mottak, selv med en stabil Message-ID. En tvetydig levering skal ikke blindt gjentas. Filutkast er arkiv; sjekk gjeldende status i oversikten før bruk av tidligere eksporterte filer.

### Eksplisitt aktivering

Før aktivering må reelle data og varslingsrettigheter være avklart, og et konkret utkast gjennomgått. Konfigurer `mail` i config.json:

```json
{
  "mode": "SMTP",
  "owner_address": "anders@eget-domene.no",
  "from_address": "flippemaskin@eget-domene.no",
  "smtp_host": "din-smtp-vert",
  "smtp_port": 587,
  "cooldown_hours": 24,
  "score_improvement": 10
}
```

Dette er felt-eksempler; ingen konto er satt opp. Legg eventuell brukernavn/passord i miljøvariablene `FINNFLIP_SMTP_USER` og `FINNFLIP_SMTP_PASSWORD`, aldri i repo eller kommandoer som legges i historikk. STARTTLS med sertifikatkontroll kreves. Send bare til den angitte eieradressen:

```bash
.venv/bin/python -m finnflip.cli drafts
.venv/bin/python -m finnflip.cli send
```

Sending beregner kandidatene på nytt før den kontrollerer pending utkast. Hver rad får eget resultat ved delvis feil. Feiltypen lagres; serverens rå svar og credentials logges ikke. Demo sendes aldri. SMTP-adapteren er testet mot en lokal stub; ekte transport og mottak er ikke verifisert.

## Lokale data og sikkerhet

Filer begrenses til 5 MiB og 10 000 rader; skjemaet avviser ukjente felt, negative priser, ugyldige desimaler, ikke-endelige tall og tidsstempler uten tidssone. Kun HTTP(S)-URL-er uten innebygde credentials godtas. Fritekst tolkes ikke som instruksjoner. HTML-escaping brukes i mail; Streamlit bruker ikke `unsafe_allow_html`. Eksporterte tekstfelt beskyttes mot vanlige regnearkformler.

Ingen selgernavn, telefon eller hjemmeadresse er del av skjemaet. Kildebevis og dokumentasjon skal bare inneholde nødvendige fakta. Lokal SQLite og utkast er ikke kryptert av applikasjonen; de ligger i brukerens lokale prosjektmappe. Bruk ikke denne enkeltbrukerappen som en offentlig tjeneste. Sikkerhetskopier databasen før faktiske handler; SQLite backup-API kan brukes ved kjørende prosess.
