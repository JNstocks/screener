import io, json, re, time
from pathlib import Path
import pandas as pd
import requests

ORDNER = Path(__file__).parent
KOPF = {"User-Agent": "ScreenerBot/1.0 (privates Projekt; kontakt@example.com)"}
API = "https://en.wikipedia.org/w/api.php"

INDIZES = [
    ("S&P 500", "List of S&P 500 companies", "", "USA", False),
    ("Nasdaq-100", "Nasdaq-100", "", "USA", False),
    ("S&P/TSX Composite", "S&P/TSX Composite Index", ".TO", "Kanada", False),
    ("Nikkei 225", "Nikkei 225", ".T", "Japan", True),
    ("Hang Seng", "Hang Seng Index", ".HK", "Hongkong", True),
    ("FTSE 100", "FTSE 100 Index", ".L", "Grossbritannien", False),
    ("DAX", "DAX", ".DE", "Deutschland", False),
    ("MDAX", "MDAX", ".DE", "Deutschland", False),
    ("CAC 40", "CAC 40", ".PA", "Frankreich", False),
    ("EURO STOXX 50", "EURO STOXX 50", "", "Europa", False),
    ("SMI", "Swiss Market Index", ".SW", "Schweiz", False),
    ("AEX", "AEX index", ".AS", "Niederlande", False),
    ("BEL 20", "BEL20", ".BR", "Belgien", False),
    ("IBEX 35", "IBEX 35", ".MC", "Spanien", False),
    ("FTSE MIB", "FTSE MIB", ".MI", "Italien", False),
    ("OMX Stockholm 30", "OMX Stockholm 30", ".ST", "Schweden", False),
    ("OBX", "OBX Index", ".OL", "Norwegen", False),
    ("S&P/ASX 200", "S&P/ASX 200", ".AX", "Australien", False),
    ("Ibovespa", "List of companies listed on B3", ".SA", "Brasilien", False),
    ("Straits Times", "Straits Times Index", ".SI", "Singapur", False),
    ("NIFTY 50", "NIFTY 50", ".NS", "Indien", False),
    ("KOSPI", "KOSPI", ".KS", "Suedkorea", True),
]

T_SP = ["symbol", "ticker", "code", "ticker symbol", "epic", "trading symbol"]
N_SP = ["company", "security", "name", "constituent", "issuer", "company name"]


def seite_holen(titel):
    for versuch in range(4):
        try:
            r = requests.get(API, headers=KOPF, timeout=30, params={
                "action": "parse", "page": titel, "prop": "text",
                "formatversion": "2", "format": "json"})
            if r.status_code == 200:
                d = r.json()
                if "parse" in d:
                    return d["parse"]["text"]
                return None
        except Exception:
            pass
        time.sleep(2 * (versuch + 1))
    return None


def spalte(tab, kand):
    for s in tab.columns:
        k = str(s).strip().lower()
        if any(k == c or k.startswith(c) for c in kand):
            return s
    return None


def saeubern(wert, suffix):
    t = re.sub(r"\[.*?\]|\(.*?\)", "", str(wert).strip().upper()).strip()
    if not t or t in {"NAN", "-"}:
        return None
    if suffix in {".HK", ".T", ".KS", ".TW"}:
        z = re.sub(r"\D", "", t)
        if not z:
            return None
        return f"{int(z):04d}.HK" if suffix == ".HK" else f"{z}{suffix}"
    t = re.sub(r"[^A-Z0-9.\-]", "", t.split(":")[-1])
    if not t or len(t) > 12:
        return None
    if suffix:
        t = t.split(".")[0] + suffix
    else:
        t = t.replace(".", "-")
    return t


def laden(name, titel, suffix, land, codes):
    html = seite_holen(titel)
    if html is None:
        print(f"  {name:22s} nicht abrufbar")
        return pd.DataFrame()

    beste = []
    try:
        tabellen = pd.read_html(io.StringIO(html))
    except Exception:
        tabellen = []

    for tab in tabellen:
        if tab.shape[0] < 15:
            continue
        tab.columns = [str(s) for s in tab.columns]
        st = spalte(tab, T_SP)
        if st is None:
            continue
        sn = spalte(tab, N_SP)
        eintraege = []
        for _, z in tab.iterrows():
            tk = saeubern(z[st], suffix)
            if tk:
                nm = re.sub(r"\[.*?\]", "", str(z[sn])).strip() if sn else tk
                eintraege.append({"ticker": tk, "name": nm or tk, "land": land})
        if len(eintraege) > len(beste):
            beste = eintraege

    if not beste and codes:
        gefunden = set(re.findall(r">\s*(\d{4})\s*<", html))
        beste = [{"ticker": saeubern(c, suffix), "name": c, "land": land}
                 for c in sorted(gefunden)]

    print(f"  {name:22s} {len(beste):4d} Titel")
    return pd.DataFrame(beste)


def main():
    print("Lade Index-Mitgliederlisten\n")
    teile = []
    for eintrag in INDIZES:
        teile.append(laden(*eintrag))
        time.sleep(1.0)
    voll = [t for t in teile if len(t)]
    if not voll:
        print("\nNichts geladen.")
        return
    alle = pd.concat(voll, ignore_index=True).dropna(subset=["ticker"])
    alle = alle.drop_duplicates(subset="ticker").sort_values("ticker")
    alle.to_csv(ORDNER / "universum.csv", index=False)
    print(f"\nFertig: {len(alle)} eindeutige Titel in universum.csv")
    print("Naechster Schritt:  py daten_holen.py")


if __name__ == "__main__":
    main()