from pathlib import Path

datei = Path("universum_bauen.py")
text = datei.read_text(encoding="utf-8")

kopf = '''import io
import requests
import pandas as pd

KOPF = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"}'''

neu = '''        antwort = requests.get(url, headers=KOPF, timeout=30)
        if antwort.status_code != 200:
            print(f"  {name:22s} Status {antwort.status_code}")
            return pd.DataFrame()
        tabellen = pd.read_html(io.StringIO(antwort.text))'''

if "KOPF = {" in text:
    print("Datei ist bereits repariert.")
else:
    text = text.replace("import pandas as pd", kopf, 1)
    text = text.replace("        tabellen = pd.read_html(url)", neu, 1)
    datei.write_text(text, encoding="utf-8")
    print("Repariert.")