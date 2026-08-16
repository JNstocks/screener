# Aktien-Screener

Zweistufiges Werkzeug: Erst ein Kursfilter über ein weltweites Universum, dann
eine Einzelprüfung je Titel mit Qualitätsfaktoren und Nachrichten.

## Dateien

| Datei | Zweck |
|---|---|
| `universum_bauen.py` | Holt die Mitglieder von 24 Leitindizes und schreibt `universum.csv`. Einmal pro Woche genug. |
| `daten_holen.py` | Kurse, Vorfilter, Stammdaten. Läuft täglich. |
| `qualitaet.py` | Die zehn Qualitätsfaktoren der Detailseite. Wird beim Öffnen eines Titels aufgerufen. |
| `nachrichten.py` | Schlagzeilen und deren Einstufung. |
| `app.py` | Die Oberfläche. |

## Start

Im Ordner, in PowerShell, einzeln:

```
py -m pip install -r requirements.txt
py universum_bauen.py
py daten_holen.py
py -m streamlit run app.py
```

`universum_bauen.py` dauert 1–2 Minuten. `daten_holen.py` braucht beim ersten
Lauf 30–60 Minuten — es lädt fünf Jahre Historie für rund 2.000 Titel und
holt danach Stammdaten für die Treffer. Lass es einmal durchlaufen; danach
geht es schneller.

## Wie gefiltert wird

**Stufe 1, automatisch beim Datenlauf:**
- nur Mitglieder der hinterlegten Indizes
- mindestens 20 % unter dem 52-Wochen-Hoch (`MIN_ABSTAND_HOCH` in `daten_holen.py`)
- mindestens 2 Mrd. USD Marktkapitalisierung, also keine Small Caps
  (`MIN_MARKTKAP_USD`)

Titel ohne Angabe zur Marktkapitalisierung bleiben drin, statt still zu
verschwinden — sie fallen sonst besonders bei asiatischen Werten grundlos raus.

**Stufe 2, in der Oberfläche:** Regler von 20 bis 50 %, dazu Filter nach Land
und Sektor.

## Die Qualitätsfaktoren

Zehn Kacheln, jede grün, gelb, rot oder grau. **Grau heißt: keine Daten
vorhanden** — es wird nichts geschätzt.

| Faktor | Grün ab |
|---|---|
| KGV | unter 20 |
| Umsatzwachstum erwartet | über 10 % |
| Gewinnwachstum erwartet | über 15 % |
| Umsatzwachstum berichtet | über 5 % p. a. |
| Gewinnwachstum berichtet | über 8 % p. a. |
| Zinsdeckung | über 4× |
| Netto-Schulden / EBITDA | unter 2× |
| Freier Cashflow | in allen Jahren positiv |
| Operative Marge | über 12 % |
| Eigenkapitalrendite | über 15 % |
| Aktienanzahl | nicht gestiegen |

Der Balken oben zeigt „X von Y Kriterien erfüllt". Graue Kacheln zählen nicht
mit, damit fehlende Daten das Ergebnis nicht verzerren. Ab 80 % ist der Balken
grün, ab 50 % gelb.

Die Schwellen stehen in `qualitaet.py` in den `_ampel(...)`-Aufrufen und lassen
sich einzeln ändern.

## Nachrichten einstufen (optional)

Ohne Schlüssel erscheinen die Schlagzeilen ohne Farbe. Für die Einstufung:

1. Schlüssel auf console.anthropic.com erzeugen
2. Datei `.streamlit/secrets.toml` anlegen mit:

```
ANTHROPIC_API_KEY = "sk-ant-..."
```

Kosten liegen bei wenigen Cent im Monat, weil nur beim Öffnen eines Titels
bewertet wird und das Ergebnis sechs Stunden zwischengespeichert bleibt.
Die Datei ist über `.gitignore` vom Hochladen ausgenommen.

## Veröffentlichen

```
git init
git add .
git commit -m "Erste Version"
git branch -M main
git remote add origin https://github.com/DEINNAME/screener.git
git push -u origin main
```

Dann auf **share.streamlit.io** anmelden, Repository wählen, Hauptdatei
`app.py`, Deploy. Den Schlüssel dort unter *Settings → Secrets* eintragen.

Die Datei `.github/workflows/taeglich.yml` aktualisiert die Daten werktags
automatisch und schreibt sie ins Repository zurück.

## Zum Universum

MSCI und FTSE geben ihre Mitgliederlisten nicht frei heraus. `universum_bauen.py`
führt deshalb die öffentlich dokumentierten Leitindizes der jeweiligen Märkte
zusammen: S&P 500, Nasdaq-100, TSX, Nikkei 225, Hang Seng, FTSE 100, DAX, MDAX,
CAC 40, EURO STOXX 50, SMI, AEX, BEL 20, IBEX, FTSE MIB, OMX, OBX, ASX 200,
Ibovespa, Straits Times, NIFTY 50, KOSPI, KLCI, SET.

Das deckt MSCI World und MSCI Emerging Markets im Large- und Mid-Cap-Bereich
weitgehend ab und enthält Nikkei, Hang Seng und TSX vollständig. Es ist eine
Annäherung, keine exakte Nachbildung — das wäre ohne Lizenz nicht möglich.

Einzelne Indizes können ausfallen, wenn Wikipedia seine Tabellen umbaut. Das
Skript meldet das und macht mit den übrigen weiter.

## Wichtig

Der Screener zeigt Titel, die deutlich gefallen sind. Das trifft vorübergehend
abgestrafte Unternehmen genauso wie dauerhaft verfallende. Die Qualitätsfaktoren
sollen helfen, beides zu unterscheiden — sie sind keine Kaufempfehlung, und der
grüne Balken ist eine Feststellung über erfüllte Kriterien, keine Aufforderung.
