# Fra ZIP til GitHub og Codex Cloud

## 1. Last opp til GitHub

1. Pakk ut `Finn-Flippemaskin-GitHub-Codex-Cloud.zip`.
2. Opprett et nytt, gjerne privat GitHub-repositorium.
3. Velg **Add file → Upload files**. Last opp innholdet i den utpakkede `Finn-Flippemaskin`-mappen, med undermappene. `app.py`, `pyproject.toml`, `config.json`, `scrape.json` og `AGENTS.md` skal ligge rett i repositoriets rot.
4. Ta også med punktfilene `.gitignore`, `.gitattributes`, `.python-version` og mappen `.streamlit`. På Mac vises skjulte filer med Cmd+Shift+punktum. Du kan bruke Git/GitHub Desktop dersom nettleseropplastingen utelater dem.
5. Lagre med **Commit changes**.

Last opp de utpakkede filene; et repo som bare inneholder ZIP-filen gir ikke Codex vanlig tilgang til kildekoden. `PAKKEINNHOLD.json` dokumenterer filene og kontrollsummene i leveransen.

## 2. Opprett skymiljøet

I Codex velger du **Work in → Cloud → Select environment → Create environment**. Velg GitHub-repositoriet, la Codex sette opp miljøet og publiser det når oppsettet er kontrollert. Menynavn kan variere med hvilken Codex Cloud-versjon du har.

Lim gjerne inn dette under oppsettet:

> Klargjør dette repositoriet for Codex Cloud. Les AGENTS.md og START_HER_GITHUB_OG_CODEX_CLOUD.md. Bruk Python 3.12 og kjør `bash scripts/setup.sh`. Kjør `.venv/bin/python -m pytest -q` og `.venv/bin/python -m ruff check finnflip app.py scripts tests`. Bruk `bash scripts/start_cloud.sh` hvis du skal starte Streamlit-forhåndsvisningen på port 8501. Behold gjeldende økonomiske regler og positivt filter. Programmet trenger ingen OpenAI API-nøkkel. Kontroller nettverk til FINN før du påstår at live-innhenting virker.

Oppsettet kan registreres som **Install script** med `bash scripts/setup.sh`. Oppstart av forhåndsvisningen er separat, siden serverprosessen fortsetter å kjøre.

## 3. Gi tilgang til FINN

Under skymiljøets internettilgang aktiverer du **Allow Codex to access internet**. Behold tilgang til pakkeregistre for installasjonen og legg til `www.finn.no` og `finn.no` som nødvendige domener for innhentingen. Lagre/publiser innstillingene og kontroller dem i en ny oppgave. Dette gir nettverkstilgang; FINN kan fortsatt avvise forespørsler fra skymiljøet. Skraperen stopper ved blokkering.

Start deretter en skyoppgave med denne teksten:

> Les AGENTS.md. Kjør `.venv/bin/python -m finnflip.cli morning` fra repositoriets rot og vent til kommandoen fullføres. Dersom den lykkes, les den nye `data/morning-report.json`. Vis bare `new_opportunities`, med lenke, kjøpspris, videresalgsanslag, kontantgevinst, økonomisk overskudd og kontrollpunkter. Hvis det ikke er treff, si at denne kjøringen ikke fant positive økonomiske anslag. Ikke endre kostnadsforutsetninger eller minimumskrav til referanser. Ikke kontakt selgere, kjøp eller send e-post. Ved nettverksfeil eller blokkering, oppgi feilen uten å presentere gamle data som nye.

Første innhenting oppretter `data/finnflip.sqlite`. Manglende variant eller sammenlignbare referanser kan gi null treff. `bash scripts/start_cloud.sh` starter oversikten; bruk eventuell portforhåndsvisning i skymiljøet.

## 4. Hva som følger med

Kildekode, gjeldende kostnads-/søkekonfigurasjon, låste avhengigheter, tester, syntetiske testdata, dokumentasjon, skjermbilder, oppsettscript og instruksjoner til Codex følger med. `config.json` har e-post i `DRY_RUN`, uten mottaker, SMTP-vert eller innloggingshemmeligheter.

Databasen, lokale vurderingsrapporter, varslingshistorikk, utkast, `.venv`, hurtigbuffer og lokale Codex-automasjoner følger ikke med. Eksisterende historikk blir bevart på den opprinnelige maskinen. Nye skyoppgaver starter derfor uten denne historikken; gamle tall i dokumentasjon/skjermbilder er historiske eksempler.

## 5. Morgenjobben må settes opp separat

GitHub-opplastingen flytter prosjektet. Den oppretter ikke automatisk daglig kjøring, varig lagring eller varsler i skyen. Planen kl. 08:00 som ble laget i den lokale Codex-chatten peker fremdeles på den opprinnelige maskinen.

Codex Cloud gir hver ny oppgave et separat arbeidsområde basert på det publiserte miljøet. En eksisterende skyoppgave beholder egne filer, men en annen ny oppgave arver ikke automatisk den løpende SQLite-databasen, referansehistorikken eller `morning-notifications.json`. Avklar og test hvordan samme oppgave eller en ekstern varig lagring skal brukes før gjentatte morgenkjøringer settes i drift. Databasen bør ikke committes til Git som erstatning for varig lagring.

Når dette virker, kan morgenplanen opprettes i skyen dersom kontoen/miljøet støtter den nødvendige kjøringen. Kontroller at den faktisk kjører uten den lokale maskinen, og at data og varsling bevares mellom kjøringene. Deretter kan den lokale planen erstattes. Denne pakken aktiverer eller stopper ingen planlagt jobb.

Offisiell veiledning, kontrollert 19. oktober 2026: [OpenAI Docs – skymiljøer](https://learn.chatgpt.com/docs/environments/cloud-environments), [planlagte oppgaver](https://learn.chatgpt.com/docs/automations?surface=app).
