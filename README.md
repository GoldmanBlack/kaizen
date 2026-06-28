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
- Fokus auf ADHS: Brain Dump, Daily Highlight, Micro-Commitment, Timer und Gamification

Features:
- Brain Dump: schneller Kopf frei machen und spontane Gedanken festhalten
- Daily Highlight: nur eine Schlüsselfrage als Fokus für den Tag
- Micro-Commitment: winzige 2-Minuten-Aufgaben zum Starten
- Stoppuhr / Start-Stop-Buttons für aktive Aufgaben
- Punkte- und Levelsystem zur Gamification
- Sync/Export: JSON-Export und optionaler GitHub-Gist-Sync
- Beispiel-Daten mit Reset-Funktion zur schnellen Demo
- Anpassbare Einstellungen für Punktvergabe, Level-Schwellen und Standard-Micro-Commit

Setup:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Start:
```bash
streamlit run app.py
```

Repository:
- GitHub: https://github.com/GoldmanBlack/kaizen

Nutzung:
1. Öffne die App im Browser.
2. Fülle im Brain Dump deine Gedanken und Ideen ein.
3. Setze ein Daily Highlight als deine wichtigste Aufgabe.
4. Starte ein Micro-Commitment und nutze den Timer, um den ersten Schritt zu machen.
5. Markiere Aufgaben als erledigt, um Punkte zu sammeln und im Level aufzusteigen.

Hinweise:
- `kaizen.db` wird lokal im Projektverzeichnis erstellt.
- In der Sidebar kannst du Beispiel-Daten hinzufügen oder komplett zurücksetzen.
- Nutze `Einstellungen speichern`, um Punkteschwellen und Timer-Defaults anzupassen.
- Wenn du GitHub-Gist-Sync nutzen willst, musst du den Token lokal einfügen und `gist` Berechtigungen erlauben.

Nächste Schritte: Zusätzliche ADHS-Anpassungen, UI-Design, mobile Darstellung und erweitertes Reporting.
