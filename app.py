"""
Aktien-Screener: Übersicht und Einzelprüfung.

Starten:
    py -m streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import nachrichten as nw
import qualitaet as qa

ORDNER = Path(__file__).parent
DATEN = ORDNER / "daten"

st.set_page_config(page_title="Julas Aktien-Screener", page_icon="📉", layout="wide")

# --------------------------------------------------------------- Farbschemata
DUNKEL = {
    "hg": "#0E1419", "karte": "#161E26", "linie": "#2A3540", "text": "#E4EAF0",
    "leise": "#8A98A6", "gruen": "#3FB950", "gelb": "#D29922", "rot": "#E5534B",
    "grau": "#4A5560", "plotly": "plotly_dark", "chart_linie": "#5AA9E6",
    "chart_flaeche": "rgba(90,169,230,0.12)",
}
HELL = {
    "hg": "#FFFFFF", "karte": "#F5F7F9", "linie": "#D8DEE4", "text": "#131A21",
    "leise": "#5A6875", "gruen": "#1A7F37", "gelb": "#9A6700", "rot": "#C1352B",
    "grau": "#AEB8C2", "plotly": "plotly_white", "chart_linie": "#1F6FB2",
    "chart_flaeche": "rgba(31,111,178,0.10)",
}

def zugang_pruefen() -> bool:
    try:
        erwartet = st.secrets.get("PASSWORT")
    except Exception:
        erwartet = None
    if not erwartet:
        return True
    if st.session_state.get("zugang_ok"):
        return True
    st.markdown("### Julas Aktien-Screener")
    st.caption("Bitte Passwort eingeben.")
    eingabe = st.text_input("Passwort", type="password", label_visibility="collapsed")
    if eingabe:
        if eingabe == erwartet:
            st.session_state.zugang_ok = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")
    return False


if not zugang_pruefen():
    st.stop()


if "dunkel" not in st.session_state:
    st.session_state.dunkel = True
if "titel" not in st.session_state:
    st.session_state.titel = None

F = DUNKEL if st.session_state.dunkel else HELL

st.markdown(f"""
<style>
  .stApp, .main {{ background: {F['hg']}; }}
  .block-container {{ padding-top: 2rem; max-width: 1350px; }}
  h1, h2, h3, h4, p, span, label, li, div[data-testid="stMarkdownContainer"] {{
      color: {F['text']}; }}
  h1 {{ font-size: 2rem; letter-spacing: -.02em; margin-bottom: .2rem; }}
  .leise {{ color: {F['leise']}; font-size: .8rem;
            font-family: ui-monospace, monospace; letter-spacing: .04em; }}
  .kachel {{ background: {F['karte']}; border: 1px solid {F['linie']};
             border-left-width: 4px; border-radius: 3px; padding: .7rem .85rem;
             margin-bottom: .55rem; }}
  .kachel .bez {{ font-size: .68rem; letter-spacing: .11em; text-transform: uppercase;
                  color: {F['leise']}; }}
  .kachel .wert {{ font-size: 1.15rem; font-weight: 600; margin-top: .15rem;
                   font-family: ui-monospace, monospace; }}
  .kachel .hint {{ font-size: .72rem; color: {F['leise']}; margin-top: .3rem;
                   line-height: 1.35; }}
  .banner {{ border-radius: 3px; padding: .85rem 1.1rem; margin: .4rem 0 1.1rem;
             font-size: 1.02rem; font-weight: 600; }}
  .meldung {{ border-left: 3px solid {F['grau']}; padding: .1rem 0 .1rem .7rem;
              margin-bottom: .85rem; }}
  .meldung a {{ color: {F['text']}; text-decoration: none; font-weight: 500; }}
  .meldung a:hover {{ text-decoration: underline; }}
  .hinweis {{ color: {F['leise']}; font-size: .78rem; border-left: 2px solid {F['linie']};
              padding-left: .7rem; line-height: 1.5; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.4rem; color: {F['text']}; }}
</style>
""", unsafe_allow_html=True)

AMPEL = {"gruen": F["gruen"], "gelb": F["gelb"], "rot": F["rot"], "grau": F["grau"]}


# ------------------------------------------------------------------ Datenzugriff
GROSSE5 = {
    "roic": ("Kapitalrendite (ROIC)", "Betriebsgewinn nach Steuern auf das eingesetzte Kapital"),
    "umsatz_cagr": ("Umsatzwachstum", "Umsatz pro Jahr"),
    "eps_cagr": ("Gewinn je Aktie", "EPS pro Jahr"),
    "ek_cagr": ("Eigenkapitalwachstum", "Buchwert pro Jahr"),
    "fcf_cagr": ("Freier Cashflow", "FCF pro Jahr"),
}
HUERDE = 10.0


@st.cache_data
def lade_tabelle() -> pd.DataFrame:
    tabelle = pd.read_csv(DATEN / "kennzahlen.csv")
    pfad = DATEN / "grosse5.csv"
    if pfad.exists():
        fuenf = pd.read_csv(pfad)
        spalten = ["ticker", "quelle", "jahre"] + list(GROSSE5)
        vorhanden = [s for s in spalten if s in fuenf.columns]
        tabelle = tabelle.merge(fuenf[vorhanden], on="ticker", how="left")
    for schluessel in GROSSE5:
        if schluessel not in tabelle.columns:
            tabelle[schluessel] = pd.NA
        tabelle[schluessel] = pd.to_numeric(tabelle[schluessel], errors="coerce")
    return tabelle


@st.cache_data
def lade_historie(ticker: str) -> pd.Series:
    df = pd.read_csv(DATEN / "historie.csv", parse_dates=["datum"])
    teil = df[df["ticker"] == ticker]
    return teil.set_index("datum")["kurs"]


@st.cache_data(ttl=86400, show_spinner=False)
def lade_historie_lang(ticker: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(ticker, period="10y", interval="1d",
                     auto_adjust=True, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].dropna()


@st.cache_data(ttl=86400, show_spinner=False)
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
def lade_qualitaet(ticker: str) -> dict:
    return qa.faktoren(ticker)


@st.cache_data(ttl=21600, show_spinner=False)
def lade_nachrichten(ticker: str, firma: str) -> list:
    return nw.bewerten(nw.schlagzeilen(ticker, firma=firma), firma)


if not (DATEN / "kennzahlen.csv").exists():
    st.error("Noch keine Daten vorhanden. Bitte zuerst ausführen:")
    st.code("py universum_bauen.py\npy daten_holen.py", language="text")
    st.stop()

daten = lade_tabelle()
stand = (DATEN / "stand.txt").read_text(encoding="utf-8") \
    if (DATEN / "stand.txt").exists() else "unbekannt"


def kopfzeile(stufe: str) -> None:
    links, rechts = st.columns([5, 1])
    links.markdown(f"<div class='leise'>{stufe}</div>", unsafe_allow_html=True)
    rechts.toggle("Hell", value=not st.session_state.dunkel, key="hell_um",
                  on_change=lambda: st.session_state.update(
                      dunkel=not st.session_state.hell_um))


# ----------------------------------------------------------------- Übersicht
def zeige_uebersicht() -> None:
    kopfzeile("STUFE 1 · KURSFILTER")
    st.title("Julas Aktien-Screener")
    st.markdown(
        f"<div class='leise'>Stand {stand} &nbsp;·&nbsp; {len(daten)} Titel mindestens "
        f"20 % unter ihrem 52-Wochen-Hoch</div>", unsafe_allow_html=True)
    st.write("")

    s1, s2, s3 = st.columns([2, 2, 2])
    schwelle = s1.slider("Mindestens % unter dem Jahreshoch", 20, 50, 20, step=1)
    laender = sorted(daten["land"].dropna().unique())
    wahl_land = s2.multiselect("Land", laender, default=[])
    sektoren = sorted(daten["sektor"].dropna().unique())
    wahl_sektor = s3.multiselect("Sektor", sektoren, default=[])

    st.markdown("**Die Großen 5** — jeweils mindestens 10 % pro Jahr")
    spalten = st.columns(5)
    gewaehlt = []
    for nr, (schluessel, (bezeichnung, _)) in enumerate(GROSSE5.items()):
        moeglich = int((daten[schluessel] >= HUERDE).sum())
        if spalten[nr].checkbox(f"{bezeichnung} ({moeglich})", key=f"f_{schluessel}"):
            gewaehlt.append(schluessel)
    ohne_wert = st.checkbox("Titel ohne Angabe trotzdem anzeigen", value=False)

    treffer = daten[daten["vom_hoch_pct"] <= -schwelle]
    if wahl_land:
        treffer = treffer[treffer["land"].isin(wahl_land)]
    if wahl_sektor:
        treffer = treffer[treffer["sektor"].isin(wahl_sektor)]
    for schluessel in gewaehlt:
        erfuellt = treffer[schluessel] >= HUERDE
        treffer = treffer[erfuellt | (treffer[schluessel].isna() & ohne_wert)]

    st.markdown(f"**{len(treffer)} Treffer**")
    if treffer.empty:
        st.info("Keine Titel in diesem Bereich.")
        return

    anzeige = treffer[["ticker", "name", "land", "sektor", "kurs",
                       "aend_1m", "aend_ytd", "vom_hoch_pct", "rsi14"]].copy()
    anzeige.columns = ["Kürzel", "Name", "Land", "Sektor", "Kurs",
                       "1 Monat", "YTD", "% unter Hoch", "RSI"]

    def rsi_farbe(wert):
        if pd.isna(wert):
            return ""
        if wert < 30:
            return f"background-color:{F['gruen']};color:#fff;font-weight:600"
        if wert < 40:
            return f"background-color:{F['gruen']}55;font-weight:600"
        if wert > 60:
            return f"background-color:{F['rot']};color:#fff;font-weight:600"
        return ""

    stil = (anzeige.style
            .map(rsi_farbe, subset=["RSI"])
            .format({"Kurs": "{:,.2f}", "1 Monat": "{:+.1f} %", "YTD": "{:+.1f} %",
                     "% unter Hoch": "{:.1f} %", "RSI": "{:.0f}"}, na_rep="—"))

    st.caption("Zeile anklicken, um die Einzelprüfung zu öffnen.")
    auswahl = st.dataframe(stil, hide_index=True, use_container_width=True,
                           height=460, key="tabelle", on_select="rerun",
                           selection_mode="single-row")
    try:
        zeilen = auswahl.selection["rows"]
    except Exception:
        zeilen = []
    if zeilen:
        st.session_state.titel = treffer.iloc[zeilen[0]]["ticker"]
        st.rerun()

    st.write("")
    st.markdown(
        "<div class='hinweis'>Der Filter zeigt Titel, die deutlich unter ihrem "
        "Jahreshoch stehen. Das trifft vorübergehend abgestrafte Unternehmen "
        "ebenso wie dauerhaft fallende — die Einzelprüfung zeigt, welcher Fall "
        "vorliegt. Keine Kaufempfehlung.</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------- Detail
def kachel(bezeichnung: str, faktor: dict) -> str:
    farbe = AMPEL[faktor["ampel"]]
    return (f"<div class='kachel' style='border-left-color:{farbe}'>"
            f"<div class='bez'>{bezeichnung}</div>"
            f"<div class='wert' style='color:{farbe}'>{faktor['text']}</div>"
            f"<div class='hint'>{faktor['hinweis']}</div></div>")


def zeige_detail(ticker: str) -> None:
    zeile = daten[daten["ticker"] == ticker].iloc[0]

    if st.button("← Zurück zur Übersicht"):
        st.session_state.titel = None
        st.rerun()

    kopfzeile("STUFE 2 · EINZELPRÜFUNG")
    kopf, preis = st.columns([3, 1])
    kopf.title(zeile["name"])
    kopf.markdown(
        f"<div class='leise'>{zeile['ticker']} · {zeile['land']} · {zeile['sektor']}"
        f" · {zeile['marktkap_mrd']:.1f} Mrd USD</div>", unsafe_allow_html=True)
    preis.metric(f"Kurs ({zeile['waehrung']})", f"{zeile['kurs']:,.2f}",
                 f"{zeile['vom_hoch_pct']:.1f} % zum Jahreshoch")

    # --- Qualitätsfaktoren + Banner ---
    with st.spinner("Kennzahlen werden geladen …"):
        faktoren = lade_qualitaet(ticker)
    erfuellt, bewertbar = qa.bilanz_zaehlen(faktoren)

    if bewertbar == 0:
        farbe, text = F["grau"], "Keine Kennzahlen verfügbar"
    else:
        anteil = erfuellt / bewertbar
        farbe = F["gruen"] if anteil >= 0.8 else F["gelb"] if anteil >= 0.5 else F["grau"]
        text = f"{erfuellt} von {bewertbar} Kriterien erfüllt"
    st.markdown(
        f"<div class='banner' style='background:{farbe}22;border:1px solid {farbe};"
        f"color:{farbe}'>{text}</div>", unsafe_allow_html=True)

    gruen_l = [k for k, v in faktoren.items() if v["ampel"] == "gruen"]
    gelb_l = [k for k, v in faktoren.items() if v["ampel"] == "gelb"]
    rot_l = [k for k, v in faktoren.items() if v["ampel"] == "rot"]
    grau_l = [k for k, v in faktoren.items() if v["ampel"] == "grau"]
    for bezeichnung, liste, farbe in [("Erfüllt", gruen_l, F["gruen"]),
                                      ("Grenzwertig", gelb_l, F["gelb"]),
                                      ("Nicht erfüllt", rot_l, F["rot"]),
                                      ("Keine Daten", grau_l, F["grau"])]:
        if liste:
            st.markdown(
                f"<div style='margin-bottom:.35rem'><span style='color:{farbe};"
                f"font-weight:600'>{bezeichnung} ({len(liste)}):</span> "
                f"<span style='color:{F['leise']}'>{', '.join(liste)}</span></div>",
                unsafe_allow_html=True)
    st.write("")

    links, rechts = st.columns([1.45, 1])

    with links:
        st.subheader("Kursverlauf")
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
        figur = go.Figure()
        figur.add_trace(go.Scatter(
            x=verlauf.index, y=verlauf.values, mode="lines",
            line=dict(color=F["chart_linie"], width=1.8),
            fill="tozeroy", fillcolor=F["chart_flaeche"],
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:,.2f}<extra></extra>"))
        figur.add_hline(y=zeile["hoch52"], line=dict(color=F["leise"], width=1, dash="dot"),
                        annotation_text="52-Wochen-Hoch",
                        annotation_font=dict(size=10, color=F["leise"]))
        figur.add_hline(y=zeile["tief52"], line=dict(color=F["leise"], width=1, dash="dot"),
                        annotation_text="52-Wochen-Tief",
                        annotation_font=dict(size=10, color=F["leise"]))
        figur.update_layout(
            template=F["plotly"], height=330, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, hovermode="x unified")
        figur.update_xaxes(dtick="M12" if wahl not in {"1 J", "YTD"} else "M3",
                           tickformat="%Y" if wahl not in {"1 J", "YTD"} else "%b %y",
                           showgrid=False,
                           tickfont=dict(color=F["leise"]))
        figur.update_yaxes(gridcolor=F["linie"], tickfont=dict(color=F["leise"]))
        st.plotly_chart(figur, use_container_width=True)

        st.subheader("Warum steht der Titel hier?")
        st.dataframe(pd.DataFrame({
            "Kriterium": ["Abstand zum 52-Wochen-Hoch", "Abstand zum 52-Wochen-Tief",
                          "Lage in der Jahresspanne", "RSI (14 Tage)",
                          "1 Monat", "seit Jahresbeginn", "3 Monate", "12 Monate"],
            "Wert": [f"{zeile['vom_hoch_pct']:+.1f} %", f"{zeile['zum_tief_pct']:+.1f} %",
                     f"{zeile['position_spanne']:.0f} von 100", f"{zeile['rsi14']:.0f}",
                     f"{zeile['aend_1m']:+.1f} %", f"{zeile['aend_ytd']:+.1f} %",
                     f"{zeile['aend_3m']:+.1f} %", f"{zeile['aend_12m']:+.1f} %"],
        }), hide_index=True, use_container_width=True)

        termine = lade_termine(ticker)
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

        st.subheader("Die Großen 5")
        jahre = zeile.get("jahre")
        herkunft = zeile.get("quelle")
        if pd.notna(jahre) and jahre:
            st.markdown(
                f"<div class='leise'>Berechnet über {int(jahre)} Jahre · "
                f"Quelle {herkunft if pd.notna(herkunft) else 'unbekannt'}</div>",
                unsafe_allow_html=True)
        fuenf_spalten = st.columns(2)
        for nr, (schluessel, (bezeichnung, erklaerung)) in enumerate(GROSSE5.items()):
            wert = zeile.get(schluessel)
            if pd.isna(wert):
                farbe, anzeige = F["grau"], "keine Angabe"
            else:
                farbe = F["gruen"] if wert >= HUERDE else F["rot"]
                anzeige = f"{wert:+.1f} % p.a."
            fuenf_spalten[nr % 2].markdown(
                f"<div class='kachel' style='border-left-color:{farbe}'>"
                f"<div class='bez'>{bezeichnung}</div>"
                f"<div class='wert' style='color:{farbe}'>{anzeige}</div>"
                f"<div class='hint'>{erklaerung} · Hürde 10 %</div></div>",
                unsafe_allow_html=True)

        st.write("")
        st.subheader("Qualitätsfaktoren")
        st.markdown("<div class='leise'>Graue Kacheln bedeuten: keine Daten "
                    "verfügbar, nicht geschätzt.</div>", unsafe_allow_html=True)
        st.write("")
        spalten = st.columns(2)
        for i, (bezeichnung, faktor) in enumerate(faktoren.items()):
            spalten[i % 2].markdown(kachel(bezeichnung, faktor), unsafe_allow_html=True)

    with rechts:
        st.subheader("Nachrichten")
        with st.spinner("Meldungen werden geladen …"):
            meldungen = lade_nachrichten(ticker, str(zeile["name"]))

        if not meldungen:
            st.info("Keine Unternehmensmeldungen der letzten 30 Tage.")
        else:
            pos, neg, neu = nw.stimmungsbild(meldungen)
            if pos or neg or neu:
                st.markdown(
                    f"<span style='color:{F['gruen']}'>▲ {pos} positiv</span> &nbsp; "
                    f"<span style='color:{F['rot']}'>▼ {neg} negativ</span> &nbsp; "
                    f"<span style='color:{F['leise']}'>● {neu} neutral</span>",
                    unsafe_allow_html=True)
                st.write("")

            for meldung in meldungen:
                farbe = {"positiv": F["gruen"], "negativ": F["rot"]}.get(
                    meldung.get("ton"), F["grau"])
                titel = (f"<a href='{meldung['link']}' target='_blank'>{meldung['titel']}</a>"
                         if meldung["link"] else meldung["titel"])
                zusatz = " · ".join(x for x in [meldung.get("datum", ""), meldung["quelle"],
                                                meldung.get("begruendung", "")] if x)
                st.markdown(
                    f"<div class='meldung' style='border-left-color:{farbe}'>{titel}"
                    f"<div class='leise' style='margin-top:.2rem'>{zusatz}</div></div>",
                    unsafe_allow_html=True)

            if all(m.get("ton") is None for m in meldungen):
                st.markdown(
                    "<div class='hinweis'>Ohne hinterlegten Schlüssel werden die "
                    "Schlagzeilen nicht eingestuft. Siehe ANLEITUNG.md.</div>",
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div class='hinweis'>Die Einstufung ist maschinell erzeugt und "
                    "kann Ironie, Kontext und Kursrelevanz falsch einordnen.</div>",
                    unsafe_allow_html=True)


if st.session_state.titel:
    zeige_detail(st.session_state.titel)
else:
    zeige_uebersicht()
