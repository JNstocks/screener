"""Holt Sektor, Waehrung und Marktkapitalisierung nach - schonend und wiederholbar."""
import time
from pathlib import Path
import pandas as pd
import yfinance as yf

DATEN = Path(__file__).parent / "daten"
CACHE = DATEN / "stammdaten.csv"

tab = pd.read_csv(DATEN / "kennzahlen.csv")
bekannt = pd.read_csv(CACHE) if CACHE.exists() else pd.DataFrame(
    columns=["ticker", "sektor", "waehrung", "marktkap"])
offen = [t for t in tab["ticker"] if t not in set(bekannt["ticker"])]
print(f"{len(bekannt)} bereits bekannt, {len(offen)} offen\n")

neu = []
for nr, sym in enumerate(offen, 1):
    sektor, waehrung, kap = "", "", 0
    try:
        aktie = yf.Ticker(sym)
        fi = aktie.fast_info
        waehrung = fi.get("currency") or ""
        kap = fi.get("market_cap") or 0
    except Exception:
        pass
    for versuch in range(2):
        try:
            info = aktie.get_info() or {}
            sektor = info.get("sector") or ""
            waehrung = waehrung or info.get("currency") or ""
            kap = kap or info.get("marketCap") or 0
            break
        except Exception:
            time.sleep(3)
    neu.append({"ticker": sym, "sektor": sektor, "waehrung": waehrung, "marktkap": kap})
    if nr % 20 == 0 or nr == len(offen):
        pd.concat([bekannt, pd.DataFrame(neu)]).to_csv(CACHE, index=False)
        treffer = sum(1 for e in neu if e["sektor"])
        print(f"  {nr}/{len(offen)}  mit Sektor: {treffer}")
    time.sleep(0.6)

alle = pd.concat([bekannt, pd.DataFrame(neu)]).drop_duplicates("ticker", keep="last")
alle.to_csv(CACHE, index=False)

tab = tab.drop(columns=["sektor", "waehrung"], errors="ignore").merge(
    alle[["ticker", "sektor", "waehrung", "marktkap"]], on="ticker", how="left")
tab["sektor"] = tab["sektor"].replace("", pd.NA).fillna("unbekannt")
tab["marktkap_mrd"] = (pd.to_numeric(tab["marktkap"], errors="coerce").fillna(0) / 1e9).round(1)
tab.drop(columns=["marktkap"]).to_csv(DATEN / "kennzahlen.csv", index=False)

print(f"\nFertig. Mit Sektor: {(tab['sektor'] != 'unbekannt').sum()} von {len(tab)}")