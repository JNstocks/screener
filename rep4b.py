from pathlib import Path
n = Path("nachrichten.py"); t = n.read_text(encoding="utf-8"); z = 0

if "TAGE_ZURUECK" not in t:
    t = t.replace('MODELL = "claude-sonnet-4-6"',
                  'MODELL = "claude-sonnet-4-6"\nTAGE_ZURUECK = 30', 1)
    t = t.replace("import json\nimport os\nimport re",
                  "import json\nimport os\nimport re\n"
                  "from datetime import datetime, timedelta, timezone", 1); z += 1

alt = "def schlagzeilen(ticker: str, anzahl: int = 8) -> list:"
neu = '''def _zeitpunkt(inhalt, eintrag):
    roh = inhalt.get("pubDate") or inhalt.get("displayTime")
    if roh:
        try:
            return datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
        except ValueError:
            pass
    stempel = eintrag.get("providerPublishTime") or inhalt.get("providerPublishTime")
    if stempel:
        try:
            return datetime.fromtimestamp(int(stempel), tz=timezone.utc)
        except (ValueError, OSError):
            pass
    return None


def _betrifft(inhalt, eintrag, ticker, firma, titel):
    kuerzel = ticker.split(".")[0].upper()
    bezug = eintrag.get("relatedTickers") or inhalt.get("relatedTickers") or []
    if bezug:
        return any(kuerzel == str(b).split(".")[0].upper() for b in bezug)
    if kuerzel in titel.upper().split():
        return True
    egal = {"corp", "inc", "plc", "group", "holding", "holdings", "company",
            "limited", "ltd", "the", "and", "international", "gmbh"}
    for wort in re.split(r"[\\s,.]+", firma):
        if len(wort) >= 4 and wort.lower() not in egal and wort.lower() in titel.lower():
            return True
    return False


def schlagzeilen(ticker: str, anzahl: int = 8, firma: str = "") -> list:'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

alt = '''    treffer = []
    for eintrag in roh[:anzahl]:
        inhalt = eintrag.get("content", eintrag)
        titel = inhalt.get("title") or eintrag.get("title")
        if not titel:
            continue'''
neu = '''    grenze = datetime.now(timezone.utc) - timedelta(days=TAGE_ZURUECK)
    treffer = []
    for eintrag in roh:
        if len(treffer) >= anzahl:
            break
        inhalt = eintrag.get("content", eintrag)
        titel = inhalt.get("title") or eintrag.get("title")
        if not titel:
            continue
        wann = _zeitpunkt(inhalt, eintrag)
        if wann is not None and wann < grenze:
            continue
        if not _betrifft(inhalt, eintrag, ticker, firma or ticker, titel):
            continue'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

alt = '''        treffer.append({"titel": titel, "quelle": quelle or "",
                        "link": link or "", "ton": None, "begruendung": ""})'''
neu = '''        treffer.append({"titel": titel, "quelle": quelle or "",
                        "link": link or "", "ton": None, "begruendung": "",
                        "datum": wann.strftime("%d.%m.") if wann else ""})'''
if alt in t:
    t = t.replace(alt, neu, 1); z += 1

n.write_text(t, encoding="utf-8")
print(f"nachrichten.py: {z} Stellen geändert.")