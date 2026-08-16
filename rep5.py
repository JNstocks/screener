from pathlib import Path

a = Path("app.py"); t = a.read_text(encoding="utf-8"); z = 0

anker = '''if "dunkel" not in st.session_state:'''
tor = '''def zugang_pruefen() -> bool:
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


if "dunkel" not in st.session_state:'''

if "def zugang_pruefen" not in t and anker in t:
    t = t.replace(anker, tor, 1); z += 1
a.write_text(t, encoding="utf-8")

w = Path(".github/workflows/taeglich.yml")
if w.exists():
    y = w.read_text(encoding="utf-8")
    alt = """      - name: Kursdaten holen
        run: python daten_holen.py
"""
    neu = """      - name: Kursdaten holen
        run: python daten_holen.py
      - name: Stammdaten holen
        run: python stammdaten_holen.py
        continue-on-error: true
"""
    if "stammdaten_holen" not in y and alt in y:
        w.write_text(y.replace(alt, neu, 1), encoding="utf-8"); z += 1

print(f"{z} Stellen geändert.")