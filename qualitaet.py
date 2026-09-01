"""
Qualitaetsfaktoren eines Unternehmens.

Wird erst beim Oeffnen eines Titels aufgerufen und einen Tag zwischengespeichert.
Alle Werte stammen aus den berichteten Abschluessen, nur KGV und die beiden
Wachstumsschaetzungen sind Markt- bzw. Analystenwerte.

Jeder Faktor gibt zurueck:
    wert      Zahl oder None
    text      Anzeigetext
    ampel     "gruen" | "gelb" | "rot" | "grau"   (grau = keine Daten)
"""

import pandas as pd
import yfinance as yf

import sec_daten


def _zahl(wert):
    try:
        if wert is None or pd.isna(wert):
            return None
        return float(wert)
    except (TypeError, ValueError):
        return None


def _zeile(df, *namen):
    """Sucht eine Kennzahlenzeile im Abschluss, mehrere Schreibweisen erlaubt."""
    if df is None or df.empty:
        return None
    for name in namen:
        for index in df.index:
            if str(index).strip().lower() == name.lower():
                return df.loc[index]
    return None


def _ampel(wert, gut, mittel, hoch_ist_gut=True):
    if wert is None:
        return "grau"
    if hoch_ist_gut:
        return "gruen" if wert >= gut else "gelb" if wert >= mittel else "rot"
    return "gruen" if wert <= gut else "gelb" if wert <= mittel else "rot"


def faktoren(ticker: str) -> dict:
    aktie = yf.Ticker(ticker)
    try:
        info = aktie.info or {}
    except Exception:
        info = {}
    try:
        guv = aktie.income_stmt
        bilanz = aktie.balance_sheet
        cashflow = aktie.cashflow
    except Exception:
        guv = bilanz = cashflow = pd.DataFrame()

    ergebnis = {}

    # --- Bewertung ---------------------------------------------------------
    kgv = _zahl(info.get("trailingPE"))
    ergebnis["KGV"] = {
        "wert": kgv,
        "text": f"{kgv:.1f}" if kgv else "keine Angabe",
        "ampel": _ampel(kgv, 20, 30, hoch_ist_gut=False) if kgv and kgv > 0 else "grau",
        "hinweis": "Kurs geteilt durch Jahresgewinn je Aktie. Unter 20 gilt als günstig.",
    }

    # --- Schaetzungen (oft lueckenhaft, dann grau) -------------------------
    for schluessel, feld, grenze, titel, erklaerung in [
        ("Umsatzwachstum erwartet", "revenueGrowth", 10,
         "Umsatzwachstum erwartet", "Erwartetes Umsatzwachstum gegenüber Vorjahr."),
        ("Gewinnwachstum erwartet", "earningsGrowth", 15,
         "Gewinnwachstum erwartet", "Erwartetes Wachstum des Gewinns je Aktie."),
    ]:
        roh = _zahl(info.get(feld))
        wert = roh * 100 if roh is not None else None
        ergebnis[titel] = {
            "wert": wert,
            "text": f"{wert:+.1f} %" if wert is not None else "keine Angabe",
            "ampel": _ampel(wert, grenze, 0) if wert is not None else "grau",
            "hinweis": erklaerung,
        }

    # --- Realisiertes Wachstum aus den Abschluessen ------------------------
    umsatz = _zeile(guv, "Total Revenue", "Operating Revenue")
    gewinn = _zeile(guv, "Net Income", "Net Income Common Stockholders")

    def cagr(reihe):
        if reihe is None:
            return None, None
        werte = [_zahl(v) for v in reihe.values]
        werte = [v for v in werte if v is not None]
        if len(werte) < 3:
            return None, None
        neu, alt = werte[0], werte[-1]          # yfinance: neuestes Jahr zuerst
        jahre = len(werte) - 1
        if alt is None or alt <= 0 or neu <= 0:
            return None, None
        wachstum = ((neu / alt) ** (1 / jahre) - 1) * 100
        gestiegen = sum(1 for a, b in zip(werte, werte[1:]) if a > b)
        return wachstum, f"{gestiegen} von {jahre}"

    umsatz_cagr, _ = cagr(umsatz)
    gewinn_cagr, gewinn_serie = cagr(gewinn)

    ergebnis["Umsatzwachstum berichtet"] = {
        "wert": umsatz_cagr,
        "text": f"{umsatz_cagr:+.1f} % p.a." if umsatz_cagr is not None else "keine Angabe",
        "ampel": _ampel(umsatz_cagr, 5, 0),
        "hinweis": "Tatsächliches Umsatzwachstum pro Jahr laut Geschäftsberichten.",
    }
    ergebnis["Gewinnwachstum berichtet"] = {
        "wert": gewinn_cagr,
        "text": (f"{gewinn_cagr:+.1f} % p.a. · Jahre gestiegen: {gewinn_serie}"
                 if gewinn_cagr is not None else "keine Angabe"),
        "ampel": _ampel(gewinn_cagr, 8, 0),
        "hinweis": "Tatsächliches Gewinnwachstum pro Jahr, plus Beständigkeit.",
    }

    # --- Verschuldung und Zinslast ----------------------------------------
    ebit = _zeile(guv, "EBIT", "Operating Income")
    zinsen = _zeile(guv, "Interest Expense", "Interest Expense Non Operating")
    deckung = None
    if ebit is not None and zinsen is not None:
        e, z = _zahl(ebit.iloc[0]), _zahl(zinsen.iloc[0])
        if e is not None and z:
            deckung = e / abs(z)
    ergebnis["Zinsdeckung"] = {
        "wert": deckung,
        "text": f"{deckung:.1f}×" if deckung is not None else "keine Angabe",
        "ampel": _ampel(deckung, 4, 2),
        "hinweis": "Betriebsgewinn im Verhältnis zum Zinsaufwand. Unter 3 wird es eng.",
    }

    ebitda = _zeile(guv, "EBITDA", "Normalized EBITDA")
    schulden = _zeile(bilanz, "Total Debt")
    liquide = _zeile(bilanz, "Cash And Cash Equivalents",
                     "Cash Cash Equivalents And Short Term Investments")
    verhaeltnis = None
    if ebitda is not None and schulden is not None:
        eb = _zahl(ebitda.iloc[0])
        sch = _zahl(schulden.iloc[0]) or 0
        bar = _zahl(liquide.iloc[0]) if liquide is not None else 0
        if eb and eb > 0:
            verhaeltnis = (sch - (bar or 0)) / eb
    ergebnis["Netto-Schulden / EBITDA"] = {
        "wert": verhaeltnis,
        "text": f"{verhaeltnis:.1f}×" if verhaeltnis is not None else "keine Angabe",
        "ampel": _ampel(verhaeltnis, 2, 4, hoch_ist_gut=False),
        "hinweis": "Wie viele Jahresgewinne nötig wären, um die Schulden zu tilgen.",
    }

    # --- Freier Cashflow ---------------------------------------------------
    fcf = _zeile(cashflow, "Free Cash Flow")
    anteil = None
    jahre_text = "keine Angabe"
    if fcf is not None:
        werte = [_zahl(v) for v in fcf.values]
        werte = [v for v in werte if v is not None]
        if werte:
            positiv = sum(1 for v in werte if v > 0)
            anteil = positiv / len(werte) * 100
            jahre_text = f"{positiv} von {len(werte)} Jahren positiv"
    ergebnis["Freier Cashflow"] = {
        "wert": anteil,
        "text": jahre_text,
        "ampel": _ampel(anteil, 99, 60),
        "hinweis": "Tatsächlich erwirtschaftetes Geld — schwerer zu beschönigen als der Gewinn.",
    }

    # --- Marge und Kapitalrendite -----------------------------------------
    marge = _zahl(info.get("operatingMargins"))
    marge = marge * 100 if marge is not None else None
    ergebnis["Operative Marge"] = {
        "wert": marge,
        "text": f"{marge:.1f} %" if marge is not None else "keine Angabe",
        "ampel": _ampel(marge, 12, 5),
        "hinweis": "Anteil des Umsatzes, der als Betriebsgewinn übrig bleibt.",
    }

    rendite = _zahl(info.get("returnOnEquity"))
    rendite = rendite * 100 if rendite is not None else None
    ergebnis["Eigenkapitalrendite"] = {
        "wert": rendite,
        "text": f"{rendite:.1f} %" if rendite is not None else "keine Angabe",
        "ampel": _ampel(rendite, 15, 8),
        "hinweis": "Verzinsung des eingesetzten Eigenkapitals. Dauerhaft über 15 % ist stark.",
    }

    # --- Verwaesserung -----------------------------------------------------
    aktien = _zeile(bilanz, "Ordinary Shares Number", "Share Issued")
    veraenderung = None
    if aktien is not None:
        werte = [_zahl(v) for v in aktien.values]
        werte = [v for v in werte if v]
        if len(werte) >= 2 and werte[-1]:
            veraenderung = (werte[0] / werte[-1] - 1) * 100
    ergebnis["Aktienanzahl"] = {
        "wert": veraenderung,
        "text": (f"{veraenderung:+.1f} % über den Zeitraum"
                 if veraenderung is not None else "keine Angabe"),
        "ampel": _ampel(veraenderung, 0, 10, hoch_ist_gut=False),
        "hinweis": "Steigt sie deutlich, wurden Altaktionäre durch neue Aktien verwässert.",
    }

    try:
        ergebnis = sec_daten.ergaenzen(ticker, ergebnis, _ampel)
    except Exception:
        pass

    return ergebnis


def bilanz_zaehlen(alle: dict) -> tuple:
    """(erfuellt, bewertbar) - grau zaehlt nicht mit."""
    bewertbar = [f for f in alle.values() if f["ampel"] != "grau"]
    erfuellt = [f for f in bewertbar if f["ampel"] == "gruen"]
    return len(erfuellt), len(bewertbar)
