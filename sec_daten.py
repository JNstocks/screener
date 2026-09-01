"""Fundamentaldaten von der SEC (EDGAR), fuer US-Titel."""

import json
from pathlib import Path

import requests

DATEN = Path(__file__).parent / "daten"
KOPF = {"User-Agent": "Julas Screener (privat) kontakt@example.com"}
BASIS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{:010d}.json"
VERZEICHNIS = "https://www.sec.gov/files/company_tickers.json"

BEGRIFFE = {
    "umsatz": ["RevenueFromContractWithCustomerExcludingAssessedTax",
               "Revenues", "SalesRevenueNet"],
    "gewinn": ["NetIncomeLoss"],
    "ebit": ["OperatingIncomeLoss"],
    "zinsen": ["InterestExpense", "InterestExpenseNonoperating"],
    "eigenkapital": ["StockholdersEquity"],
    "op_cashflow": ["NetCashProvidedByUsedInOperatingActivities"],
    "investitionen": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "aktien": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"],
}


def ist_us(ticker):
    return "." not in ticker


def _cik_verzeichnis():
    ablage = DATEN / "cik.json"
    if ablage.exists():
        try:
            return json.loads(ablage.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        antwort = requests.get(VERZEICHNIS, headers=KOPF, timeout=30)
        antwort.raise_for_status()
        tabelle = {e["ticker"].upper(): e["cik_str"] for e in antwort.json().values()}
        DATEN.mkdir(exist_ok=True)
        ablage.write_text(json.dumps(tabelle), encoding="utf-8")
        return tabelle
    except Exception:
        return {}


def _jahreswerte(fakten, begriffe):
    for raum in ("us-gaap", "dei"):
        for begriff in begriffe:
            eintrag = fakten.get(raum, {}).get(begriff)
            if not eintrag:
                continue
            for einheit in eintrag.get("units", {}).values():
                jahre = {}
                for posten in einheit:
                    if posten.get("form") != "10-K" or posten.get("fp") != "FY":
                        continue
                    jahr = posten.get("fy")
                    if jahr and posten.get("val") is not None:
                        jahre[jahr] = posten["val"]
                if len(jahre) >= 2:
                    return sorted(jahre.items(), key=lambda p: -p[0])[:6]
    return []


def kennzahlen(ticker):
    if not ist_us(ticker):
        return {}
    cik = _cik_verzeichnis().get(ticker.upper())
    if not cik:
        return {}
    try:
        antwort = requests.get(BASIS.format(int(cik)), headers=KOPF, timeout=30)
        if antwort.status_code != 200:
            return {}
        fakten = antwort.json().get("facts", {})
    except Exception:
        return {}
    return {name: _jahreswerte(fakten, begriffe) for name, begriffe in BEGRIFFE.items()}


def _cagr(reihe):
    if len(reihe) < 3:
        return None, None
    neu, alt = reihe[0][1], reihe[-1][1]
    jahre = len(reihe) - 1
    if not alt or alt <= 0 or neu <= 0:
        return None, None
    werte = [w for _, w in reihe]
    gestiegen = sum(1 for a, b in zip(werte, werte[1:]) if a > b)
    return ((neu / alt) ** (1 / jahre) - 1) * 100, f"{gestiegen} von {jahre}"


def ergaenzen(ticker, ergebnis, ampel, quelle="SEC"):
    if not ist_us(ticker):
        return ergebnis
    if not [k for k, v in ergebnis.items() if v["ampel"] == "grau"]:
        return ergebnis
    roh = kennzahlen(ticker)
    if not roh:
        return ergebnis

    def setzen(name, wert, text, farbe):
        if name in ergebnis and ergebnis[name]["ampel"] == "grau" and wert is not None:
            ergebnis[name].update({"wert": wert, "text": f"{text}  ({quelle})",
                                   "ampel": farbe})

    umsatz_cagr, _ = _cagr(roh.get("umsatz", []))
    if umsatz_cagr is not None:
        setzen("Umsatzwachstum berichtet", umsatz_cagr,
               f"{umsatz_cagr:+.1f} % p.a.", ampel(umsatz_cagr, 5, 0))

    gewinn_cagr, bestand = _cagr(roh.get("gewinn", []))
    if gewinn_cagr is not None:
        setzen("Gewinnwachstum berichtet", gewinn_cagr,
               f"{gewinn_cagr:+.1f} % p.a. · Jahre gestiegen: {bestand}",
               ampel(gewinn_cagr, 8, 0))

    ebit = roh.get("ebit", [])
    zinsen = roh.get("zinsen", [])
    if ebit and zinsen and zinsen[0][1]:
        deckung = ebit[0][1] / abs(zinsen[0][1])
        setzen("Zinsdeckung", deckung, f"{deckung:.1f}x", ampel(deckung, 4, 2))

    umsatz = roh.get("umsatz", [])
    ek = roh.get("eigenkapital", [])
    if ebit and umsatz and umsatz[0][1]:
        marge = ebit[0][1] / umsatz[0][1] * 100
        setzen("Operative Marge", marge, f"{marge:.1f} %", ampel(marge, 12, 5))
    if roh.get("gewinn") and ek and ek[0][1]:
        rendite = roh["gewinn"][0][1] / ek[0][1] * 100
        setzen("Eigenkapitalrendite", rendite, f"{rendite:.1f} %", ampel(rendite, 15, 8))

    ocf = roh.get("op_cashflow", [])
    capex = dict(roh.get("investitionen", []))
    if ocf:
        frei = [w - capex.get(j, 0) for j, w in ocf]
        positiv = sum(1 for w in frei if w > 0)
        anteil = positiv / len(frei) * 100
        setzen("Freier Cashflow", anteil,
               f"{positiv} von {len(frei)} Jahren positiv", ampel(anteil, 99, 60))

    aktien = roh.get("aktien", [])
    if len(aktien) >= 2 and aktien[-1][1]:
        wandel = (aktien[0][1] / aktien[-1][1] - 1) * 100
        setzen("Aktienanzahl", wandel, f"{wandel:+.1f} % über den Zeitraum",
               ampel(wandel, 0, 10, False))

    return ergebnis