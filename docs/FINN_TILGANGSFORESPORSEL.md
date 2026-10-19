# Ferske FINN-data – konkret neste steg

Dato: 19. oktober 2026. Status: lokalt utkast, ikke sendt. Anders har bekreftet at ingen tilgangsavtale finnes ennå.

## Hva vi trenger avklart

Vi trenger en avtalt innkommende datakilde for **andre selgeres** annonser i to avgrensede produktfamilier, ikke publisering av egne annonser. Det er ukjent om FINN tilbyr dette bruksområdet. Vi skal få et konkret svar før vi legger mer arbeid i funksjoner som forutsetter live-data.

FINNs [API-hjelp](https://hjelpesenter.finn.no/hc/no/articles/22629030477202-API) oppgir en API-kontakt. [Utviklerportalen](https://www.finn.no/api/) viser også til kundeservice. Be om at forespørselen sendes til riktig ansvarlig for Torget/datapartnerskap. [Store Hub Connect](https://www.finn.no/bedriftskunde/torget/store-hub-connect) gjelder publisering og er ikke den datatjenesten vi trenger.

## Henvendelse klar til bruk

**Emne:** Forespørsel om avgrenset datatilgang til Torget for lokal analysepilot

Hei,

Jeg undersøker muligheten for en skriftlig avtale om tilgang til et avgrenset utvalg Torget-annonser til et lokalt analyseverktøy jeg utvikler for egen bruk.

Verktøyet skal vurdere mulige kjøp av brukte varer for videresalg, med beregning av kostnader, risiko og tidsbruk. Første pilot gjelder utvalgte MacBook Air-modeller med Apple-chip og Garmin-klokker i Oslo-området. Området og modellutvalget kan tilpasses en eventuell avtale.

Jeg er kjent med at det ordinære API-et beskrives som tilgang til egne annonsedata. Forespørselen gjelder derfor uttrykkelig annonser fra andre selgere og tillatelse til den beskrevne analysen.

Tilbyr dere en avtale eller godkjent partnerløsning for et slikt avgrenset bruksområde?

For en mulig pilot ønsker jeg å avklare:

1. Om tilgang kan gis til nye annonser, prisendringer og informasjon om at en annonse ikke lenger er tilgjengelig. Forsvinning vil ikke behandles som bekreftet salg eller kjent oppgjørspris.
2. Hvilke produktfelt som kan gjøres tilgjengelige: stabil annonse-ID, URL, pris, publisert-/endringstid, omtrentlig sted og nødvendige modell-/konfigurasjonsfakta. Tittel eller begrenset beskrivelsestekst er aktuelt bare dersom det omfattes av avtalen og trengs for modellidentifikasjon.
3. Faktisk forsinkelse fra publisering/endring til data kan mottas. For å teste raske kjøpsmuligheter er ønsket vårt helst under fem minutter; dette er et pilotønske, ikke en forventning om at dere tilbyr en slik tjeneste.
4. Tillatelse til lokal lagring, sammenligning av prisobservasjoner, beregnede vurderinger og varsling til meg selv, samt eventuelle vilkår for oppbevaring og sletting.
5. API/feed-format, begrensninger på volum og frekvens, tilgangskrav, priser og mulighet for en begrenset prøveperiode. Det ønskes ikke noe abonnement eller kjøp på bakgrunn av denne forespørselen.

Pilotens formål er å finne ut om verktøyet tilfører praktisk verdi. Jeg planlegger ikke automatisk kjøp, automatiske meldinger til selgere, offentlig republisering av annonser eller lagring av selgernavn, telefon eller hjemmeadresse.

Hvis dere ikke tilbyr dette, er det også nyttig å få bekreftet det og eventuelt få henvisning til en godkjent dataleverandør for akkurat denne bruken.

Vennlig hilsen
Anders

## Hva som skjer etter et svar

| Svar | Videre arbeid |
|---|---|
| Avtalt feed/API med relevant dekning | Gå gjennom avtale og skjema; implementer konkret adapter, kontinuerlig innlesing, kildehelse og måling av forsinkelse. |
| FINN foreslår en partner | Verifiser partnerens tillatelse, omfang, leveringsforsinkelse og pris før integrasjon. |
| Tilgang bare til egne annonser | Oppfyller ikke behovet for å oppdage andres nye annonser. |
| Ingen egnet tilgang | Revurder prosjektet. FINNs egne appvarsler kan brukes manuelt, men utgjør ikke automatisk dataintegrasjon med denne appen. |

Ingen ekstern henvendelse, abonnement eller bestilling er utført. En eventuell skriftlig avtale er ikke i seg selv en ferdig teknisk integrasjon: dagens `LicensedFeedAdapter` er fortsatt en plassholder.

## Før live-funksjonen regnes som levert

- Avtalt kilde dekker annonser fra andre selgere og den faktiske analysen, lagringen og varslingen.
- Ekte nye annonser og prisendringer kommer inn automatisk med stabile identiteter og relevante produktfelt.
- Publisert-, mottatt- og vurdert-tid måles separat; manglende publiseringstid vises som ukjent.
- Ende-til-ende-forsinkelse rapporteres med faktisk målt fordeling, ikke med pollingintervallet som løfte om hastighet.
- Feil, rate limits og avbrudd er synlige. Duplikater og gammel kildeinformasjon gir ikke falske nye muligheter.
- Referansegrunnlaget er avklart og dokumentert; manglende RAM/SSD, variant eller nok relevante referanser gir fortsatt U.
- Utkast kontrolleres på ekte inndata før aktiv e-post prøves separat.

Fem minutters forsinkelse er et foreløpig ønske som kan endres når vi kjenner tilbudet og hvilke muligheter som faktisk er tilgjengelige. Det er verken en garanti eller en akseptert økonomisk ramme.
