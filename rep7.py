from pathlib import Path

a = Path("app.py"); t = a.read_text(encoding="utf-8"); z = 0

alt = '''@st.cache_data
def lade_tabelle() -> pd.DataFrame:
    return pd.read_csv(DATEN / "kennzahlen.csv")'''
neu = '''GROSSE5 = {
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
    return tabelle'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

alt = '''    treffer = daten[daten["vom_hoch_pct"] <= -schwelle]
    if wahl_land:
        treffer = treffer[treffer["land"].isin(wahl_land)]
    if wahl_sektor:
        treffer = treffer[treffer["sektor"].isin(wahl_sektor)]
'''
neu = '''    st.markdown("**Die Großen 5** — jeweils mindestens 10 % pro Jahr")
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
'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

alt = '''        st.subheader("Qualitätsfaktoren")'''
neu = '''        st.subheader("Die Großen 5")
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
        st.subheader("Qualitätsfaktoren")'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

a.write_text(t, encoding="utf-8")
print(f"{z} Stellen geändert.")
