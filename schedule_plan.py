#!/usr/bin/env python3
"""Entscheidet bei geplanten Läufen, ob jetzt gepostet wird.

GitHub-Cron läuft in UTC. Damit 07:17 und 19:17 Uhr Berliner Zeit ganzjährig stimmen,
gibt es je Zeitfenster zwei Crons (Sommer- und Winterzeit). Dieses Skript lässt nur den
passenden durch, wählt im Modus "test" täglich abwechselnd Morgen oder Abend und
verhindert mehr als einen Beitrag pro Berliner Kalendertag.

Aufruf im Workflow:  python schedule_plan.py   -> schreibt run=true|false nach $GITHUB_OUTPUT
Nur Standardbibliothek, damit der Schritt vor der Installation laufen kann.
"""
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
BERLIN = ZoneInfo("Europe/Berlin")


def load(name, default):
    path = ROOT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def scheduled_slot(schedule, now, slots):
    """Ordnet einen Cron-Ausdruck ('17 6 * * *') dem Berliner Zeitfenster zu, das er heute trifft."""
    minute, hour = (int(x) for x in schedule.split()[:2])
    planned = now.astimezone(dt.timezone.utc).replace(hour=hour, minute=minute, second=0, microsecond=0)
    local_hour = planned.astimezone(BERLIN).hour
    for name, slot_hour in slots.items():
        if local_hour == slot_hour:
            return name
    return None


def wanted_slot(day, mode):
    """Modus 'morning'/'evening' fest, Modus 'test' wechselt täglich (gerade Tageszahl = Morgen)."""
    if mode in ("morning", "evening"):
        return mode
    return "morning" if day.toordinal() % 2 == 0 else "evening"


def posted_on(state, day):
    for entry in state:
        stamp = entry.get("posted")
        if stamp and dt.datetime.fromisoformat(stamp).astimezone(BERLIN).date() == day:
            return True
    return False


def decide(schedule, now, cfg, state):
    """Gibt (ja/nein, Begründung) zurück."""
    if not schedule:
        return True, "manuell gestartet"
    day = now.astimezone(BERLIN).date()
    slot = scheduled_slot(schedule, now, cfg.get("slots", {"morning": 7, "evening": 19}))
    if slot is None:
        return False, f"Cron '{schedule}' gehört heute nicht zu einem Zeitfenster (Sommer-/Winterzeit)"
    wanted = wanted_slot(day, cfg.get("posting_mode", "test"))
    if slot != wanted:
        return False, f"heute ist das Zeitfenster '{wanted}' dran, nicht '{slot}'"
    if posted_on(state, day):
        return False, f"am {day:%d.%m.%Y} wurde bereits gepostet"
    return True, f"Zeitfenster '{slot}' am {day:%d.%m.%Y}"


if __name__ == "__main__":
    ok, reason = decide(os.environ.get("SCHEDULE", "").strip(), dt.datetime.now(dt.timezone.utc),
                        load("config.json", {}), load("state/posted.json", []))
    print(("Lauf startet: " if ok else "Kein Post: ") + reason)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"run={'true' if ok else 'false'}\n")
