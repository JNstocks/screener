"""
Holt Kurse, wendet den Vorfilter an und ergaenzt Stammdaten.

Aufruf:
    py daten_holen.py

Ablauf:
  1. Kurse fuer das gesamte Universum (guenstig, in Paketen)
  2. Vorfilter: nur Titel ab MIN_ABSTAND_HOCH Prozent unter dem 52-Wochen-Hoch
  3. Nur fuer diese Treffer: Sektor, Land, Marktkapitalisierung (teuer, einzeln)
  4. Small Caps aussortieren

Ergebnis im Ordner daten/:
    kennzahlen.csv  eine Zeile je Treffer
    historie.csv    5 Jahre Kursverlauf je Treffer
    stand.txt       Zeitpunkt des Laufs
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

ORDNER = Path(__file__).parent
DATEN = ORDNER / "daten"

MIN_ABSTAND_HOCH = 20.0      # Prozent unter dem 52-Wochen-Hoch
MIN_MARKTKAP_USD = 2_000_000_000   # Grenze Mid/Small Cap
JAHR = 252
PAKET = 80                   # Ticker je Sammelabruf


# ------------------------------------------------------------ Hilfsfunktionen
def rsi(kurse: pd.Series, tage: int = 14) -> float:
    diff = kurse.diff()
    auf = diff.clip(lower=0).ewm(alpha=1 / tage, adjust=False).mean()
    ab = (-diff.clip(upper=0)).ewm(alpha=1 / tage, adjust=False).mean()
    if ab.iloc[-1] == 0:
        return 100.0
    return float(100 - 100 / (1 + auf.iloc[-1] / ab.iloc[-1]))


def wechselkurse(waehrungen: set) -> dict:
    """Umrechnungsfaktoren in USD."""
    kurse = {"USD": 1.0}
    for waehrung in waehrungen:
        if waehrung in kurse or not waehrung:
            continue
        try:
            df = yf.download(f"{waehrung}USD=X", period="5d",
                             progress=False, threads=False)
            kurse[waehrung] = float(df["Close"].dropna().iloc[-1])
        except Exception:
            kurse[waehrung] = None
    # GBp (Pence) und ZAc kommen als Untereinheit
    if kurse.get("GBP"):
        kurse["GBp"] = kurse["GBP"] / 100
    return kurse


def kennzahlen_aus_kurs(ticker: str, schluss: pd.Series) -> dict | None:
    schluss = schluss.dropna()
    if len(schluss) < 260:
        return None

    fenster = schluss.tail(JAHR)
    kurs = float(schluss.iloc[-1])
    tief, hoch = float(fenster.min()), float(fenster.max())
    if hoch <= tief or kurs <= 0:
        return None

    def wandel(tage: int):
        if len(schluss) <= tage:
            return None
        alt = float(schluss.iloc[-tage - 1])
        return round((kurs / alt - 1) * 100, 1) if alt else None

    jahresanfang = schluss[schluss.index.year == schluss.index[-1].year]
    ytd = round((kurs / float(jahresanfang.iloc[0]) - 1) * 100, 1) \
        if len(jahresanfang) > 1 else None

    return {
        "ticker": ticker,
        "kurs": round(kurs, 2),
        "tief52": round(tief, 2),
        "hoch52": round(hoch, 2),
        "vom_hoch_pct": round((kurs / hoch - 1) * 100, 1),
        "zum_tief_pct": round((kurs / tief - 1) * 100, 1),
        "aend_1m": wandel(21),
        "aend_ytd": ytd,
        "aend_3m": wandel(63),
        "aend_12m": wandel(JAHR),
        "rsi14": round(rsi(schluss), 1),
        "position_spanne": round((kurs - tief) / (hoch - tief) * 100),
    }


# ------------------------------------------------------------------- Ablauf 1
def kurse_laden(ticker_liste: list) -> tuple:
    """Sammelabruf in Paketen. Gibt (Kennzahlen, Verlaeufe) zurueck."""
    kennzahlen, verlaeufe = [], {}
    pakete = [ticker_liste[i:i + PAKET] for i in range(0, len(ticker_liste), PAKET)]

    for nr, paket in enumerate(pakete, start=1):
        print(f"  Paket {nr:3d}/{len(pakete)}  ({len(paket)} Titel)", end="", flush=True)
        try:
            roh = yf.download(paket, period="5y", interval="1d", auto_adjust=True,
                              progress=False, threads=True, group_by="ticker")
        except Exception as fehler:
            print(f"   Fehler: {type(fehler).__name__}")
            continue

        treffer = 0
        for ticker in paket:
            try:
                teil = roh[ticker] if isinstance(roh.columns, pd.MultiIndex) else roh
                schluss = teil["Close"].dropna()
            except Exception:
                continue
            if schluss.empty:
                continue
            werte = kennzahlen_aus_kurs(ticker, schluss)
            if werte:
                kennzahlen.append(werte)
                verlaeufe[ticker] = schluss
                treffer += 1
        print(f"   {treffer} mit Historie")

    return kennzahlen, verlaeufe


# ------------------------------------------------------------------- Ablauf 3
def stammdaten_laden(ticker_liste: list) -> pd.DataFrame:
    """Sektor, Land, Marktkapitalisierung - nur fuer die Treffer."""
    zeilen = []
    for nr, ticker in enumerate(ticker_liste, start=1):
        if nr % 25 == 0 or nr == 1:
            print(f"  {nr}/{len(ticker_liste)}", flush=True)
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}
        zeilen.append({
            "ticker": ticker,
            "sektor": info.get("sector") or "",
            "land_yf": info.get("country") or "",
            "waehrung": info.get("currency") or "",
            "marktkap": info.get("marketCap") or 0,
            "name_yf": info.get("shortName") or "",
        })
    return pd.DataFrame(zeilen)


def main() -> None:
    universum = pd.read_csv(ORDNER / "universum.csv")
    ticker_liste = universum["ticker"].dropna().unique().tolist()
    print(f"Universum: {len(ticker_liste)} Titel\n")

    print("1. Kurse laden")
    kennzahlen, verlaeufe = kurse_laden(ticker_liste)
    if not kennzahlen:
        print("\nKeine Kursdaten erhalten. Internetverbindung pruefen.")
        return
    tabelle = pd.DataFrame(kennzahlen)
    print(f"   {len(tabelle)} Titel mit ausreichender Historie\n")

    print(f"2. Vorfilter: mindestens {MIN_ABSTAND_HOCH:.0f} % unter dem Jahreshoch")
    tabelle = tabelle[tabelle["vom_hoch_pct"] <= -MIN_ABSTAND_HOCH]
    print(f"   {len(tabelle)} Titel bleiben uebrig\n")
    if tabelle.empty:
        print("Keine Treffer.")
        return

    print("3. Stammdaten fuer die Treffer laden")
    stamm = stammdaten_laden(tabelle["ticker"].tolist())
    tabelle = tabelle.merge(stamm, on="ticker", how="left")
    tabelle = tabelle.merge(universum[["ticker", "name", "land"]], on="ticker", how="left")
    tabelle["name"] = tabelle["name"].fillna(tabelle["name_yf"]).fillna(tabelle["ticker"])
    tabelle["land"] = tabelle["land_yf"].replace("", pd.NA).fillna(tabelle["land"])
    tabelle["sektor"] = tabelle["sektor"].replace("", "unbekannt").fillna("unbekannt")

    print("\n4. Small Caps aussortieren")
    fx = wechselkurse(set(tabelle["waehrung"].dropna()) - {""})
    tabelle["marktkap_usd"] = [
        (kap or 0) * (fx.get(wae) or 0)
        for kap, wae in zip(tabelle["marktkap"], tabelle["waehrung"])
    ]
    ohne_angabe = tabelle["marktkap_usd"] <= 0
    gross_genug = tabelle["marktkap_usd"] >= MIN_MARKTKAP_USD
    print(f"   {int(gross_genug.sum())} Large/Mid Cap, "
          f"{int((~gross_genug & ~ohne_angabe).sum())} Small Cap entfernt, "
          f"{int(ohne_angabe.sum())} ohne Angabe (bleiben drin)")
    tabelle = tabelle[gross_genug | ohne_angabe]

    tabelle["marktkap_mrd"] = (tabelle["marktkap_usd"] / 1e9).round(1)
    tabelle = tabelle.sort_values("vom_hoch_pct")

    spalten = ["ticker", "name", "land", "sektor", "kurs", "aend_1m", "aend_ytd",
               "vom_hoch_pct", "rsi14", "zum_tief_pct", "aend_3m", "aend_12m",
               "position_spanne", "tief52", "hoch52", "marktkap_mrd", "waehrung"]

    DATEN.mkdir(exist_ok=True)
    tabelle[spalten].to_csv(DATEN / "kennzahlen.csv", index=False)

    verlauf_zeilen = []
    for ticker in tabelle["ticker"]:
        reihe = verlaeufe.get(ticker)
        if reihe is None:
            continue
        verlauf_zeilen.append(pd.DataFrame({
            "ticker": ticker, "datum": reihe.index.date, "kurs": reihe.round(4).values}))
    pd.concat(verlauf_zeilen).to_csv(DATEN / "historie.csv", index=False)

    (DATEN / "stand.txt").write_text(
        datetime.now().strftime("%d.%m.%Y %H:%M"), encoding="utf-8")

    print(f"\nFertig: {len(tabelle)} Titel gespeichert.")
    print("Naechster Schritt:  py -m streamlit run app.py")


if __name__ == "__main__":
    main()
