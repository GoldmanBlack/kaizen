import streamlit as st
import sqlite3
from datetime import datetime, date, timedelta
import time

DB_PATH = "kaizen.db"

# Scoring configuration
POINTS_PER_TASK = 10
LEVEL_STEP = 100

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY,
        entry_type TEXT,
        content TEXT,
        tags TEXT,
        priority INTEGER DEFAULT 0,
        estimate_minutes INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        created_at TEXT,
        entry_date TEXT,
        done INTEGER DEFAULT 0,
        completed_at TEXT,
        elapsed_seconds INTEGER DEFAULT 0,
        last_modified TEXT,
        started_at TEXT
    )
    ''')
    # ensure compatibility when adding started_at to existing DBs
    c.execute("PRAGMA table_info(entries)")
    cols = [r[1] for r in c.fetchall()]
    if 'started_at' not in cols:
        try:
            c.execute('ALTER TABLE entries ADD COLUMN started_at TEXT')
        except Exception:
            pass
    # settings table
    c.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return default


def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, str(value)))
    conn.commit()
    conn.close()

def add_entry(entry_type, content, tags=None, priority=0, estimate=0, points=0):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO entries (entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, last_modified)
                 VALUES (?,?,?,?,?,?,?,?,?)''',
              (entry_type, content, tags or "", priority, estimate, points, now, date.today().isoformat(), now))
    conn.commit()
    conn.close()

def get_today_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points, created_at, done, completed_at, elapsed_seconds, started_at
                 FROM entries WHERE entry_date=? ORDER BY id DESC''', (date.today().isoformat(),))
    rows = c.fetchall()
    conn.close()
    return rows

def toggle_done(entry_id, new, elapsed_seconds=0, points=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    if new:
        # mark completed
        if points is None:
            points = POINTS_PER_TASK
        c.execute('UPDATE entries SET done=1, completed_at=?, elapsed_seconds=?, points=?, last_modified=?, started_at=NULL WHERE id=?',
                  (now, elapsed_seconds, points, now, entry_id))
    else:
        c.execute('UPDATE entries SET done=0, completed_at=NULL, elapsed_seconds=0, points=0, last_modified=?, started_at=NULL WHERE id=?',
                  (now, entry_id))
    conn.commit()
    conn.close()

def total_points():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT SUM(points) FROM entries')
    s = c.fetchone()[0] or 0
    conn.close()
    return s

def get_level_and_progress():
    try:
        level_step = int(get_setting('level_step') or LEVEL_STEP)
    except Exception:
        level_step = LEVEL_STEP
    pts = total_points()
    level = pts // level_step
    progress = pts % level_step
    return level, progress, level_step

### GitHub Gist sync helpers (optional)
import requests

def gist_save(token, gist_id, data_dict):
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {"Authorization": f"token {token}"}
    files = {"kaizen.json": {"content": data_dict}}
    r = requests.patch(url, json={"files": files}, headers=headers)
    return r.status_code, r.text

def gist_create(token, data_dict, description="Kaizen export"):
    url = "https://api.github.com/gists"
    headers = {"Authorization": f"token {token}"}
    files = {"kaizen.json": {"content": data_dict}}
    r = requests.post(url, json={"files": files, "description": description, "public": False}, headers=headers)
    return r.status_code, r.json()


def start_task(entry_id):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE entries SET started_at=?, last_modified=? WHERE id=?', (now, now, entry_id))
    conn.commit()
    conn.close()


def clear_start(entry_id):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE entries SET started_at=NULL, last_modified=? WHERE id=?', (now, entry_id))
    conn.commit()
    conn.close()


def compute_points(elapsed_seconds, estimate_minutes):
    elapsed_minutes = int(round(elapsed_seconds / 60)) if elapsed_seconds else 0
    try:
        base = int(get_setting('points_per_task') or POINTS_PER_TASK)
    except Exception:
        base = POINTS_PER_TASK
    bonus = 0
    if estimate_minutes and estimate_minutes > 0:
        saved = max(0, estimate_minutes - elapsed_minutes)
        bonus = saved * 2
    # small speed bonus for very fast completion (<5min)
    if elapsed_minutes <= 5:
        bonus += 1
    return base + bonus


### Sample data / reset helpers
def insert_sample_data():
    samples = [
        ("brain", "Gedanken: Heute an Projekt X denken", "sample_data"),
        ("brain", "Idee: Microblog starten", "sample_data"),
        ("highlight", "Wichtig: Erste Aufgabe für Projekt X", "sample_data"),
        ("micro", "2 Minuten: E-Mail an Jonas schreiben", "sample_data"),
        ("micro", "2 Minuten: Kurze Aufräumaktion Schreibtisch", "sample_data"),
    ]
    for etype, content, tags in samples:
        add_entry(etype, content, tags=tags, estimate=2, points=0)

def delete_sample_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE tags LIKE '%sample_data%'")
    conn.commit()
    conn.close()

def delete_all_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM entries')
    conn.commit()
    conn.close()

def main():
    st.set_page_config(page_title="Kaizen — ADHS-optimiert", layout="centered")
    st.title("Kaizen — Tageslog (ADHS-freundlich)")

    init_db()

    st.markdown("""
    Einfache 3‑Schritte-Tageseinheit: Brain Dump, Daily Highlight, Micro‑Commitment.
    Ziel: den Kopf leeren, eine einzige Priorität setzen und mit einem winzigen Schritt Momentum erzeugen.
    """)

    # Brain Dump
    st.header("Brain Dump — Alles raus")
    with st.form("brain_form"):
        brain_text = st.text_area("Schreib alles auf, was dir gerade im Kopf ist", height=120)
        tags = st.text_input("Tags (Komma-getrennt)")
        submitted = st.form_submit_button("Hinzufügen")
        if submitted and brain_text.strip():
            add_entry("brain", brain_text.strip(), tags=tags)
            st.success("Gespeichert — gut gemacht.")

    # Daily Highlight
    st.header("Daily Highlight — EINE Aufgabe")
    today_entries = get_today_entries()
    brain_texts = [r[2] for r in today_entries if r[1]=="brain"]
    with st.form("highlight_form"):
        choice = st.selectbox("Aus Brain Dump wählen (optional)", [""] + brain_texts)
        highlight = st.text_input("Oder tippe eine neue Highlight-Aufgabe", value="" if not choice else choice)
        tags = st.text_input("Tags (optional)")
        estimate = st.number_input("Geschätzte Minuten (optional)", min_value=0, step=5)
        set_hl = st.form_submit_button("Als Daily Highlight setzen")
        if set_hl and highlight.strip():
            add_entry("highlight", highlight.strip(), tags=tags, estimate=estimate)
            st.success("Daily Highlight gesetzt — fokussiere dich auf diese Aufgabe.")

    # Micro-Commitment
    st.header("Micro-Commitment — 2 Minuten")
    with st.form("micro_form"):
        micro = st.text_input("2-Minuten-Aktion (z.B. E‑Mail beantworten)")
        tags = st.text_input("Tags (optional)")
        start = st.form_submit_button("Start 2-Minuten")
        if start and micro.strip():
            add_entry("micro", micro.strip(), tags=tags)
            st.info("Micro-Commitment gespeichert. Starte den Timer unten.")

    if st.button("Timer 2 Minuten anzeigen/starten"):
        placeholder = st.empty()
        total = 120
        for i in range(total, -1, -1):
            mins, secs = divmod(i, 60)
            placeholder.markdown(f"**Verbleibend:** {mins:02d}:{secs:02d}")
            time.sleep(1)
        placeholder.markdown("**Fertig!** Gut gemacht. Markiere dein Micro-Commitment als erledigt.")

    # Today's entries
    st.header("Heute — Einträge")
    rows = get_today_entries()
    if not rows:
        st.write("Noch nichts für heute — fang mit einem Brain Dump an.")
    else:
        for r in rows:
            eid, etype, content, tags, priority, estimate, points, created_at, done, completed_at, elapsed_seconds = r
            cols = st.columns([0.55, 0.15, 0.15, 0.15])
            with cols[0]:
                st.write(f"**{etype}** — {content}")
                if tags:
                    st.caption(f"Tags: {tags}")
                if estimate:
                    st.caption(f"Schätzung: {estimate} min")
                if started_at:
                    st.caption(f"gestartet: {started_at}")
                st.caption(f"erstellt: {created_at}")
            with cols[1]:
                if done:
                    st.write(f"✅ {points} pts")
                else:
                    st.write("—")
            with cols[2]:
                start_btn = st.button("Start", key=f"start_{eid}")
                if start_btn:
                    start_task(eid)
                    st.experimental_rerun()
                stop_btn = st.button("Stop", key=f"stop_{eid}")
                if stop_btn:
                    # stop means compute elapsed since started_at and mark done
                    elapsed = 0
                    if started_at:
                        try:
                            sa = datetime.fromisoformat(started_at)
                            elapsed = int((datetime.utcnow() - sa).total_seconds())
                        except Exception:
                            elapsed = 0
                    pts = compute_points(elapsed, estimate)
                    toggle_done(eid, True, elapsed_seconds=elapsed, points=pts)
                    st.experimental_rerun()
            with cols[3]:
                new = st.checkbox("Erledigt", value=bool(done), key=f"done_{eid}")
                if new != bool(done):
                    if new:
                        elapsed = 0
                        if started_at:
                            try:
                                sa = datetime.fromisoformat(started_at)
                                elapsed = int((datetime.utcnow() - sa).total_seconds())
                            except Exception:
                                elapsed = 0
                        pts = compute_points(elapsed, estimate)
                        toggle_done(eid, new, elapsed_seconds=elapsed, points=pts)
                    else:
                        toggle_done(eid, new, elapsed_seconds=0)
                    st.experimental_rerun()

    # Scoring and level
    level, progress, goal = get_level_and_progress()
    st.sidebar.header(f"Score: {total_points()} pts — Level {level}")
    st.sidebar.progress(int(progress / goal * 100))

    st.sidebar.header("Quick Actions")
    # Settings / Presets
    st.sidebar.subheader("Einstellungen / Presets")
    with st.sidebar.expander("Punkte & Level Einstellungen"):
        pts_input = st.number_input("Punkte pro Aufgabe (Basis)", value=int(get_setting('points_per_task') or POINTS_PER_TASK), min_value=1)
        lvl_input = st.number_input("Punkte pro Level (Level-Schwelle)", value=int(get_setting('level_step') or LEVEL_STEP), min_value=10)
        timer_default = st.number_input("Standard-Micro-Commit (Minuten)", value=int(get_setting('timer_default') or 2), min_value=1)
        if st.button("Einstellungen speichern"):
            set_setting('points_per_task', pts_input)
            set_setting('level_step', lvl_input)
            set_setting('timer_default', timer_default)
            st.sidebar.success("Einstellungen gespeichert.")
        if st.button("Einstellungen zurücksetzen"):
            set_setting('points_per_task', POINTS_PER_TASK)
            set_setting('level_step', LEVEL_STEP)
            set_setting('timer_default', 2)
            st.sidebar.success("Einstellungen auf Standard zurückgesetzt.")

    st.sidebar.subheader("Sync / Export")
    if st.sidebar.checkbox("Online-Sync aktivieren (GitHub Gist)"):
        token = st.sidebar.text_input("GitHub Token (mit gist scope)", type="password")
        gist_id = st.sidebar.text_input("Gist ID (leer → neuer Gist)")
        if st.sidebar.button("Exportiere alle Daten als Gist"):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT id, entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, done, completed_at, elapsed_seconds FROM entries')
            allrows = c.fetchall()
            conn.close()
            import json
            payload = json.dumps([dict(id=r[0], type=r[1], content=r[2], tags=r[3], priority=r[4], estimate=r[5], points=r[6], created_at=r[7], entry_date=r[8], done=r[9], completed_at=r[10], elapsed_seconds=r[11]) for r in allrows], ensure_ascii=False)
            if token and gist_id:
                status, text = gist_save(token, gist_id, payload)
                st.write(f"Gist update status: {status}")
            elif token and not gist_id:
                status, resp = gist_create(token, payload)
                if status == 201:
                    st.write("Gist erstellt:", resp.get('html_url'))
                else:
                    st.write("Fehler beim Erstellen des Gists", status, resp)
            else:
                st.download_button("Download JSON", data=payload, file_name=f"kaizen_export_{date.today().isoformat()}.json")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Beispieldaten & Reset")
    if st.sidebar.button("Beispieldaten einfügen"):
        insert_sample_data()
        st.sidebar.success("Beispieldaten eingefügt.")

    if st.sidebar.button("Beispieldaten löschen"):
        delete_sample_data()
        st.sidebar.success("Beispieldaten gelöscht.")

    with st.sidebar.expander("Kompletten Reset (alle Daten löschen)"):
        confirm = st.text_input("Gib DELETE ein, um alle Daten zu löschen")
        if st.button("Alle Daten löschen") and confirm == "DELETE":
            delete_all_data()
            st.sidebar.success("Alle Daten gelöscht.")

    st.sidebar.markdown("---")
    st.sidebar.write("Tip: Nutze das Daily Highlight als einzige Priorität. Micro-Commitments starten Routine.")

if __name__ == '__main__':
    main()
