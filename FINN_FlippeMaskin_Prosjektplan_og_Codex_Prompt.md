# FINN-flippemaskin – prosjektplan og Codex-prompt

Dato: 17. oktober 2026. Eier: Anders.

> **Oppdatert gjennomføringsvalg 19. oktober 2026:** Anders har etter gjennomgang uttrykkelig bedt om nettskraping dersom API-et ikke dekker behovet. Dette overstyrer den opprinnelige føringen under om ikke å implementere FINN-skraping. Offentlige søke-/annonsesider er nå valgt som teknisk datavei; det er ikke dokumentasjon på en avtale med FINN. Øvrige krav til beregninger, datakvalitet og ingen automatiske kjøp eller selgerkontakt gjelder fortsatt. Gjeldende implementasjon er beskrevet i README og docs/DATA_ACCESS.md. Resten av dette dokumentet er opprinnelig prosjektplan.

## 1. Vurdering: et godt prosjekt?

**Ja, som et avgrenset eksperiment med en tydelig lønnsomhetstest.** Jeg ville ikke startet med å bygge en skanner for hele FINN. Først må vi vise at vi kan identifisere varer som faktisk kan kjøpes og selges med tilfredsstillende fortjeneste etter kostnader, risiko og tidsbruk.

Fordelen kan komme fra bedre produktforståelse, raskere vurdering og billigere gjennomføring. Selve AI-en er ingen dokumentasjon på at vi har en fordel. Et godt kjøp må også være tilgjengelig, mulig å kontrollere og lett nok å selge videre.

Min vurdering er at dette passer godt som et personlig analyseverktøy og en praktisk test av en liten handelsvirksomhet. Et skalerbart produkt for mange brukere er en senere hypotese: datalisens, konkurranse mellom brukere om de samme varene og kundenes faktiske betalingsvilje er uavklart.

Tre forhold avgjør om prosjektet er verdt å fortsette:

1. Vi får en egnet, tillatt og tilstrekkelig rask datakilde.
2. Prisestimatene holder når varer faktisk skal selges.
3. Fortjenesten er attraktiv sammenlignet med kapitalbinding og Anders' tidsbruk.

Det er ikke undersøkt konkrete annonser eller dokumentert lønnsomme nisjer i denne leveransen. Nisjevalgene og tersklene under er forslag som skal testes.

## 2. Første avklaring: data og hastighet

FINNs publiserte brukervilkår sier at automatisert og systematisk innhenting krever eksplisitt skriftlig samtykke. Hjelpesenteret beskriver standard-API-et som tilgang til annonsedata man selv eier. En ordinær API-nøkkel løser derfor ikke behovet for å lese hele Torget. [1][2]

FINN beskriver e-postvarsler fra lagrede søk som en oppsummering én gang per døgn. Appen har varsler om nye annonser, men dette er ikke dokumentasjon på en tilgjengelig maskinell sanntidsstrøm. [3][4]

**Konsekvens:** En e-postbasert prototype kan teste sortering og verdsettelse. Den kan ikke dokumentere at vi vil vinne konkurransen om de aller raskeste kuppene. En rask e-post fra vår motor hjelper lite hvis annonsen allerede er mange timer gammel.

| Datavei | Bruk i prosjektet | Avklaring |
|---|---|---|
| Avtalt FINN-tilgang / lisensiert leverandør | Ønsket vei til automatisk skanning | Tilgang til andres annonser, rett til analyse/lagring/varsling, dekning, forsinkelse og pris må dokumenteres |
| Brukerens mottatte FINN-varsler | Mulig begrenset pilot | Avklar at planlagt behandling er tillatt; bare tilgjengelige felt, ingen automatisk henting av lenkede annonser |
| Manuelt registrerte observasjoner | Test av verdsettelse og arbeidsflyt | Avgrenset og tillatt registrering av nødvendige produktfakta; ikke bruk dette som et opplegg for systematisk kopiering |
| Syntetiske testdata | Umiddelbar lokal utvikling | Bevis på at programmet fungerer, ingen dokumentasjon på markedsmuligheten |

Fase 0 skal ende med en beslutning om datavei. Manglende tillatt tilgang skal ikke omgås med skjulte endepunkter, proxyer eller en tredjepart som bare videreselger uavklart skraping. Et teknisk tilgjengelig endepunkt eller robots.txt er ikke i seg selv en tilgangsavtale.

## 3. Nisjer eller hele markedet?

**Anbefaling: to produktfamilier, totalt omtrent 5–10 eksakte modell-/konfigurasjonsgrupper.** Oslo med lokal kontroll ved kjøp er et foreløpig geografisk utgangspunkt. Sted, radius og fraktmulighet skal kunne endres i konfigurasjonen.

| Nisje | Hvorfor den er aktuell | Hva som kan spise opp gevinsten | Prioritet |
|---|---|---|---|
| Utvalgte MacBook Air-modeller med Apple-chip | Modell og konfigurasjon kan beskrives presist; du kjenner produktområdet | RAM/SSD, batteri, skader, aktiveringslås, organisasjonsadministrering og hard konkurranse | Pilot 1 |
| Utvalgte Garmin-klokker | Du kjenner treningsprodukter; små varer er praktiske å håndtere | Modellvarianter, batteri, funksjonsfeil, slitasje og priskutt på nye modeller | Pilot 2 |
| Kontorstoler fra kjente produsenter | Interessant mulig lokal prisforskjell | Transport, lagring, variant og tilstand | Reserve dersom logistikk er enkel |
| Kameraobjektiver / profesjonelt verktøy | Mulige tydelige modellgrupper | Krever egen fagkunnskap og funksjonskontroll | Senere ved dokumentert kompetanse |
| Møbler generelt, klær, samlerobjekter og «alt» | Stor bredde | Vanskelig sammenligning, autentisering, plass og mye støy | Ikke første versjon |

Dette er en vurdering av egnethet for testing, ikke en rangering av observerte marginer eller salgshastighet. MacBook-risikoen er reell: Apple beskriver at aktiveringslås kan hindre reaktivering og bruk uten nødvendig autentisering. [5]

Velg eksakte varianter etter en kort kartlegging av referansegrunnlaget. Ikke slå sammen ulike RAM-/SSD-konfigurasjoner, klokkestørrelser eller modellgenerasjoner for å få flere observasjoner. Hvis én nisje mangler sammenlignbare objekter, bytt nisje fremfor å senke kvalitetskravet.

Utvid først når én nisje har vist gode resultater. En senere bred søkefunksjon kan foreslå nye nisjer, men hver nisje trenger egne prisregler, kostnader og kontrollpunkter.

## 4. Hvordan underprising skal beregnes

En lav pris sammenlignet med gjennomsnittet av aktive annonser er bare et første signal. Aktive annonser kan være overpriset. En fjernet eller «solgt»-merket annonse dokumenterer heller ikke hvilken pris handelen ble gjennomført til.

Skill mellom:

- **Annonsert pris:** det selger ber om.
- **Anslått videresalgspris:** modellens estimat med dokumenterte forutsetninger.
- **Bekreftet transaksjonspris:** faktisk kjent oppgjør, med kilde og dato.

Prisgrunnlaget må ha kildetype, tidspunkt, nøyaktig produktvariant, tilstand og sikkerhetsnivå. Referanser fra forhandlere med garanti skal ikke ukritisk sammenlignes med privat videresalg.

Første prisregel: bruk et robust lavt prisnivå blant relevante referanser, eksempelvis nedre kvartil av nylige, sammenlignbare annonsepriser. Dette er et startanslag for annonserte priser, ikke en validert salgspris eller en statistisk nedre sikkerhetsgrense. Juster for tilstand og manglende tilbehør bare med eksplisitte regler. Eventuell rabatt fra annonsepris til salgspris må stå som en antakelse til den kan kalibreres mot gjennomførte handler.

Start med et krav om minst fem uavhengige, relevante referanser før motoren gir en ordinær prisbasert rangering. Fem er en foreløpig minimumsterskel, ikke et kvalitetsbevis. Vis antall, alder og prisspredning. Duplikater, samme vare som republiseres og selve kandidatannonsen skal ikke blåse opp referansegrunnlaget.

Ved manglende eksakt modell, tvilsom prisbetydning eller for svakt prisgrunnlag: **«Kan ikke vurderes» eller «Må avklares».** Motoren skal kunne avstå.

### Økonomi per objekt

Alle beløp under gjelder før inntektsskatt. Hvis MVA-behandling er relevant, må beregningen tilpasses en avklart behandling; ikke anta at alle differanser er disponibel fortjeneste. Systematisk aktivitet med videresalg må vurderes etter kriteriene for næringsvirksomhet. [6]

```text
Kontantgevinst = konservativt anslått videresalgspris
                − innkjøpspris
                − direkte kostnader til kjøp og salg
                − risikoreserve

Økonomisk overskudd = kontantgevinst
                     − timer × valgt timeverdi
                     − fordelt driftskostnad
                     − kostnad ved kapitalbinding

Avkastning på innsats = kontantgevinst / (innkjøpspris + direkte kostnader)
```

Direkte kostnader omfatter blant annet relevant frakt, transport, emballasje, gebyrer, nødvendig tilbehør og kjent reparasjon. Risikoreserve dekker andre usikre tap og må ikke telle samme kjente reparasjon to ganger. Ukjent alvorlig feil skal utløse kontroll, ikke skjules i en liten standardreserve.

Rapporter også maksimal kjøpspris gitt krav til kontantgevinst og avkastning. En handel som bare fungerer hvis selger godtar pruting, merkes **«Forhandlingsmulighet»**, og teller ikke som et kupp til annonsert pris.

**Regneeksempel – oppdiktede beløp, ingen faktisk annonse:**

| Post | Beløp |
|---|---:|
| Anslått videresalg | 6 000 kr |
| Innkjøp | −4 000 kr |
| Direkte kostnader | −400 kr |
| Risikoreserve | −300 kr |
| Kontantgevinst | **1 300 kr** |
| To timer à 300 kr | −600 kr |
| Fordelt drift | −100 kr |
| Økonomisk overskudd, før eventuell kapitalkostnad | **600 kr** |

Med 10 % lavere videresalgspris blir økonomisk overskudd i eksemplet null, før eventuell kapitalkostnad. En tilsynelatende prisforskjell på 2 000 kroner er derfor ikke det samme som en attraktiv handel.

## 5. Verdipotensialscore og klasser

Bruk en forklarbar score fra 0 til 100. Hold datakvalitet synlig ved siden av scoren. Scoren er et prioriteringsverktøy, ikke en sannsynlighet for gevinst.

| Del | Vekt | Hva som vurderes |
|---|---:|---|
| Kontantgevinst i kroner | 35 % | Etter kostnader og risikoreserve |
| Avkastning på innsats | 20 % | Gevinst relativt til kapitalbehov |
| Styrke i verdsettelsesgrunnlaget | 20 % | Eksakt variant, referansekvalitet og bekreftede transaksjoner |
| Omsettelighet | 15 % | Dokumentert salgstid/etterspørsel; ellers tydelig merket antakelse |
| Gjennomførbarhet | 10 % | Transport, kontroll, tidsbruk og lagringsbehov |

Normaliser delene med faste, konfigurerbare mål per nisje. Ikke bruk min/maks i dagens søkeresultat: da kan en dårlig kandidat få høy score bare fordi resten er verre. Manglende omsettelighetsdata skal ikke fylles inn med en oppdiktet salgssannsynlighet.

| Klasse | Foreløpig regel | Handling |
|---|---|---|
| A – prioriter kontroll | Score ≥80, sterkt datagrunnlag, alle økonomiske krav oppfylt | E-post så raskt datakilden tillater |
| B – interessant | Score 65–79, eller høyere score med uavklarte forhold | Samlerapport / manuell vurdering |
| C – overvåk | Score 50–64 | Vis i oversikt, normalt ingen e-post |
| D – svak mulighet | Score <50 eller økonomiske minstekrav ikke oppfylt | Arkiver begrunnelse |
| U – utilstrekkelige data | Modell, prisbetydning eller prisgrunnlag kan ikke avklares | Ingen påstått fortjeneste |

A er ikke en kjøpsinstruksjon. Alvorlige uavklarte forhold overstyrer score. Kun aktive annonsepriser gir normalt middels vurderingssikkerhet og skal ikke alene utløse A-varsel i piloten. Manuelt validert prisgrunnlag kan brukes, men må merkes som et menneskelig anslag. Høy vurderingssikkerhet betyr heller ikke at skjult feil eller svindel er utelukket.

Forslag til startkrav, som skal kalibreres:

- Kontantgevinst minst 1 000 kr for MacBook og 500 kr for Garmin.
- Avkastning på innsats minst 20 %.
- Økonomisk overskudd positivt ved valgt timeverdi; start med 300 kr/time som en beslutningsparameter.
- Vis et scenario med 10 % lavere videresalgspris. Negativt økonomisk overskudd i dette scenariet nedgraderer A til B.
- Ingen A-varsling ved uavklart pris for pakke/delbetaling, mulig lås, alvorlig skade eller svak modellmatching.

## 6. Første versjon

Arbeidsflyt: **Inndata → produktidentifikasjon → referanser → økonomi → score og kontrollpunkter → e-post → registrert utfall.**

Inkluder:

1. Import av syntetiske og tillatte manuelt registrerte CSV/JSON-data. Grensesnitt for fremtidig godkjent datakilde.
2. Normalisering av merke, modell, variant, tilstand, pris, sted og tilgjengelige tidsstempler.
3. Referansegrunnlag med kilde og dato, separat fra kandidatene som skal vurderes.
4. Forklarbar prisberegning, økonomi, score og risikoflagg.
5. Enkel lokal oversikt med filtre på nisje, klasse og status.
6. E-postutkast som standard; adapter for senere aktiv sending til Anders.
7. Duplikatkontroll, historikk for prisendringer og kontroll mot varselsøppel.
8. Tilbakemelding: uinteressant, feil modell, allerede borte, undersøkt, kjøpt, solgt, returnert eller tap.
9. Handelslogg med faktisk kjøpspris, salg, kostnader, tidsbruk og lagerstatus.

Utsett automatisk kjøp, kontakt med selgere, pruting, reparasjonsprosjekter, bil/eiendom, hele Torget og avansert maskinlæring. Bruk regler og strukturert produktkatalog først. AI kan senere hjelpe med ustrukturert tekst; pris og gevinst må fortsatt bygge på identifiserbare data.

### Innhold i en e-post

Emne: `[FINN FLIPP][A][84/100] Produkt – anslått kontantgevinst 1 300 kr`

Innhold: lenke, annonsert pris, modell/variant, anslått prisintervall, kontantgevinst, økonomisk overskudd, maksimal kjøpspris, relevante referanser, vurderingssikkerhet, viktigste kontrollpunkter og en kort forklaring på hvorfor den er flagget. Alle eksempeltall merkes som demo.

Vis både annonsens alder når den er kjent, tidspunkt mottatt og tidspunkt vurdert. Manglende publiseringstid skal være «ukjent», ikke erstattes med importtid. E-posten skal gjøre det mulig å avgjøre om annonsen er verdt å åpne på under et minutt.

## 7. Prosjektfaser

Tidsangivelsene er arbeidsestimater etter at nødvendige data er tilgjengelige. Tilgangsavtaler kan ta lengre tid og inngår ikke i estimatet.

| Fase | Omtrentlig tid | Leveranse | Beslutning før videre arbeid |
|---|---|---|---|
| 0. Tilgang og rammer | 1–2 arbeidsdager til kartlegging | Databeslutning, 2 nisjer, kapitalramme, geografisk område og terskler | Finnes en realistisk vei til tillatt data? |
| 1. Referanser og manuell test | 3–5 arbeidsdager | Ca. 50–100 relevante referanseobservasjoner totalt, produktkatalog og eksempelvurderinger | Kan objektene identifiseres og verdsettes uten store gjettverk? |
| 2. Lokal MVP | 3–5 arbeidsdager | Kjørbar import, score, oversikt, e-postutkast og handelslogg | Er beregningene riktige og varslene forståelige? |
| 3. Fremoverskuende pilot | 2–4 kalenderuker | Vurderte nye kandidater, sammenligning mot enkel metode og eventuelt få handler | Finnes økonomisk og praktisk merverdi? |
| 4. Drift og utvidelse | Etter positiv pilot | Godkjent dataintegrasjon, drift, aktive varsler og én ny nisje om gangen | Har reell nettogevinst og kapasitet holdt seg? |

Teknisk startforslag: Python, SQLite, Pydantic, en enkel lokal Streamlit-visning og pytest for vesentlig beslutningslogikk. Bruk lokal CLI for import og rapportering; en ekstern scheduler kan komme når kontinuerlig drift er relevant. Dette er en liten analysepipeline, ikke en grunn til å bygge en omfattende skyplattform.

Driftsbudsjett må skille mellom data, eventuell modellbruk, e-post og hosting. Ikke legg til grunn at rask FINN-tilgang er gratis. Ingen betalte abonnementer eller kjøp inngår i selve prosjektplanleveransen.

## 8. Hvordan vi avgjør om prosjektet virker

Lag først en enkel referansemetode: lagret søk + faste prisgrenser per modellgruppe + samme manuelle kontroll. Vår motor skal forbedre dette på samme kandidater, med samme informasjon og sammenlignbart varslingsvolum.

Velg terskler på et tidlig utvalg, frys dem og evaluer på senere kandidater. Bruk bare referanser som var kjent ved vurderingstidspunktet. Registrer vurderinger også når handelen ikke gjennomføres; ellers ser vi bare de vellykkede eksemplene.

Mål:

- Andel av de høyest rangerte som etter kontroll faktisk er verdt å følge opp.
- Andel som fortsatt er tilgjengelige når vi kan handle, og hva årsaken er når de ikke er det.
- Feil modell/konfigurasjon, feil prisbetydning og manglende referanser.
- Estimert mot faktisk salgspris, kostnader, tidsbruk og salgstid der utfallet er kjent.
- Samlet realisert kontantgevinst, økonomisk overskudd og kapital bundet i usolgt lager.
- Tid brukt per brukbar mulighet og merverdi mot referansemetoden.

**Forslag til beslutningsmål:** Etter 100 nye kandidater ønsker vi at minst 60 % av topp 10 er brukbare etter kontroll, og at motoren enten finner flere slike kandidater ved samme kontrolltid eller reduserer tidsbruken merkbart mot referansemetoden. Dette er valgte pilotmål, ikke en prognose. Undersøk også noen lavt rangerte kandidater for å oppdage tapte muligheter.

Før vesentlig oppskalering ville jeg krevd minst 5–10 avsluttede kjøp/videresalg med positivt samlet økonomisk resultat og et ærlig lagerregnskap. Det gir tidlig indikasjon, ikke statistisk sikkerhet. Inkluder usolgte varer til et forsiktig realiserbart anslag og faktiske tap. Et godt resultat i en demo eller noen få kupp dokumenterer ikke en stabil virksomhet.

Stopp eller endre prosjektet hvis datatilgangen blir for dyr/langsom, prisanslagene systematisk er for høye, handelen ikke slår alternativ bruk av tiden, eller motoren ikke tilfører noe utover enkle prisvarsler. Hvis prisvurderingen fungerer, men varslingen er for sen, kan vi teste mer lokale eller mindre tidssensitive nisjer før vi bygger mer teknologi.

## 9. Ferdig prompt til Codex

Kopier teksten i kodeblokken. Prompten ber Codex implementere en lokal MVP, mens faktisk FINN-innhenting er avhengig av dokumentert datatilgang.

```text
Du skal bygge FINN-flippemaskinen for Anders: et lokalt analyseverktøy som identifiserer mulige underprisede brukte varer, beregner realistisk fortjeneste, rangerer dem og lager e-postvarsler.

MÅL OG ARBEIDSFORM
Bygg en fungerende lokal MVP, ikke bare en plan. Les eventuell AGENTS.md og eksisterende prosjekt før endringer. Gjenbruk eksisterende struktur der den passer. Lag ellers et lite Python-prosjekt med SQLite, Pydantic, en enkel Streamlit-visning og pytest for kritisk logikk. Kontroller gjeldende primærdokumentasjon før du velger bibliotekversjoner eller eksterne integrasjoner. Gjør rimelige reversible valg selv og dokumenter dem. Ikke kjøp tjenester, kontakt selgere eller gjennomfør handler.

Forretningsmålet er økonomisk overskudd etter kostnader og tidsbruk. Lav pris eller stor prosentvis rabatt alene er ikke tilstrekkelig. Vi vet ennå ikke om dette er lønnsomt; løsningen skal gjøre hypotesen testbar.

DATA SOM FØRSTE LEVERANSE
Opprett docs/DATA_ACCESS.md med dokumentert status. FINNs publiserte brukervilkår krever eksplisitt skriftlig samtykke for automatisert/systematisk innhenting. Det ordinære FINN-API-et er beskrevet som tilgang til egne annonsedata. FINNs e-postvarsler er beskrevet som daglige, så de er ingen dokumentert sanntidskilde. Kontroller oppdaterte primærkilder før eventuell senere integrasjon.

Ikke implementer eller aktiver FINN-skraping, automatiserte nettleserbesøk, skjulte endepunkter eller omgåelse av tilgangsbegrensninger. Opprett et SourceAdapter-grensesnitt og en deaktivert adapterplassholder for en fremtidig avtalt feed. Den skal kreve dokumentert rettighetsgrunnlag og kildekonfigurasjon og stoppe tydelig hvis det mangler. En vanlig config-bryter alene er ikke dokumentasjon på tilgang.

Bygg fungerende import fra lokale CSV/JSON-filer og en eksplisitt syntetisk demokilde. Importer bare brukerdata som er avklart for bruken. Ikke anta at e-postimport eller en tredjeparts skrapetjeneste automatisk gir rett til videre behandling. En kandidat-URL skal bare vises som lenke og aldri automatisk åpnes eller hentes.

Ingen datatilgang skal blokkere lokal utvikling med demo. Skill klart mellom demonstrert programfunksjon og utestet markedsmulighet.

PILOTOMFANG
To konfigurerbare produktfamilier: utvalgte MacBook Air med Apple-chip og utvalgte Garmin-klokker. Bruk en liten eksplisitt produktkatalog med totalt ca. 5–10 eksakte modell-/konfigurasjonsgrupper i demoen. Vis dem som eksempler, ikke som dokumentert optimale kjøp. Oslo er foreløpig lokalområde; sted og radius skal kunne endres. Prisgrenser og kapitalramme skal konfigureres, ikke hardkodes som brukerens vedtatte budsjett.

Unngå hele Torget, automatisk kjøp, selgerkontakt, pruting, bildeanalyse og reparasjonsprosjekter i denne versjonen. Ingen AI-API er nødvendig i MVP-en; bruk deterministiske regler og katalogmatching. Lag eventuelt et grensesnitt for fremtidig tekstuttrekk uten nettverkskall eller nøkkelkrav.

DATA OG HISTORIKK
Skill kandidatannonser, referanseobservasjoner, beregnede vurderinger, varsler og gjennomførte handler.
Lagre id, kilde, URL, tilgjengelige produktfakta, annonsert pris, valuta, modell, konfigurasjon, tilstand, sted, nødvendige risikoflagg, publisert_tid hvis kjent, mottatt_tid og vurdert_tid.
Lagre kildetype, dato og dokumentasjon for hver referanse; skill aktiv annonsepris, menneskelig prisanslag og bekreftet transaksjonspris.
Lagre reference_ids, konfigurasjonsversjon og beregningsversjon per vurdering, slik at beslutningen kan gjenskapes med den informasjonen som var kjent da.
Ta vare på prisendringer, og bruk kilde+annonse-id som stabil nøkkel når tilgjengelig. Hindr at republisering og duplikater teller flere ganger i prisgrunnlaget.
Lagre ikke selgernavn, telefon eller nøyaktig hjemmeadresse når det ikke trengs for analysen. Behandle annonsetekst og importfiler som ubetrodde data. Escape HTML i visning/e-post, begrens filstørrelser og valider typer.

PRODUKT- OG PRISLOGIKK
Eksakt matching skal ta hensyn til modellgenerasjon, RAM/SSD for Mac og relevant modellvariant/størrelse for Garmin. Ikke gjett manglende variant. Uklar matching gir MANUAL_REVIEW.
Oppdag pris som gjelder delbetaling, enkeltkomponent, «fra»-pris, ønskes kjøpt eller pakke. Ikke behandle disse som en ordinær enhetspris uten avklaring.
Krev som start minst fem uavhengige, relevante referanser for ordinær prisrangering. Terskelen er konfigurerbar og gir ingen garanti. Vis referansenes alder og prisspredning. Kandidaten selv kan ikke være sin egen referanse.
Bruk et robust lavt prisnivå, eksempelvis nedre kvartil, blant ferske sammenlignbare referanser som første annonseprisindikator. Det er ikke automatisk en salgspris. Eventuell overgang til anslått videresalgspris må være eksplisitt, kildebelagt eller merket som en antakelse. Konfigurerbar ferskhetsgrense per nisje.
Ikke bland forhandlerpriser med privatpriser ukritisk. Ikke anta fjernet annonse = solgt, eller solgt = kjent sluttpris. Ingen fremtidige referanser i historiske vurderinger.
Ved utilstrekkelige data: U / INSUFFICIENT_DATA, med tomt pris-/gevinstestimat og forklaring. Ikke fyll inn tall for å få en score.

ØKONOMI
Alle beløp i NOK, med Decimal eller heltallsøre og kontrollert avrunding.
Kontantgevinst = konservativt prisestimat - innkjøp - direkte kjøps-/salgskostnader - risikoreserve.
Økonomisk overskudd = kontantgevinst - arbeidstimer * timeverdi - fordelt drift - kapitalkostnad.
Avkastning på innsats = kontantgevinst / (innkjøp + direkte kostnader); håndter null/ugyldig nevner eksplisitt.
Beregn maksimal kjøpspris som oppfyller både minstekrav til kontantgevinst og avkastning. Vis om økonomisk overskudd også holder. Ikke anta rabatt på annonsert kjøpspris. Muligheter som krever pruting skilles fra muligheter til prisantydning.
Vis scenario med 10 % lavere videresalgspris. Unngå dobbelttelling mellom kjente reparasjoner og risikoreserve.
Vis at resultater er før inntektsskatt. MVA-behandling kan være uavklart; ikke anta null som et bekreftet forhold eller implementer uverifisert skatteberegning. Dokumenter forutsetningene før faktisk handel.

SCORE OG VARSLINGSKRAV
Forklarbar 0–100-score: 35 % kontantgevinst i kroner, 20 % avkastning på innsats, 20 % styrke i verdsettelsesgrunnlaget, 15 % omsettelighet og 10 % gjennomførbarhet.
Bruk faste konfigurerbare mål per nisje for normalisering, ikke min/maks i dagens kandidatsett. Vis delscore, vekter og årsaker. Manglende salgstidsdata må merkes som ukjent, ikke en kalibrert sannsynlighet. Vurderingssikkerhet vises separat fra score og er ikke sannsynlighet for gevinst.
A: >=80 OG alle økonomiske krav OG sterkt grunnlag OG ingen alvorlige uavklarte forhold.
B: 65–79 eller høyere score som trenger mer avklaring.
C: 50–64. D: <50 eller økonomiske minstekrav som feiler. U: utilstrekkelig pris-/produktgrunnlag.
Kun aktive annonsepriser skal normalt gi maksimalt middels vurderingssikkerhet og ikke alene A-varsel. Menneskelig godkjente prisanslag merkes eksplisitt og kan ikke presenteres som bekreftede transaksjoner.
Foreløpige konfigurerbare terskler: minimum 1 000 kr kontantgevinst for MacBook og 500 kr for Garmin; minst 20 % avkastning; positivt økonomisk overskudd; timeverdi 300 kr/time. Negativt økonomisk overskudd i 10 %-scenario nedgraderer A til B. Dette er pilotparametere som skal testes.
Uavklart aktiveringslås/organisasjonsadministrering, alvorlig skade eller uklar prisbetydning blokkerer A uansett score. Fravær av en feilbeskrivelse beviser ikke at varen er kontrollert.

OVERSIKT OG E-POST
Lag en enkel lokal visning med filtre for nisje, klasse og status. Vis kandidat, prisintervall/antakelser, gevinst, økonomisk overskudd, maksimal kjøpspris, referanser, delscore, sikkerhet, risiko og datatidspunkter.
Lag HTML- og tekstutgave av e-post. A gir prioritert varsel, B samlerapport. Ingen utsending av U som kupp. Vis annonsealder bare hvis publiseringstid er kjent; vis alltid mottatt_tid og vurdert_tid.
Standard er DRY_RUN: lagre e-postutkast lokalt og vis forhåndsvisning. SMTP-adapter skal bare sende ved eksplisitt aktivert konfigurasjon til en angitt eieradresse. Ingen credential i repo eller logger. Implementer ikke faktisk kontooppkobling som en forutsetning for demo.
Bruk varslingslogg/outbox med stabil dedupliseringsnøkkel. Ingen nye varsler for uendret annonse. Prisendring eller vesentlig bedre vurdering kan gi nytt varsel etter konfigurerbar pause. Håndter delvis sendefeil og beskriv at SMTP ikke gir en absolutt garanti mot duplikater ved tvetydig levering.

LÆRING OG VALIDERING
Registrer tilbakemelding: irrelevant, feil modell, allerede borte, undersøkt, kjøpt, solgt, returnert og tap. Lagre faktisk innkjøp, salgspris, direkte kostnader, timer, datoer og usolgt lager. Beregnet resultat og realisert resultat må vises hver for seg.
Implementer en enkel baseline med faste prisgrenser per eksakt modellgruppe på samme kandidatgrunnlag. Lag CSV-rapport som sammenligner brukbare toppkandidater og kontrolltid når menneskelige etiketter finnes. Ikke presenter nøyaktighet/fortjeneste som målt uten reelle etiketter/handler.

LEVERANSER OG AKSEPTANSE
1. README med oppsett, få tydelige kommandoer og begrensninger.
2. docs/DATA_ACCESS.md, arkitektur- og scorebeskrivelse, konfigurasjonseksempel og dataskjema.
3. Syntetiske fixtures med tydelig DEMO-merking, to nisjer og nok uavhengige referanser per fullstendig eksempel. Ingen påstått ekte FINN-annonselenke; bruk example.invalid for demolenker.
4. Fungerende flyt: importer demo -> identifiser -> verdsett -> score -> vis oversikt -> lag e-postutkast -> registrer handelsutfall.
5. Tester for økonomiformler, avrunding, prisvarianter, eksakt matching, manglende referanser, uavklart lås, scoregrenser, stresscenario, duplikater og historisk informasjonsgrunnlag. Ingen test skal være avhengig av live-FINN.
6. Demonstrer en attraktiv kandidat, en som ser billig ut men feiler etter kostnader, en med feil konfigurasjon, en med utilstrekkelige data og en med alvorlig uavklart feil. Demonstrer at terskler kan justeres uten kodeendring.
7. Lokal oppstart og relevante tester skal kjøres. Ikke hev at FINN-skanning, faktisk e-postlevering eller lønnsomhet er verifisert når dette bare er simulert.

Start med et kort implementeringsoppsett, bygg deretter hele MVP-en og kontroller flyten. Avslutt med hva som virker, hvordan jeg starter den, testresultater og hva som konkret gjenstår før tillatt live-data og aktive e-postvarsler kan brukes.
```

## 10. Kilder kontrollert 17. oktober 2026

1. [FINN – brukervilkår, særlig punkt 6](https://www.finn.no/vilkar/brukervilkar-finn).
2. [FINN Hjelpesenter – API og tilgang til egne data](https://hjelpesenter.finn.no/hc/no/articles/22629030477202-API).
3. [FINN Hjelpesenter – varslinger på e-post](https://hjelpesenter.finn.no/hc/no/articles/22651852160786-Varslinger-p%C3%A5-e-post).
4. [FINN Hjelpesenter – varslinger i appen](https://hjelpesenter.finn.no/hc/no/articles/22652337506834-Varslinger-i-appen).
5. [Apple – aktiveringslås for Mac](https://support.apple.com/no-no/102541).
6. [Skatteetaten – er jeg næringsdrivende?](https://www.skatteetaten.no/bedrift-og-organisasjon/starte-og-drive/er-jeg-naringsdrivende/).

Kildene dokumenterer tilgangsrammer, varslingsfunksjon, en produktrisiko og generelle næringskriterier. De dokumenterer ikke at de foreslåtte nisjene gir fortjeneste. Alle pilotmål, scorevekter, priseksempler og tidsestimater i planen er forslag.
