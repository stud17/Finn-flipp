# Pris, økonomi og prioritering

Alle pilotparametere ligger i `config.json`; de er forslag til testing. Ingen demo-pris er en markedsobservasjon.

## Identifikasjon og referanser

Produktkatalogen inneholder åtte eksakte grupper. Mac krever merke, generasjon, modellvariant, RAM og SSD. Garmin krever modell, variant og størrelse. Normalisering ignorerer bare bokstavstørrelse og ytre mellomrom. Ufullstendige opplysninger eller en annen variant gir `U / MANUAL_REVIEW`, uten pris, gevinst eller score.

Nettskraperen trekker eksplisitte fakta fra avgrenset produkttekst før katalogmatching. M1 Air kan identifiseres som 13-tommersfamilien fra 2020 fordi dette er samme modellfamilie i [Apples spesifikasjon](https://support.apple.com/en-us/111883); den gjetter ikke RAM/SSD. M2 krever avklart skjerm-/årsvariant. Garmin uten avklart variant/størrelse gir fortsatt U. Tilbehørstitler filtreres før detaljlesing. Dette er deterministiske regler og kan avstå; ingen AI fyller ut manglende fakta.

Parser 1.2 skiller eksplisitte sammenligningssetninger om standardmodeller og selgerens erstatningsmaskin fra den annonserte maskinen. En M2 16/512 forkastes derfor ikke automatisk fordi teksten også sammenligner med standardmodellens 8 GB og nevner en ny jobb-Mac med M5. Faktiske motstridende opplysninger om salgsobjektet gir fortsatt ukjent konfigurasjon. En eksplisitt liten GB-kapasitet på en M1/M2 Air kan tolkes som minne også uten ordet «RAM»; manglende GB-tall erstattes aldri med en standardkonfigurasjon.

Delbetaling, enkeltkomponent, fra-pris, pakke og kjøpsønske avvises både via strukturert `price_meaning` og et begrenset sett tekstregler. Tekstreglene dekker ikke alle formuleringer: inndata må kontrolleres manuelt. Vi forsøker ikke generell AI-identifikasjon.

Referanser må gjelde samme eksakte produkt, tilstand og demo-/reell kildekategori, være private, ha positiv pris, være tilstrekkelig ferske og være kjent ved vurderingstidspunktet. Importtid fungerer som ytterligere nedre grense for når en referanse var kjent. Forhandlerpriser utelates. Ingen tilstandsjustering gjøres automatisk.

Identiteter forenes transitivt ved global `entity_id`, kilde+annonse-ID og URL uten sporing/fragmentsuffiks. Kandidaten og dens gjenpubliseringer utelates. Nyeste kjente referanse beholdes per vare. `entity_id` må tildeles samme fysiske vare på tvers av republiseringer; systemet kan ikke bevise uavhengighet når en importør feilaktig tildeler helt nye identiteter og lenker. Uavhengighet er en eksplisitt datakvalitetsforutsetning.

Minst fem uavhengige, sammenlignbare referanser kreves som standard. Vi velger en komplett gruppe i rekkefølgen bekreftede oppgjør → menneskelige prisanslag → aktive annonsepriser. Hver kildetype må selv ha minst konfigurasjonens minimum; prisbetydninger blandes ikke for å fylle opp antallet. Dokumentert kildetype, antall, alder, spredning og verdsettelsesreferanser lagres.

Lavt prisanslag er nedre kvartil, med lineær interpolasjon. Øvre anslag er øvre kvartil. Intervallet beskriver referansepriser; det er ikke et statistisk sikkerhetsintervall. Aktive annonsepriser reduseres med konfigurert `asking_discount` (10 % som uvalidert startantakelse). For oppgjør og menneskelige anslag brukes ingen skjult rabatt. Estimater fra mennesker merkes uttrykkelig.

## Økonomi

Decimal og kommersiell avrunding til to desimaler brukes for NOK; ROI beregnes med Decimal uten prosentavrunding i beslutningen.

```text
investert = kjøpspris + direkte kostnader
kontantgevinst = videresalgsanslag − investert − risikoreserve
økonomisk overskudd = kontantgevinst − timer × timeverdi − fordelt drift − kapitalkostnad
ROI = kontantgevinst / investert
```

Direkte kostnader summerer transport, frakt, emballasje, gebyrer, tilbehør og kjent reparasjon. Reserve er for usikre tap og skal ikke inkludere kjent reparasjon på nytt. Ukjent alvorlig feil må avklares. Objektets eksplisitte `costs` erstatter hele standardkostnadsobjektet; delvis overskriving/automatisk summering brukes ikke. Manglende kostnader bruker synlig merkede nisjeanslag.

Maks kjøpspris for minstekrav til kontantgevinst G og avkastning R:

```text
min(videresalg − direkte − reserve − G,
    (videresalg − reserve) / (1 + R) − direkte)
```

Prisen rundes **ned** til nærmeste øre. Negativt resultat betyr ingen mulig ikke-negativ kjøpspris og vises som tom grense, ikke som en garantert lønnsom pris på 0 kr. Økonomisk overskudd ved denne grensen vises separat. En egen grense krever minst ett øre positivt økonomisk overskudd. Stresscenarioet bruker 90 % av lavt videresalgsanslag med de samme kostnadene. Ingen pruting forutsettes. D-kandidater som kan oppfylle krav ved lavere kjøpspris merkes `NEGOTIATION_OPPORTUNITY`.

Resultater er før inntektsskatt. MVA er uavklart, og ingen MVA- eller skatteberegning er implementert. Faktisk handelsresultat trekker faktiske kostnader, tidsverdi, drift og kapitalkostnad; en budsjettert risikoreserve trekkes ikke som om den var et realisert tap.

## Score

| Del | Vekt | Fast normalisering |
|---|---:|---|
| Kontantgevinst | 35 % | Gevinst / nisjens gevinstmål, begrenset til 0–100 |
| ROI | 20 % | ROI / nisjens ROI-mål, begrenset til 0–100 |
| Prisgrunnlag | 20 % | 100 for nok bekreftede oppgjør, 85 for nok menneskelige anslag, 55 for nok annonsepriser |
| Omsettelighet | 15 % | Måldager / median dokumentert salgstid, begrenset til 100; minst tre salgstider kreves |
| Gjennomførbarhet | 10 % | Måltimer / estimerte arbeidstimer, begrenset til 100; uavklarte kontrollpunkter gir 25 |

Manglende salgstidsdata gir synlig «ukjent» og 0 på denne delen, ikke en oppdiktet sannsynlighet. Totalscoren er vektet sum, avrundet til to desimaler før klassegrensene. Dagens kandidatsett påvirker aldri normaliseringen. Vurderingssikkerhet vises separat og er ikke en sannsynlighet for gevinst.

U krever avklaring av produkt, pris eller grunnlag. Med prisgrunnlag gjelder A ≥80, B ≥65, C ≥50 og D <50. Økonomiske minstekrav som feiler gir alltid D. A krever også sterkt grunnlag, ingen uavklarte kontrollpunkter, positivt ordinært økonomisk overskudd og ikke-negativt stressresultat. En høy score med blokkert A gir B. Bare aktive annonsepriser gir maksimalt middels sikkerhet og aldri A.

Kontrollpunkter omfatter Mac-aktiveringslås, MDM, manglende funksjonskontroll, alle eksplisitte risikoflagg, uavklart transport/avstand og overskredet kapitalramme for objektet. Avstand er brukerregistrert og må gjelde konfigurert utgangspunkt; det gjøres ingen geokoding. A betyr prioriter kontroll, ikke automatisk kjøp.

## Pilot og baseline

Baseline bruker faste kjøpsprisgrenser per eksakt kataloggruppe med samme tilgjengelige fakta. CSV viser motorens rangering, baseline utvalg og rangering (pris relativt til fast modellgrense), topp 10, menneskelig brukbarhetsvurdering, kontrolltid og faktiske resultater. Rangeringer beregnes separat for demo og reelle data. `matched_volume` velger minimum av ti og antall tilgjengelige kandidater fra hver metode; `engine_matched_volume` og `baseline_matched_volume` markerer like store sammenligningsutvalg. U-kandidater får ingen motorrangering. Felter uten reelle etiketter eller handler står tomme. Ingen målt presisjon hevdes.

Frys konfigurasjonen på et tidlig utvalg og bruk en separat fremoverskuende periode. Sammenlign samme antall kandidater og samme tidsbudsjett, og kontroller noen lavt rangerte varer. CSV-en er et vurderingsgrunnlag, ikke en automatisk konklusjon om lønnsomhet.
