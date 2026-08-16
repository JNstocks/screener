from pathlib import Path

datei = Path("app.py")
text = datei.read_text(encoding="utf-8")
zaehler = 0

alt = '''            fill="tozeroy", fillcolor=F["chart_linie"] + "1A",'''
neu = '''            fill="tozeroy", fillcolor=F["chart_flaeche"],'''
if alt in text:
    text = text.replace(alt, neu, 1); zaehler += 1

for schema, rgba in [('"chart_linie": "#5AA9E6",', '"chart_flaeche": "rgba(90,169,230,0.12)",'),
                     ('"chart_linie": "#1F6FB2",', '"chart_flaeche": "rgba(31,111,178,0.10)",')]:
    if schema in text and "chart_flaeche" not in text.split(schema)[1][:80]:
        text = text.replace(schema, schema + "\n    " + rgba, 1); zaehler += 1

alt = '''    st.dataframe(stil, hide_index=True, use_container_width=True, height=460)

    st.write("")
    gewaehlt = st.selectbox(
        "Titel prüfen",
        treffer["ticker"],
        format_func=lambda t: f"{t} — {treffer.loc[treffer.ticker == t, 'name'].iloc[0]}")
    if st.button("Einzelprüfung öffnen", type="primary"):
        st.session_state.titel = gewaehlt
        st.rerun()'''
neu = '''    st.caption("Zeile anklicken, um die Einzelprüfung zu öffnen.")
    auswahl = st.dataframe(stil, hide_index=True, use_container_width=True,
                           height=460, key="tabelle", on_select="rerun",
                           selection_mode="single-row")
    try:
        zeilen = auswahl.selection["rows"]
    except Exception:
        zeilen = []
    if zeilen:
        st.session_state.titel = treffer.iloc[zeilen[0]]["ticker"]
        st.rerun()'''
if alt in text:
    text = text.replace(alt, neu, 1); zaehler += 1

alt = '''    links, rechts = st.columns([1.45, 1])'''
neu = '''    gruen_l = [k for k, v in faktoren.items() if v["ampel"] == "gruen"]
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

    links, rechts = st.columns([1.45, 1])'''
if alt in text:
    text = text.replace(alt, neu, 1); zaehler += 1

datei.write_text(text, encoding="utf-8")
print(f"{zaehler} Stellen geändert.")