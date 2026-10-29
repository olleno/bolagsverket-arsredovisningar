# Bolagsverkets årsredovisningar som nyckeltal

Hämtar Bolagsverkets öppna årsredovisningsdata (värdefulla datamängder, `vardefulla-datamangder.bolagsverket.se`) och gör om varje årsredovisning till en rad med nyckeltal för innevarande och föregående år.

- `data/ar/<år>_<vecka>_<del>.csv.gz` – en fil per del av Bolagsverkets bulkfiler. En rad per årsredovisning: organisationsnummer, bokslutsdatum, inlämningsmånad och 23 nyckeltal (omsättning, resultat, tillgångar, eget kapital, skulder, anställda m.m.).
- `data/status_ab.csv.gz` – aktiebolagens status ur Bolagsverkets registerfil (registrerings- och avregistreringsdatum, orsak, pågående förfarande).
- `data/SAMMANFATTNING.txt` – vad som är hämtat.

Bara aktiebolag och andra juridiska personer. Rader med nummer som liknar personnummer tas aldrig med (`parse_ar.py`).

## Hur det körs
GitHub-flödet `hamta-arsredovisningar` körs varje tisdag natt och kan startas för hand. Det startas aldrig av en ändring i koden. Redan hämtade delar hoppas över.

Repot är publikt för att GitHubs maskiner är gratis för publika repon. Det privata repot `olleno/obduktion` hämtar datan härifrån.

Källa: Bolagsverket. Datan är öppen data enligt EU:s förordning om värdefulla datamängder.
