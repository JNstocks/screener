from pathlib import Path

w = Path(".github/workflows/taeglich.yml")
y = w.read_text(encoding="utf-8")

zusatz = """      - name: Grosse 5 berechnen
        run: python grosse5_holen.py
        continue-on-error: true
"""

stamm = """      - name: Stammdaten holen
        run: python stammdaten_holen.py
        continue-on-error: true
"""
kurse = """      - name: Kursdaten holen
        run: python daten_holen.py
"""

if "grosse5_holen" in y:
    print("Ist bereits eingetragen.")
elif stamm in y:
    w.write_text(y.replace(stamm, stamm + zusatz, 1), encoding="utf-8")
    print("Eingetragen nach dem Stammdaten-Schritt.")
elif kurse in y:
    w.write_text(y.replace(kurse, kurse + zusatz, 1), encoding="utf-8")
    print("Eingetragen nach dem Kursdaten-Schritt.")
else:
    print("Stelle nicht gefunden - schick mir diese Meldung.")