from pathlib import Path

datei = Path("universum_bauen.py")
text = datei.read_text(encoding="utf-8")

alt = """        antwort = requests.get(url, headers=KOPF, timeout=30)
        if antwort.status_code != 200:
            print(f"  {name:22s} Status {antwort.status_code}")
            return pd.DataFrame()"""

neu = """        antwort = None
        for versuch in range(4):
            antwort = requests.get(url, headers=KOPF, timeout=30)
            if antwort.status_code == 200:
                break
            time.sleep(3 * (versuch + 1))
        if antwort is None or antwort.status_code != 200:
            print(f"  {name:22s} Status {antwort.status_code}")
            return pd.DataFrame()"""

if "for versuch in range" in text:
    print("Bereits erledigt.")
elif alt in text:
    datei.write_text(text.replace(alt, neu, 1), encoding="utf-8")
    print("Repariert.")
else:
    print("Stelle nicht gefunden - schick mir diese Meldung.")