# Kaizen — ADHS-optimiertes Tages-Log (kleines Streamlit-Prototyp)

Minimaler Prototyp des Kaizen-Systems: Brain Dump, Daily Highlight, Micro-Commitment.

Installieren:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Starten:

```bash
streamlit run app.py
```

Designentscheidungen (erste Version):
- Lokale Speicherung in `kaizen.db` (SQLite)
- Einfache Exportfunktion nach JSON
- Deutsche Benutzeroberfläche

Nächste Schritte: ADHS-spezifische Anpassungen, Presets, Sync/Cloud-Optionen und UI-Feinschliff.

Beispieldaten & Reset:
- Die App bietet eine Option, Beispiel‑Daten einzufügen (Sidebar)
- Beispiel‑Daten sind mit dem Tag `sample_data` markiert und können separat gelöscht werden
- Es gibt einen bestätigten Komplett-Reset, der alle Einträge löscht (Eingabe `DELETE`)

Presets / Einstellungen:
- In der Sidebar gibt es ein Einstellungs-Panel, um `Punkte pro Aufgabe`, `Punkte pro Level` und `Standard-Micro-Commit` zu konfigurieren.
- Einstellungen werden in der lokalen Datenbank (`settings` Tabelle) gespeichert und bleiben erhalten.
- Es gibt eine Schaltfläche zum Zurücksetzen auf Standardwerte.
