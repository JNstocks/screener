from pathlib import Path

z = 0

q = Path("qualitaet.py"); t = q.read_text(encoding="utf-8")
if "sec_daten" not in t:
    t = t.replace("import pandas as pd\nimport yfinance as yf",
                  "import pandas as pd\nimport yfinance as yf\n\nimport sec_daten", 1)
    t = t.replace("""    return ergebnis


def bilanz_zaehlen""",
                  """    try:
        ergebnis = sec_daten.ergaenzen(ticker, ergebnis, _ampel)
    except Exception:
        pass

    return ergebnis


def bilanz_zaehlen""", 1)
    q.write_text(t, encoding="utf-8"); z += 1

a = Path("app.py"); t = a.read_text(encoding="utf-8")

if "def lade_termine" not in t:
    t = t.replace("""@st.cache_data(ttl=86400, show_spinner=False)
def lade_qualitaet""",
                  """@st.cache_data(ttl=86400, show_spinner=False)
def lade_termine(ticker: str) -> dict:
    import yfinance as yf
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=12)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    heute = pd.Timestamp.now(tz=df.index.tz)
    return {"naechster": df[df.index > heute].index.min(),
            "letzter": df[df.index <= heute].index.max()}


@st.cache_data(ttl=86400, show_spinner=False)
def lade_qualitaet""", 1)
    z += 1

alt = '''        st.subheader("Qualitätsfaktoren")'''
neu = '''        termine = lade_termine(ticker)
        if termine:
            sp1, sp2 = st.columns(2)
            letzter = termine.get("letzter")
            kommend = termine.get("naechster")
            sp1.metric("Letzte Zahlen",
                       letzter.strftime("%d.%m.%Y") if letzter is not None else "—")
            sp2.metric("Nächste Zahlen",
                       kommend.strftime("%d.%m.%Y") if kommend is not None else "—")

        suche = f"{zeile['name']} investor relations".replace(" ", "+")
        quellen = f"[Investor Relations](https://www.google.com/search?q={suche})"
        if "." not in ticker:
            quellen += (f" &nbsp;·&nbsp; [SEC-Einreichungen]"
                        f"(https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                        f"&ticker={ticker}&type=10-K&dateb=&owner=include&count=20)")
        st.markdown(quellen)

        st.subheader("Qualitätsfaktoren")'''
if alt in t and "Investor Relations" not in t:
    t = t.replace(alt, neu, 1); z += 1

a.write_text(t, encoding="utf-8")
print(f"{z} Stellen geändert.")