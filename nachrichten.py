"""
Nachrichten zu einem Titel, optional mit Tonalitaetsbewertung.

Die Bewertung uebernimmt ein Sprachmodell. Ohne hinterlegten Schluessel werden
die Schlagzeilen ohne Einstufung angezeigt - bewusst grau statt geraten.

Schluessel hinterlegen:
  lokal      Datei .streamlit/secrets.toml  ->  ANTHROPIC_API_KEY = "sk-ant-..."
  im Netz    In der Streamlit-Oberflaeche unter Settings -> Secrets
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

import yfinance as yf

MODELL = "claude-sonnet-4-6"
TAGE_ZURUECK = 30


def schluessel() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None


def _zeitpunkt(inhalt, eintrag):
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
    for wort in re.split(r"[\s,.]+", firma):
        if len(wort) >= 4 and wort.lower() not in egal and wort.lower() in titel.lower():
            return True
    return False


def schlagzeilen(ticker: str, anzahl: int = 8, firma: str = "") -> list:
    try:
        roh = yf.Ticker(ticker).news or []
    except Exception:
        return []

    grenze = datetime.now(timezone.utc) - timedelta(days=TAGE_ZURUECK)
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
            continue
        anbieter = inhalt.get("provider")
        quelle = anbieter.get("displayName") if isinstance(anbieter, dict) \
            else eintrag.get("publisher", "")
        adresse = inhalt.get("canonicalUrl")
        link = adresse.get("url") if isinstance(adresse, dict) else eintrag.get("link", "")
        treffer.append({"titel": titel, "quelle": quelle or "",
                        "link": link or "", "ton": None, "begruendung": "",
                        "datum": wann.strftime("%d.%m.") if wann else ""})
    return treffer


def bewerten(meldungen: list, firma: str) -> list:
    """Stuft die Schlagzeilen ein. Ohne Schluessel bleibt alles unbewertet."""
    key = schluessel()
    if not key or not meldungen:
        return meldungen

    try:
        import anthropic
    except ImportError:
        return meldungen

    liste = "\n".join(f"{i}. {m['titel']}" for i, m in enumerate(meldungen))
    auftrag = (
        f"Bewerte jede Schlagzeile zu {firma} danach, ob sie für Aktionäre eher "
        f"positiv, negativ oder neutral ist. Antworte ausschließlich mit einem "
        f"JSON-Array, ein Objekt je Schlagzeile, in derselben Reihenfolge, "
        f"jeweils mit den Feldern \"nr\" (Zahl), \"ton\" "
        f"(\"positiv\"|\"negativ\"|\"neutral\") und \"grund\" (maximal 8 Wörter, "
        f"auf Deutsch). Kein weiterer Text.\n\n{liste}"
    )

    try:
        antwort = anthropic.Anthropic(api_key=key).messages.create(
            model=MODELL, max_tokens=1000,
            messages=[{"role": "user", "content": auftrag}])
        text = "".join(t.text for t in antwort.content if t.type == "text")
        text = re.sub(r"```(json)?", "", text).strip()
        for eintrag in json.loads(text):
            nr = int(eintrag.get("nr", -1))
            if 0 <= nr < len(meldungen):
                meldungen[nr]["ton"] = eintrag.get("ton")
                meldungen[nr]["begruendung"] = eintrag.get("grund", "")
    except Exception:
        pass          # bei jedem Fehler bleiben die Meldungen unbewertet

    return meldungen


def stimmungsbild(meldungen: list) -> tuple:
    """(positiv, negativ, neutral) unter den bewerteten Meldungen."""
    bewertet = [m["ton"] for m in meldungen if m.get("ton")]
    return (bewertet.count("positiv"), bewertet.count("negativ"),
            bewertet.count("neutral"))
