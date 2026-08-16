from pathlib import Path
a = Path("app.py"); t = a.read_text(encoding="utf-8"); z = 0

if 'st.title("Aktien-Screener")' in t:
    t = t.replace('st.title("Aktien-Screener")', 'st.title("Julas Aktien-Screener")', 1)
    t = t.replace('page_title="Aktien-Screener"', 'page_title="Julas Aktien-Screener"', 1); z += 1

if "def lade_historie_lang" not in t:
    t = t.replace('''@st.cache_data(ttl=86400, show_spinner=False)
def lade_qualitaet''', '''@st.cache_data(ttl=86400, show_spinner=False)
def lade_historie_lang(ticker: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(ticker, period="10y", interval="1d",
                     auto_adjust=True, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].dropna()


@st.cache_data(ttl=86400, show_spinner=False)
def lade_qualitaet''', 1); z += 1

alt = '''        st.subheader("Kursverlauf 5 Jahre")
        verlauf = lade_historie(ticker)
        figur = go.Figure()'''
neu = '''        st.subheader("Kursverlauf")
        ZR = {"1 J": 1, "2 J": 2, "3 J": 3, "4 J": 4, "5 J": 5, "YTD": "ytd", "10 J": 10}
        wahl = st.radio("Zeitraum", list(ZR), index=4,
                        horizontal=True, label_visibility="collapsed")
        spanne = ZR[wahl]
        if spanne == 10:
            with st.spinner("10 Jahre werden geladen ..."):
                verlauf = lade_historie_lang(ticker)
        else:
            verlauf = lade_historie(ticker)
        if spanne == "ytd":
            verlauf = verlauf[verlauf.index.year == verlauf.index[-1].year]
        elif isinstance(spanne, int) and spanne < 10:
            grenze = verlauf.index[-1] - pd.DateOffset(years=spanne)
            verlauf = verlauf[verlauf.index >= grenze]
        figur = go.Figure()'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

alt = '''        figur.update_xaxes(dtick="M12", tickformat="%Y", showgrid=False,'''
neu = '''        figur.update_xaxes(dtick="M12" if wahl not in {"1 J", "YTD"} else "M3",
                           tickformat="%Y" if wahl not in {"1 J", "YTD"} else "%b %y",
                           showgrid=False,'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

t = t.replace('st.info("Keine Meldungen gefunden.")',
              'st.info("Keine Unternehmensmeldungen der letzten 30 Tage.")', 1)
t = t.replace("return nw.bewerten(nw.schlagzeilen(ticker), firma)",
              "return nw.bewerten(nw.schlagzeilen(ticker, firma=firma), firma)", 1)
t = t.replace('zusatz = " · ".join(x for x in [meldung["quelle"],',
              'zusatz = " · ".join(x for x in [meldung.get("datum", ""), meldung["quelle"],', 1)
a.write_text(t, encoding="utf-8")
print(f"app.py: {z} Hauptstellen geändert.")