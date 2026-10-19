# Datatilgang – beslutning 19. oktober 2026

**Gjeldende beslutning 19. oktober 2026:** Anders har uttrykkelig bedt om å gå videre med nettskraping når standard-API-et ikke dekker andres Torget-annonser. En avgrenset `PublicFinnAdapter` leser nå offentlige søke- og annonsesider. Den tidligere føringen om bare lokale/syntetiske data er dermed endret av prosjekteieren. Ingen skriftlig FINN-avtale er forelagt prosjektet, og denne brukerbeslutningen er ikke en slik avtale.

**Verifisert:** Første komplette kjøring hentet 29 ekte annonser og 27 prisantydninger fra fire søk, med 33 sideforespørsler og ingen innlesingsfeil. Tid fra start til avslutning var om lag 64 sekunder. Dette måler kjøringen, ikke forsinkelse fra opprinnelig publisering. Alle 29 fikk U i første kjøring fordi eksakt modell/prisgrunnlag ikke var tilstrekkelig. Ingen annonsert pris er presentert som bekreftet oppgjør eller dokumentert lønnsomhet. En forespørsel om særskilt tilgang finnes fortsatt lokalt i [FINN_TILGANGSFORESPORSEL.md](FINN_TILGANGSFORESPORSEL.md).

## Primærkilder kontrollert

Kontrollert 19. oktober 2026:

| Kilde | Dokumentert innhold | Konsekvens |
|---|---|---|
| [FINN brukervilkår, punkt 6](https://www.finn.no/vilkar/brukervilkar-finn) | Automatisert og systematisk kopiering forutsetter skriftlig samtykke. | Vilkårsstatus er fortsatt uavklart; offentlig teknisk tilgjengelighet er ikke et samtykke. |
| [FINN Hjelpesenter: API](https://hjelpesenter.finn.no/hc/no/articles/22629030477202-API) | Standard-API gir tilgang til annonsedata man selv eier, med tilgangsavtale og nøkkel. | En vanlig nøkkel dokumenterer ikke rett til Torget-data fra andre selgere. |
| [FINN: Varslinger på e-post](https://hjelpesenter.finn.no/hc/no/articles/22651852160786-Varslinger-p%C3%A5-e-post) | Lagrede søk gir en daglig oppsummering. | E-post er ingen dokumentert sanntidsfeed, og behandling av innhold må avklares særskilt. |
| [FINN API Developer Resources](https://www.finn.no/api/) | Beskriver forretningsforhold, eierskap til data og aksepterte vilkår som tilgangskrav. | Dokumentasjonen gir ingen generell tilgang til andre brukeres annonser. |
| [Store Hub Connect](https://www.finn.no/bedriftskunde/torget/store-hub-connect) | Publiserer og oppdaterer bedriftens egne produkter fra en feed til FINN. | Dette er ikke en innkommende markedsfeed til analyseverktøyet vårt. |
| [Varslinger i appen](https://hjelpesenter.finn.no/hc/no/articles/22652337506834-Varslinger-i-appen) | Varsler om nye annonser fra lagrede søk. | Kan brukes av Anders i FINN-appen; dokumenterer ikke en maskinell kilde eller en garantert forsinkelse. |

Dette dokumenterer tilgangsrammer. Offentlige annonser er nå lest og teknisk normalisert, men ingen handel, margin eller faktisk etterspørsel er validert.

Den supplerende undersøkelsen fant ingen offentlig dokumentert, åpen feed til andres Torget-annonser. Dette er et undersøkelsesresultat, ikke et bevis på at FINN aldri inngår særavtaler. Om en avgrenset pilot kan godkjennes, og til hvilken pris og forsinkelse, må FINN svare på.

## Datakilder

- `DemoAdapter`: lokale, tydelig syntetiske fakta og `example.invalid`-lenker. Demo og reelle observasjoner holdes atskilt i verdsettelsen og handelsloggen.
- `PublicFinnAdapter`: offentlig HTML fra konfigurerte Torget-søk og annonselenker som faktisk finnes i søkeresultatene. Bruker synlige annonsekort, produktets JSON-LD i selve HTML-en og synlige produktfelt. Ingen skjulte API-er, konto, nettleserprofil eller autentisering brukes.
- `LocalFileAdapter`: lokale JSON/CSV-filer etter en dokumentert avklaring av aktuell bruk. En vanlig boolsk bryter er ikke tilstrekkelig.
- `LicensedFeedAdapter`: deaktivert plassholder med `SourceAdapter`-grensesnitt. Manglende rettighetsgrunnlag og kildekonfigurasjon gir `PermissionError`. Selv med begge angitt stopper adapteren med `NotImplementedError` inntil en konkret avtale er gjennomgått og integrert.

Nettskraperen henter bare offentlige HTTPS-sider på finn.no med søke- eller annonseadresse. Vilkårlige lenker fra lokale importfiler hentes ikke. Offentlig `dealer_segment=1` ble kontrollert ved å velge «Privat» i FINNs synlige søkefilter; `PUBLISHED_DESC` ble kontrollert som «Nyeste først». Ingen selgere kontaktes og ingen handler gjennomføres.

Standardoppsettet bruker fire landsdekkende produktsøk med inntil åtte relevante annonser hver og et målrettet referansesøk på MacBook Air M1/256 med inntil 20. Overlapp dedupliseres. Områdefiltre kan legges inn gjennom offentlige søke-URL-er i `scrape.json`. Betalt plassering og gjenkjente tilbehørstitler hoppes over. Det er minst to sekunder mellom forespørsler og normalt ti minutter mellom kjøringer, med mellomlagring av nylig leste, uendrede detaljer. HTTP 401/403/429, innlogging eller en verifiseringsside stopper kjøringen. Etter blokkering gjøres ingen ny nettverksprøve før minst én time. Det finnes ingen omgåelsesmekanisme.

Bare strukturerte nødvendige produktfakta lagres. Annonsens beskrivelse brukes midlertidig til regeluttrekk, men full tekst, selgerprofil, telefon, bilder og presis adresse lagres ikke av skraperen. Publiseringstid står som ukjent når den ikke finnes; «sist endret» lagres separat. En fjernet annonse er ikke et kjent salg.

## Rettighetsmanifest for lokal import

Opprett et JSON-manifest ved siden av et dokument som beskriver det faktiske grunnlaget. Eksemplet under er en struktur, **ikke en tillatelse**:

```json
{
  "approved_by": "Person som har vurdert grunnlaget",
  "approved_at": "2026-10-19T16:00:00+02:00",
  "basis": "Beskriv konkret opphav, tillatelse, omfang og begrensninger.",
  "purposes": ["analysis", "storage", "drafts"],
  "input_sha256": "SHA256_FOR_DEN_EKSAKTE_DATAFILEN",
  "evidence_file": "grunnlag.txt",
  "evidence_sha256": "SHA256_FOR_GRUNNLAGSDOKUMENTET"
}
```

Hashene må være 64 små heksadesimale tegn. Finn dem lokalt med `shasum -a 256 data.json grunnlag.txt`. Evidensfilen tolkes relativt til manifestet og må finnes. Manifest, filhash og importtid lagres i importloggen. Endret datafil krever et nytt manifest som gjelder den filen. Programmet verifiserer samsvar og at feltene finnes; eieren må selv vurdere om tillatelsen faktisk er dekkende. Det valideres ikke at et egenprodusert manifest er et ekte samtykke fra FINN.

Ikke kopier store annonsemengder manuelt for å omgå vilkårene. Ikke legg selgeridentitet eller kontaktinformasjon i fritekst. Importer bare nødvendige produktfakta innenfor avklart bruk. Ekstern varsling må også være omfattet av datagrunnlaget før SMTP brukes.

## Før en godkjent feed kan utvikles

Dokumenter rettighetshaver og avtale, annonser som omfattes, analyse, lagring, oppbevaring, sletting, varsling, tredjepartskrav, oppdateringsfrekvens, responstid, pris og sikker nøkkelhåndtering. Deretter implementeres en egen adapter og kontrakttester mot avtalt skjema. En kildebryter alene aktiverer aldri FINN-tilgang.
