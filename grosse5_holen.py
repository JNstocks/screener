"""Berechnet Die Grossen 5 fuer alle Titel aus kennzahlen.csv."""

import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

import sec_daten

DATEN = Path(__file__).parent / "daten"
ABLAGE = DATEN / "grosse5.csv"
STEUERSATZ = 0.25
MAX_JAHRE = 11

SEC_BEGRIFFE = {
    "umsatz": ["RevenueFromContractWithCustomerExcludingAssessedTax",
               "Revenues", "SalesRevenueNet"],
    "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "eigenkapital": ["StockholdersEquity"],
    "ebit": ["OperatingIncomeLoss"],
    "schulden": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "op_cashflow": ["NetCashProvidedByUsedInOperatingActivities"],
    "investitionen": ["PaymentsToAcquirePropertyPlantAndEquipment"],
}


def cagr(reihe):
    werte = [w for _, w in reihe if w is not None]
    if len(werte) < 3:
        return None
    neu, alt = werte[0], werte[-1]
    if alt is None or alt <= 0 or neu <= 0:
        return None
    return ((neu / alt) ** (1 / (len(werte) - 1)) - 1) * 100


def sec_reihen(ticker):
    cik = sec_daten._cik_verzeichnis().get(ticker.upper())
    if not cik:
        return {}
    try:
        antwort = requests.get(sec_daten.BASIS.format(int(cik)),
                               headers=sec_daten.KOPF, timeout=30)
        if antwort.status_code != 200:
            return {}
        fakten = antwort.json().get("facts", {})
    except Exception:
        return {}
    reihen = {}
    for name, begriffe in SEC_BEGRIFFE.items():
        for raum in ("us-gaap", "dei"):
            gefunden = None
            for begriff in begriffe:
                eintrag = fakten.get(raum, {}).get(begriff)
                if not eintrag:
                    continue
                for einheit in eintrag.get("units", {}).values():
                    jahre = {}
                    for posten in einheit:
                        if posten.get("form") != "10-K" or posten.get("fp") != "FY":
                            continue
                        if posten.get("fy") and posten.get("val") is not None:
                            jahre[posten["fy"]] = posten["val"]
                    if len(jahre) >= 3:
                        gefunden = sorted(jahre.items(), key=lambda p: -p[0])[:MAX_JAHRE]
                        break
                if gefunden:
                    break
            if gefunden:
                reihen[name] = gefunden
                break
    return reihen


def yahoo_reihen(ticker):
    def zeile(df, *namen):
        if df is None or df.empty:
            return None
        for name in namen:
            for index in df.index:
                if str(index).strip().lower() == name.lower():
                    return [(s.year, v) for s, v in df.loc[index].items() if pd.notna(v)]
        return None

    try:
        aktie = yf.Ticker(ticker)
        guv, bilanz, cf = aktie.income_stmt, aktie.balance_sheet, aktie.cashflow
    except Exception:
        return {}

    reihen = {}
    for schluessel, quelle, namen in [
        ("umsatz", guv, ("Total Revenue", "Operating Revenue")),
        ("eps", guv, ("Diluted EPS", "Basic EPS")),
        ("ebit", guv, ("EBIT", "Operating Income")),
        ("eigenkapital", bilanz, ("Stockholders Equity", "Total Equity Gross Minority Interest")),
        ("schulden", bilanz, ("Long Term Debt", "Total Debt")),
        ("fcf", cf, ("Free Cash Flow",)),
    ]:
        werte = zeile(quelle, *namen)
        if werte:
            reihen[schluessel] = werte
    return reihen


def auswerten(ticker):
    reihen, quelle = {}, ""
    if sec_daten.ist_us(ticker):
        reihen = sec_reihen(ticker)
        quelle = "SEC" if reihen else ""
    if not reihen:
        reihen = yahoo_reihen(ticker)
        quelle = "Yahoo" if reihen else ""
    if not reihen:
        return {"ticker": ticker, "quelle": "", "jahre": 0}

    fcf = reihen.get("fcf")
    if fcf is None and "op_cashflow" in reihen:
        capex = dict(reihen.get("investitionen", []))
        fcf = [(j, w - capex.get(j, 0)) for j, w in reihen["op_cashflow"]]

    roic_werte = []
    schulden = dict(reihen.get("schulden", []))
    kapital_je_jahr = dict(reihen.get("eigenkapital", []))
    for jahr, ebit in reihen.get("ebit", []):
        kapital = kapital_je_jahr.get(jahr)
        if not kapital or kapital <= 0:
            continue
        basis = kapital + (schulden.get(jahr) or 0)
        if basis > 0:
            roic_werte.append(ebit * (1 - STEUERSATZ) / basis * 100)

    def gerundet(reihe):
        wert = cagr(reihe or [])
        return round(wert, 1) if wert is not None else None

    return {
        "ticker": ticker,
        "quelle": quelle,
        "jahre": max((len(v) for v in reihen.values()), default=0),
        "roic": round(sum(roic_werte) / len(roic_werte), 1) if roic_werte else None,
        "umsatz_cagr": gerundet(reihen.get("umsatz")),
        "eps_cagr": gerundet(reihen.get("eps")),
        "ek_cagr": gerundet(reihen.get("eigenkapital")),
        "fcf_cagr": gerundet(fcf),
    }


def main():
    tabelle = pd.read_csv(DATEN / "kennzahlen.csv")
    bekannt = pd.read_csv(ABLAGE) if ABLAGE.exists() else pd.DataFrame(columns=["ticker"])
    offen = [t for t in tabelle["ticker"] if t not in set(bekannt["ticker"])]
    print(f"{len(bekannt)} bereits berechnet, {len(offen)} offen\n")

    neu = []
    for nr, ticker in enumerate(offen, start=1):
        neu.append(auswerten(ticker))
        if nr % 20 == 0 or nr == len(offen):
            pd.concat([bekannt, pd.DataFrame(neu)]).to_csv(ABLAGE, index=False)
            print(f"  {nr}/{len(offen)}  mit Daten: {sum(1 for e in neu if e.get('quelle'))}")
        time.sleep(0.3)

    alle = pd.concat([bekannt, pd.DataFrame(neu)]).drop_duplicates("ticker", keep="last")
    alle.to_csv(ABLAGE, index=False)

    for name in ["roic", "umsatz_cagr", "eps_cagr", "ek_cagr", "fcf_cagr"]:
        werte = pd.to_numeric(alle[name], errors="coerce")
        print(f"  {name:12s} vorhanden: {werte.notna().sum():4d}   "
              f"erfuellt: {(werte >= 10).sum():4d}")
    print(f"\nFertig: {len(alle)} Titel in grosse5.csv")


if __name__ == "__main__":
    main()