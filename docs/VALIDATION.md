# Validering – 19. oktober 2026

## Resultat

Lokal MVP kjørt på macOS med Python 3.12.14, Pydantic 2.14.1, Streamlit 1.66.0 og pytest 9.1.1. Det fullstendige installerte miljøet er låst i `requirements.lock.txt`.

**108 tester bestått. Ruff bestått.** Testene bruker en fast klokke for at statiske demoobservasjoner ikke skal gjøre testene tidsavhengige. Ingen automatisk test krever FINN eller et eksternt e-postsystem.

## Positivt filter og morgenjobb

Oversikten starter med økonomisk overskudd > 0 kr som filter. Nye tester skiller dette fra positiv kontantgevinst og utelukker null, ukjent, fjernet, foreldet detaljkontroll, lesefeil, annonser som ikke ble sett i siste søk, demo og kandidater som allerede er behandlet. Positiv C/D er tillatt uten å endre motorens klassegrenser. Rapportgenerering kvitterer ikke varsler; eksplisitt kvittering husker dem, og ny melding krever lavere pris og minst 250 kr bedre økonomisk anslag.

`morning` er også kjørt mot offentlige FINN-sider 19. oktober kl. 18:26 Oslo-tid: 49 annonser, null kildefeil og null positive muligheter. Rapporten ligger i `data/morning-report.json`. Daglig kjøring kl. 08:00 er aktivert i denne Codex-chatten, automasjon `finn-positive-muligheter-hver-morgen`. Datamaskinen og Codex må være på for lokal kjøring.

## Konkrete gevinstestimater

Et målrettet tilleggssøk på MacBook Air M1/256 GB og parser 1.2 ga 49 kandidater, 46 prisobservasjoner og ingen innlesingsfeil ved 54 forespørsler. Åtte ekte annonser fikk nå gevinstestimater med sju sammenlignbare referanser hver. Alle åtte fikk D fordi økonomien er negativ med konfigurerte forutsetninger. De øvrige 41 synlige FINN-kandidatene hadde fortsatt utilstrekkelig grunnlag. Det er ikke senket krav til referanseantall eller endret kostnader for å produsere et resultat.

Eksempel fra Oslo: kjøpspris 4 500 kr, lavt videresalgsanslag 4 275 kr, kontantgevinst −825 kr og økonomisk overskudd −1 555 kr. Dette bygger på annonsepriser og en eksplisitt antatt salgsrabatt; det er ikke et kjent oppgjør. [Alle åtte vurderinger, regnestykke og referanser](LIVE_ASSESSMENTS.md).

Parserfeilen som ble rettet: En annonse om egen M2 16/512 kunne sammenligne med standardmodellens 8 GB RAM og nevne selgerens nye jobb-Mac med M5. Tidligere regler blandet disse opplysningene. Nye tester verifiserer at slike eksplisitte sammenligninger ikke overstyrer salgsobjektet, samtidig som faktiske motstridende konfigurasjoner fortsatt gir U. Manglende minne-/lagringstall fylles ikke ut med en standardkonfigurasjon.

## Tillegg: ekte FINN-data

Etter Anders' instruks om nettskraping er `PublicFinnAdapter` implementert og kjørt mot offentlige sider. Første komplette kjøring 19. oktober startet 17:32:59 og avsluttet 17:34:03, Oslo-tid: 29 kandidater, 27 prisantydningsreferanser, 33 forespørsler, ingen innlesingsfeil og ingen nye e-postutkast. Fire søk ga opptil åtte kort hver; overlapp mellom søk ble deduplisert.

Alle 29 fikk U i første kjøring. Bare to hadde full katalogmatch med første parsers regelsett; disse manglet nok sammenlignbare referanser. Dette er en konkret begrensning i identifikasjon og referansedekning, ikke en påvist lønnsom mulighet. Første kjøring viste også tilbehørstreff; parser 1.1 filtrerer gjenkjente ladekabler, reimer og iPad-titler før detaljinnhenting, støtter flere skrivemåter for tommer og bruker en kildebelagt identifikasjon av M1 Air-familien. Ufullstendige produktfakta gjøres fortsatt ikke om til sikre varianter.

Tilleggstestene dekker offentlig HTML/JSON-LD, deklarativ Shadow DOM, prisformat, privat/ukjent selgertype, ufullstendige fakta, tilbehørsfilter, mellomlagring, oppdatering av pris og parser-versjon, bevart første mottakstid, transaksjonell pause mellom kjøringer, blokkering/innlogging, at rå selgeropplysninger ikke lagres, og at fjernede annonser trekkes ut av aktivt referansegrunnlag uten å bli tolket som oppgjør. AppTest dekker også FINN-filteret og knappen for innhenting med en simulert transport.

FINNs synlige søkefilter «Privat» ble valgt i en nettleser og ga `dealer_segment=1`; «Nyeste først» ga `PUBLISHED_DESC`. Kildevalget henter offentlig HTML uten API-nøkkel. Det er ikke en dokumentert API-avtale eller en måling av garantert publiseringsforsinkelse.

En ny komplett innhenting med parser 1.1 hentet 32 annonser og 29 prisantydninger, brukte 36 forespørsler og ga ingen innlesingsfeil. Den hoppet over 34 tilbehørskort i de fire førstesidene før utvalget på åtte per søk. 17 kandidatrevisjoner ble lagret; øvrige kandidatfakta var uendret. Ingen nye utkast ble opprettet. FINN-visningen viste 32 kandidater med klasse U, og nettleserkontrollen fant ingen JavaScript-feil. Eldre tilbehørstreff er bevart i historikken og kan sees under «Alle».

| Kontroll | Resultat |
|---|---|
| Installasjon via `bash scripts/setup.sh` | Kjørt; alle låste avhengigheter tilgjengelige |
| Demoimport | 56 referanser, 11 kandidater, åtte eksakte kataloggrupper |
| Gjentatt demoimport | Ingen nye uendrede revisjoner eller dupliserte utkast |
| Ordinær demovurdering | 1 A, 2 B, 1 C, 2 D, 5 U |
| Utkast fra ren database | Ett prioritert A-utkast og én B-samlerapport; HTML og tekst |
| Oppfølging | Syntetisk tilbakemelding, avsluttet handel og usolgt lager registrert via CLI |
| Sammenligning | CSV eksportert med separate demo-/reelle rangeringer og likt sammenligningsvolum |
| Lokal server | Startet på 127.0.0.1:8501; `/_stcore/health` returnerte `ok` |
| Streamlit AppTest | Oversikt og familie-/klassefiltre kjørt uten unntak |
| Faktisk nettleser | Lokal app åpnet med Playwright og installert Chrome; ingen registrerte JavaScript-feil |

## Viktig beslutningslogikk som er testet

- Regneeksemplets gevinst, overskudd, ROI og stresscenario; øreavrunding, gulvavrunding av maksimal kjøpspris, ugyldige/ikke-endelige beløp og nullnevner.
- Eksakt RAM, SSD, modellvariant og klokkestørrelse; manglende variant gir U uten oppdiktede estimater.
- Delbetaling, deler, fra-pris, kjøpsønske og pakkepris, også når feil strukturert som enhetspris.
- Utilstrekkelige referanser, feil tilstand, fremtidige/for gamle referanser, importtid som kunnskapsgrense, forhandlerpriser og skille mellom demo/reelle data.
- Kandidaten som egen referanse, republisering og transitiv duplikatidentitet; betydningsfulle URL-parametere som annonse-ID bevares mens sporing fjernes.
- Klassegrenser 50/65/80, økonomiske overstyringer, aktiveringslås/MDM, ukjent funksjonskontroll, risiko og geografisk avklaring.
- Bare annonsepriser gir aldri A; menneskelige estimater er uttrykkelig merket; manglende salgstider gir ingen oppdiktet sannsynlighet.
- Prisendringer og retur til gammel pris lagres; full vurdering kan rekonstrueres fra snapshot.
- Dedupliserte utkast, pause mellom endringer, HTML-escaping, ukjent publiseringstid og bortfalt relevans etter tilbakemelding.
- Rettighetsmanifest er bundet til riktig fil og bevisdokument. Live-plassholder og DRY_RUN stopper nettverksbruk.
- SMTP-stub verifiserer angitt eieradresse, feil før sending, tvetydig levering og at sistnevnte ikke gjentas automatisk. Demo sendes aldri.
- Faktisk oppgjør holdes separat fra estimater. Lager gir ikke realisert gevinst. CSV finner på verken etiketter, kontrolltid eller målte oppgjør.

## Demonstrerte tall – bare syntetiske

Air M1 8/256-eksemplet får et lavt videresalgsanslag på 6 800 kr, kontantgevinst på 3 800 kr og økonomisk overskudd på 3 070 kr. Med 10 % lavere videresalg er økonomisk overskudd 2 390 kr. En annen Mac ser billig ut, men gir −500 kr etter de registrerte kostnadene og tidsbruken. En Mac med uavklart lås får B selv med høy score. Fem kandidater får U uten gevinstestimat.

Demo-handelen med oppdiktet oppgjør 6 500 kr gir kontantresultat 3 800 kr og økonomisk resultat 3 070 kr etter faktiske kostnader/tid. Dette er ikke et reelt salg. Usolgt Garmin-demo har 980 kr kapital bundet og 2 200 kr oppdiktet forsiktig lageranslag; ingen realisert gevinst.

En separat konfigurasjonsfil satte minstekrav til gevinst til 10 000 kr for Mac og 5 000 kr for Garmin. Samme fixtures ga da seks D og fem U, og ingen utkast. Dette ble kjørt via `--config` med en separat database, uten kodeendringer. Standardkonfigurasjonen ble ikke endret av eksperimentet.

## Praktiske begrensninger

Offentlig FINN-innhenting er teknisk verifisert. Avtalt live-feed, virkelig SMTP-levering, faktisk etterspørsel, realiserte salgspriser og lønnsomhet er ikke validert. Videre pilot trenger dekkende referanser, kontroll av varene og dokumenterte utfall. Tilstand og uavhengighet er avhengig av korrekte inndata; programmet kan ikke avdekke alle skjulte feil, feilaktige identiteter eller falsk dokumentasjon.

Kapitalgrensen kontrollerer ett objekt; samlet lagerkapital må vurderes manuelt. Skatte-/MVA-behandling er ikke beregnet. Lokale data har ingen offentlig innlogging eller skybackup. Dette er et lokalt enkeltbrukerverktøy.

Skjermbilder fra lokal demo: [oversikt](preview.png), [handelslogg](journal-preview.png) og [mobilvisning](mobile-preview.png).

Ekte FINN-visning etter serveroppstart og ny innhenting: [live-visning](live-preview.png). Nettleserkontrollen fant ingen JavaScript-feil, viste 32 annonser etter filtrering av eldre tilbehørstreff, og bekreftet at innhentingsknappen er tilgjengelig uten demo-advarsel. En serveromstart var nødvendig fordi den tidligere prosessen holdt en gammel importert databasemodul i minnet; data ble bevart.
