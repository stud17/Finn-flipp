# Dataskjema og import

JSON er en toppnivåliste av objekter; kandidater og referanser importeres separat. CSV har overskrifter med samme feltnavn. De sammensatte feltene `product`, `costs` og `risk_flags` lagres som JSON i CSV-celler (se `fixtures/candidates.csv`). Tom CSV-celle betyr manglende valgfritt felt. UTF-8 og UTF-8 med BOM støttes. Decimal-beløp skrives helst som strenger med punktum og høyst to desimaler.

## Felles observasjon

| Felt | Type | Betydning |
|---|---|---|
| `id`, `source` | tekst, maks 100/80 | Stabil annonse-/observasjons-ID og kilde; bokstaver, tall, `_`, `-`, `.` |
| `entity_id` | tekst, maks 160 | Global identitet for samme fysiske vare, også ved republisering/annen kilde |
| `url` | HTTP(S)-URL | Kun manuell lenke; aldri automatisk henting |
| `title` | tekst, maks 250 | Kort produktbeskrivelse uten personopplysninger |
| `product` | objekt | Eksakte produktfakta, se under |
| `price` | NOK-desimal ≥0 | Annonsert pris for kandidat; pris med referansens uttrykkelige betydning for referanser |
| `currency` | `NOK` | Ingen valutakonvertering |
| `condition` | enum | `excellent`, `good`, `fair`, `damaged`, `unknown` |
| `demo` | bool, standard false | Demo krever `example.invalid` eller et underdomene |

`product` har `family` (`macbook`/`garmin`), `brand`, `model`, `variant`, `ram_gb`, `ssd_gb`, `size_mm`. Urelevante konfigurasjonsfelt er `null`. Modellnavn og variant må samsvare med `config.json`; motoren gjetter ikke manglende verdier. Null eller ukjent pris/tilstand vurderes ikke som ordinært kupp.

## Kandidater

Tillegg til fellesfeltene:

| Felt | Betydning |
|---|---|
| `received_at` | Påkrevd tidspunkt med tidssone |
| `published_at` | Kjent publiseringstid med tidssone eller null; ukjent erstattes ikke med importtid |
| `updated_at` | Separat kjent «sist endret» hos kilden; erstatter ikke publiseringstid |
| `seller_type` | `private`, `dealer`, `unknown`; skraperen bekrefter privat via offentlig søkefilter |
| `availability` | `active`, `removed`, `unknown`; borte betyr ikke kjent oppgjør |
| `location` | Sted, standard `ukjent` |
| `distance_km`, `distance_origin` | Registrert avstand og utgangspunkt; A krever avklart lokal transport eller tillatt frakt |
| `shipping_possible` | Bool, standard false |
| `price_meaning` | `unit`, `installment`, `component`, `from`, `wanted`, `bundle`, `unknown` |
| `price_note` | Kort avklaring av prisens betydning, maks 500 tegn |
| `risk_flags` | Liste over eksplisitte uavklarte risikoer, maks 30 × 100 tegn |
| `activation_lock`, `mdm` | `cleared`, `unknown` eller `locked`; standard unknown |
| `inspected` | Eksplisitt utført kontroll, standard false |
| `costs` | Fullstendig kostnadsobjekt eller null for merkede nisjestandarder |

Kostnader: `transport`, `shipping`, `packaging`, `fees`, `accessories`, `repair`, `risk_reserve`, `overhead`, `capital_cost` (NOK) og `hours` (desimal). Alle beløp er ikke-negative. Et eksplisitt kostnadsobjekt erstatter nisjestandardene, det er ikke en delvis sammenslåing. Kjent reparasjon og usikker reserve må ha atskilte formål.

## Referanser

| Felt | Betydning |
|---|---|
| `kind` | `asking` = aktiv annonsepris, `human_estimate` = menneskelig prisanslag, `transaction` = kjent oppgjør |
| `seller_type` | `private`, `dealer` eller `unknown`; bare avklart privatgrunnlag brukes i piloten |
| `availability` | Aktive annonsepriser brukes bare når `active`; `removed` trekker dem ut av grunnlaget for nye vurderinger |
| `observed_at` | Tidspunkt for observasjonen, med tidssone |
| `known_at` | Når referansen var kjent, ikke før observasjon; effektiv grense er også minst faktisk importtid |
| `documentation` | Kildegrunnlag/dato og hva prisen betyr, 5–1500 tegn |
| `days_to_sell` | Heltall eller null; dokumentert salgstid godtas kun for `transaction` |

Fjernet eller solgtmerket annonse uten kjent oppgjør er ikke `transaction`. Opplysningene må være relevante og ha reelt kildegrunnlag. Importøren har ansvar for at `entity_id` og dokumentasjon beskriver uavhengighet og prisbetydning korrekt.

## Lagring

| Tabell | Innhold |
|---|---|
| `metadata` | Skjemaversjon 2; tidligere data bevares, nye kildetabeller/kolonne legges til ved oppstart |
| `observations` | Append-only revisjoner av kandidater/referanser med stabil nøkkel, importtid, digest og validert JSON |
| `imports` | Importtid, type, filhash og rettighetsmanifest/demoproveniens |
| `assessments` | Alle vurderingskjøringer med fullstendig snapshot, referanse-ID-er og konfigurasjons-/beregningsversjon |
| `outbox` | Subject, tekst og escapet HTML, dedupliseringsnøkkel, vurderinger, status, forsøk og feiltype |
| `alert_events` | Sist varslet pris/score/klasse per fysisk vare |
| `feedback` | Append-only status, brukbarhet, tidsbruk og demo-merking |
| `trades` | Siste registrerte handel per kandidat |
| `trade_history` | Alle tidligere versjoner av handelen, også korrigerte beløp |
| `scrape_runs` | Start/slutt, kjørestatus, antall forespørsler og kildefeil |
| `live_items` | Sist sett i søk, sist kontrollert detaljside, søkenavn, uttrekksmerknader, parser-versjon og feiltype |

Fysiske vareidentiteter dedupliserer referanser og varsler, mens kilde+annonse-ID bevarer hver annonsehistorikk. Globale og stabile identiteter må følge dataene. SQL-spørringer bruker parameterbinding. Skjemaet er en første lokal versjon; lag en eksplisitt migrering ved senere strukturendring.

## Tilbakemelding og handel

`Feedback`: `candidate_key`, `status`, `usable` (bool/null), `review_minutes`, `at`, `demo`.

Statusverdier: `irrelevant`, `wrong_model`, `gone`, `investigated`, `bought`, `sold`, `returned`, `loss`.

`Trade`: `candidate_key`, `bought_at`, `purchase`, `costs`, `hourly_value`, `status`, `sale`, `closed_at`, `inventory_value`, `demo`.

Handelsstatus: `inventory`, `sold`, `returned`, `loss`. Avsluttet handel krever faktisk oppgjør (også null ved totalt tap) og avslutningsdato. Lagerhandel kan ikke ha salgsoppgjør. Retur registrerer faktisk refundert beløp i `sale`. `inventory_value` er et forsiktig anslag, aldri realisert gevinst. Faktisk resultat bruker faktiske kostnader og trekker ikke en hypotetisk risikoreserve. Beløpene må være komplette, også frakt og kostnader som ikke ble refundert ved retur. Eksempler ligger i `fixtures/trade-*.json` og `fixtures/feedback.json`.

UI støtter en enkel totalsum for direkte kostnader; CLI kan registrere hver kostnadskomponent. Den totalsummen lagres i transportfeltet og merkes som samlet direkte kostnad i UI; bruk strukturert CLI-import for detaljert kostnadsregnskap.

Maskinlesbare JSON Schema-filer finnes i `docs/schemas/` for kandidater, referanser, konfigurasjon, rettighetsmanifest, tilbakemeldinger og handler.
