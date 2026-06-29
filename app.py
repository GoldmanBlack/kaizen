import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from datetime import datetime, date, timedelta
import time
import json
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

DB_PATH = "kaizen.db"

POINTS_PER_TASK = 10
LEVEL_STEP = 100

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
          "Juli", "August", "September", "Oktober", "November", "Dezember"]

TYPE_LABELS = {"highlight": "⭐ Highlight", "micro": "⏱️ Micro", "brain": "📝 To-Do"}


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
        started_at TEXT,
        deadline TEXT
    )
    ''')
    c.execute("PRAGMA table_info(entries)")
    cols = [r[1] for r in c.fetchall()]
    for col, typedef in [('started_at', 'TEXT'), ('deadline', 'TEXT')]:
        if col not in cols:
            try:
                c.execute(f'ALTER TABLE entries ADD COLUMN {col} {typedef}')
            except Exception:
                pass
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
    return row[0] if row else default


def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, str(value)))
    conn.commit()
    conn.close()


def add_entry(entry_type, content, tags=None, priority=0, estimate=0, points=0,
              entry_date=None, deadline=None):
    now = datetime.utcnow().isoformat()
    entry_date = entry_date or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO entries
                 (entry_type, content, tags, priority, estimate_minutes, points,
                  created_at, entry_date, last_modified, deadline)
                 VALUES (?,?,?,?,?,?,?,?,?,?)''',
              (entry_type, content, tags or "", priority, estimate, points,
               now, entry_date, now, deadline or ""))
    conn.commit()
    conn.close()


def get_today_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points,
                        created_at, entry_date, done, completed_at, elapsed_seconds, started_at, deadline
                 FROM entries WHERE entry_date=? ORDER BY id DESC''', (date.today().isoformat(),))
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points,
                        created_at, entry_date, done, completed_at, elapsed_seconds, started_at, deadline
                 FROM entries ORDER BY entry_date DESC, id DESC''')
    rows = c.fetchall()
    conn.close()
    return rows


def toggle_done(entry_id, new, elapsed_seconds=0, points=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    if new:
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


def start_task(entry_id):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE entries SET started_at=?, last_modified=? WHERE id=?', (now, now, entry_id))
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
    if elapsed_minutes <= 5:
        bonus += 1
    return base + bonus


def get_urgency(deadline_str):
    """Returns (level, days_left, label, css_class) for a deadline string."""
    if not deadline_str:
        return "none", 9999, "", "urg-none"
    try:
        dl = date.fromisoformat(deadline_str)
        days_left = (dl - date.today()).days
        if days_left < 0:
            return "overdue", days_left, f"🔴 {abs(days_left)}T überfällig!", "urg-overdue"
        elif days_left == 0:
            return "today", 0, "🟠 Heute fällig!", "urg-today"
        elif days_left == 1:
            return "tomorrow", 1, "🟡 Morgen fällig", "urg-tomorrow"
        elif days_left <= 3:
            return "soon", days_left, f"🟢 Noch {days_left} Tage", "urg-soon"
        else:
            return "later", days_left, f"📅 {dl.strftime('%d.%m.%Y')}", "urg-later"
    except Exception:
        return "none", 9999, "", "urg-none"


# ========== ANALYTICS & PREDICTION ==========

def get_average_duration_by_type(entry_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT AVG(elapsed_seconds) FROM entries WHERE entry_type=? AND done=1 AND elapsed_seconds>0", (entry_type,))
    result = c.fetchone()[0]
    conn.close()
    return int(result / 60) if result else None


def get_average_duration_by_tags(tags_str):
    if not tags_str:
        return None
    tags_list = [t.strip() for t in tags_str.split(',')]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    durations = []
    for tag in tags_list:
        c.execute("SELECT AVG(elapsed_seconds) FROM entries WHERE tags LIKE ? AND done=1 AND elapsed_seconds>0", (f'%{tag}%',))
        result = c.fetchone()[0]
        if result:
            durations.append(int(result / 60))
    conn.close()
    return int(np.mean(durations)) if durations else None


def predict_duration(entry_type, tags=None, estimate_minutes=None):
    if estimate_minutes and estimate_minutes > 0:
        return estimate_minutes
    tag_avg = get_average_duration_by_tags(tags) if tags else None
    type_avg = get_average_duration_by_type(entry_type)
    predictions = [p for p in [tag_avg, type_avg] if p is not None]
    if predictions:
        return int(np.mean(predictions))
    return {"brain": 5, "highlight": 25, "micro": 2}.get(entry_type, 10)


def get_analytics_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM entries WHERE done=1")
    completed_tasks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM entries")
    total_tasks = c.fetchone()[0]
    c.execute("SELECT SUM(elapsed_seconds) FROM entries WHERE done=1")
    total_time = c.fetchone()[0] or 0
    c.execute("SELECT entry_type, COUNT(*), AVG(elapsed_seconds), SUM(elapsed_seconds) FROM entries WHERE done=1 GROUP BY entry_type")
    type_stats = c.fetchall()
    c.execute("SELECT tags, COUNT(*), AVG(elapsed_seconds) FROM entries WHERE done=1 AND tags IS NOT NULL AND tags!='' GROUP BY tags")
    tag_stats = c.fetchall()
    c.execute("""
        SELECT DATE(completed_at) as day, COUNT(*), SUM(elapsed_seconds)
        FROM entries WHERE done=1 AND completed_at IS NOT NULL
        AND completed_at > datetime('now', '-30 days')
        GROUP BY DATE(completed_at) ORDER BY day
    """)
    daily_trend = c.fetchall()
    conn.close()
    return {
        "completed": completed_tasks, "total": total_tasks,
        "total_minutes": int(total_time / 60),
        "type_stats": type_stats, "tag_stats": tag_stats, "daily_trend": daily_trend
    }


# ========== SAMPLE DATA / RESET ==========

def insert_sample_data():
    samples = [
        ("brain", "Gedanken: Heute an Projekt X denken", "sample_data", None),
        ("brain", "Idee: Microblog starten", "sample_data", None),
        ("highlight", "Wichtig: Erste Aufgabe für Projekt X", "sample_data",
         (date.today() + timedelta(days=1)).isoformat()),
        ("micro", "2 Minuten: E-Mail an Jonas schreiben", "sample_data",
         date.today().isoformat()),
        ("micro", "2 Minuten: Kurze Aufräumaktion Schreibtisch", "sample_data", None),
    ]
    for etype, content, tags, dl in samples:
        add_entry(etype, content, tags=tags, estimate=2, points=0, deadline=dl)


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


# ========== GIST SYNC ==========

def gist_save(token, gist_id, data_dict):
    url = f"https://api.github.com/gists/{gist_id}"
    r = requests.patch(url, json={"files": {"kaizen.json": {"content": data_dict}}},
                       headers={"Authorization": f"token {token}"})
    return r.status_code, r.text


def gist_create(token, data_dict, description="Kaizen export"):
    url = "https://api.github.com/gists"
    r = requests.post(url, json={"files": {"kaizen.json": {"content": data_dict}},
                                  "description": description, "public": False},
                      headers={"Authorization": f"token {token}"})
    return r.status_code, r.json()


# ========== SHARED CSS ==========

URGENCY_CSS = """<style>
@keyframes glow-red {
    0%,100% { box-shadow: 0 0 6px rgba(239,68,68,0.4); }
    50%      { box-shadow: 0 0 22px rgba(239,68,68,0.85); }
}
@keyframes glow-orange {
    0%,100% { box-shadow: 0 0 4px rgba(249,115,22,0.3); }
    50%      { box-shadow: 0 0 16px rgba(249,115,22,0.7); }
}
.urg-overdue  { border-left:5px solid #ef4444; background:rgba(239,68,68,0.09);
                border-radius:10px; padding:14px 18px; margin-bottom:10px;
                animation: glow-red 1.8s ease-in-out infinite; }
.urg-today    { border-left:5px solid #f97316; background:rgba(249,115,22,0.08);
                border-radius:10px; padding:14px 18px; margin-bottom:10px;
                animation: glow-orange 2.5s ease-in-out infinite; }
.urg-tomorrow { border-left:4px solid #eab308; background:rgba(234,179,8,0.07);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-soon     { border-left:4px solid #84cc16; background:rgba(132,204,22,0.06);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-later    { border-left:3px solid #60a5fa; background:rgba(96,165,250,0.05);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-none     { border-left:3px solid #475569; background:rgba(71,85,105,0.04);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-done     { opacity:0.32; text-decoration:line-through; }
.dl-badge     { display:inline-block; font-size:12px; font-weight:600;
                padding:2px 8px; border-radius:20px; margin-left:8px;
                background:rgba(255,255,255,0.08); }
/* Fokus page cards */
.fok-hl  { border-left:5px solid #ffd700; background:rgba(255,215,0,0.07);
           border-radius:10px; padding:14px 18px; margin-bottom:12px; }
.fok-mc  { border-left:4px solid #4ade80; background:rgba(74,222,128,0.06);
           border-radius:8px; padding:10px 15px; margin-bottom:8px; }
.fok-br  { border-left:4px solid #60a5fa; background:rgba(96,165,250,0.06);
           border-radius:8px; padding:10px 15px; margin-bottom:8px; }
.fok-done { opacity:0.35; text-decoration:line-through; }
</style>"""


# ========== PAGES ==========

def render_lofi_start_page():
    stats = get_analytics_stats()
    try:
        with open('static/styles.css', 'r', encoding='utf-8') as f:
            css = f.read()
    except Exception:
        css = ''
    try:
        with open('static/rain.js', 'r', encoding='utf-8') as f:
            js = f.read()
    except Exception:
        js = ''

    html = f"""
    <div style="position:relative;width:100%;height:640px;margin:-40px 0 20px 0;">
      <style>
        html,body{{margin:0;padding:0;height:100%;}}
        .lofi-bg{{position:absolute;inset:0;z-index:0;}}
        .lofi-overlay{{position:relative;z-index:2;display:flex;align-items:center;justify-content:center;height:100%;pointer-events:none}}
        .stats-box{{background:rgba(8,12,20,0.45);backdrop-filter:blur(6px);padding:18px 26px;border-radius:12px;border:1px solid rgba(255,255,255,0.04);pointer-events:auto;color:#dfefff}}
        {css}
      </style>
      <canvas id="rain" class="lofi-bg" width="1600" height="640" style="width:100%;height:100%;display:block;border-radius:0;"></canvas>
      <div class="lofi-overlay">
        <div class="stats-box">
          <div style="text-align:center;font-weight:700;font-size:28px;color:#00d4ff">🌧️ KAIZEN</div>
          <div style="text-align:center;margin:6px 0 12px;color:#dfefff">Start deinen perfekten Tag • Eins nach dem anderen</div>
          <div style="display:flex;gap:10px;justify-content:center">
            <div style="background:rgba(0,212,255,0.08);padding:10px 16px;border-radius:10px;color:#00d4ff">
              <div style="font-size:20px;font-weight:700">{stats['completed']}</div>
              <div style="font-size:12px;color:#dfefff">Aufgaben erledigt</div>
            </div>
            <div style="background:rgba(0,212,255,0.08);padding:10px 16px;border-radius:10px;color:#00d4ff">
              <div style="font-size:20px;font-weight:700">{stats['total_minutes']}</div>
              <div style="font-size:12px;color:#dfefff">Minuten investiert</div>
            </div>
            <div style="background:rgba(0,212,255,0.08);padding:10px 16px;border-radius:10px;color:#00d4ff">
              <div style="font-size:20px;font-weight:700">{total_points()}</div>
              <div style="font-size:12px;color:#dfefff">Punkte gesammelt</div>
            </div>
          </div>
        </div>
      </div>
      <script>{js}</script>
    </div>
    """
    components.html(html, height=720, scrolling=False)
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Tag starten", use_container_width=True, key="lofi_start_btn"):
            st.session_state.page = "Planen"
            st.rerun()
    st.write("")
    st.markdown("---")
    st.write("💡 **Was dich erwartet:** Brain Dump → Daily Highlight → Micro-Commitment → Tagesfokus")


def render_start_page():
    render_lofi_start_page()


def _deadline_fields(form_key):
    """Renders optional deadline picker inside a form. Returns deadline string or None."""
    use_dl = st.checkbox("⏰ Deadline setzen", value=False, key=f"use_dl_{form_key}")
    if use_dl:
        dl_date = st.date_input("Deadline", value=date.today() + timedelta(days=1),
                                 min_value=date.today(), key=f"dl_{form_key}")
        return dl_date.isoformat()
    return None


def render_planen_page():
    st.title("Tag planen")
    st.caption("Drei kurze Schritte — dann direkt in den Fokus-Modus.")

    rows = get_today_entries()
    has_brain     = any(r[1] == "brain"     for r in rows)
    has_highlight = any(r[1] == "highlight" for r in rows)
    has_micro     = any(r[1] == "micro"     for r in rows)
    steps_done    = sum([has_brain, has_highlight, has_micro])

    st.progress(steps_done / 3, text=f"Schritt {steps_done} von 3 abgeschlossen")

    if steps_done >= 1:
        _, btn_col, _ = st.columns([0.35, 0.30, 0.35])
        with btn_col:
            if st.button("Tagesfokus →", key="plan_to_focus_top", use_container_width=True):
                st.session_state.page = "Tagesfokus"
                st.rerun()

    st.markdown("---")

    # Step 1: Brain Dump
    step1_label = "✅ Brain Dump erledigt" if has_brain else "1️⃣  Brain Dump — Alles raus aus dem Kopf"
    with st.expander(step1_label, expanded=not has_brain):
        with st.form("brain_form"):
            brain_text = st.text_area("Was geht dir durch den Kopf?", height=100,
                                       placeholder="Einfach alles aufschreiben — ohne Filter")
            tags = st.text_input("Tags (optional, Komma-getrennt)")
            deadline = _deadline_fields("brain")
            if st.form_submit_button("Raus damit!"):
                if brain_text.strip():
                    add_entry("brain", brain_text.strip(), tags=tags, deadline=deadline)
                    st.rerun()

    # Step 2: Daily Highlight
    brain_texts = [r[2] for r in rows if r[1] == "brain"]
    step2_label = "✅ Daily Highlight gesetzt" if has_highlight else "2️⃣  Daily Highlight — EINE Aufgabe"
    with st.expander(step2_label, expanded=has_brain and not has_highlight):
        with st.form("highlight_form"):
            choice = st.selectbox("Aus Brain Dump wählen (optional)", [""] + brain_texts) if brain_texts else ""
            highlight = st.text_input("Highlight-Aufgabe", value=choice,
                                       placeholder="Was ist deine wichtigste Aufgabe heute?")
            tags_hl = st.text_input("Tags (optional)")
            predicted = predict_duration("highlight", tags_hl or None)
            if predicted:
                st.info(f"🤖 Basierend auf deiner Historie: ~{predicted} Minuten")
            estimate = st.number_input("Geschätzte Minuten", min_value=0, step=5, value=int(predicted or 25))
            date_input = st.date_input("Eintragsdatum", value=date.today())
            deadline_hl = _deadline_fields("hl")
            if st.form_submit_button("Als Daily Highlight setzen"):
                if highlight.strip():
                    add_entry("highlight", highlight.strip(), tags=tags_hl,
                               estimate=estimate, entry_date=date_input.isoformat(),
                               deadline=deadline_hl)
                    st.session_state.page = "Tagesfokus"
                    st.rerun()

    # Step 3: Micro-Commitment
    step3_label = "✅ Micro-Commitment hinzugefügt" if has_micro else "3️⃣  Micro-Commitment — 2 Minuten"
    with st.expander(step3_label, expanded=has_highlight and not has_micro):
        with st.form("micro_form"):
            micro = st.text_input("Was kannst du in 2 Minuten starten?",
                                   placeholder="z.B. E-Mail öffnen, Notiz anlegen...")
            tags_mc = st.text_input("Tags (optional)")
            date_input_mc = st.date_input("Datum", value=date.today(), key="mc_date")
            deadline_mc = _deadline_fields("mc")
            if st.form_submit_button("Hinzufügen & Fokus starten"):
                if micro.strip():
                    add_entry("micro", micro.strip(), tags=tags_mc,
                               entry_date=date_input_mc.isoformat(), deadline=deadline_mc)
                    st.session_state.page = "Tagesfokus"
                    st.rerun()


def render_tagesfokus_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)

    today = date.today()
    today_label = f"{WOCHENTAGE[today.weekday()]}, {today.day}. {MONATE[today.month - 1]} {today.year}"

    t_col, b_col = st.columns([0.85, 0.15])
    with t_col:
        st.title("Tagesfokus")
        st.caption(today_label)
    with b_col:
        st.write("")
        if st.button("← Planen", key="fok_back"):
            st.session_state.page = "Planen"
            st.rerun()

    rows = get_today_entries()
    total      = len(rows)
    done_count = sum(1 for r in rows if r[9])
    pts_today  = sum(r[6] for r in rows)
    pct        = done_count / total if total > 0 else 0

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Aufgaben", f"{done_count} / {total}")
    mc2.metric("Fortschritt", f"{int(pct * 100)} %")
    mc3.metric("Punkte heute", pts_today)
    st.progress(pct)
    st.markdown("---")

    if not rows:
        st.info("Noch keine Aufgaben für heute — starte mit dem Tag planen.")
        if st.button("Tag planen →", key="fok_goto_planen"):
            st.session_state.page = "Planen"
            st.rerun()
        return

    highlights = [r for r in rows if r[1] == "highlight"]
    micros     = [r for r in rows if r[1] == "micro"]
    brains     = [r for r in rows if r[1] == "brain"]

    def render_row(r, css_class, pfx):
        eid, etype, content, tags, priority, estimate, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at, deadline = r
        urg_level, urg_days, urg_label, urg_class = get_urgency(deadline)
        card_cls = f"{css_class} fok-done" if done else css_class
        dl_html = f'<span class="dl-badge">{urg_label}</span>' if urg_label and not done else ""
        st.markdown(
            f'<div class="{card_cls}"><strong>{content}</strong>{dl_html}'
            + (f'<br><small style="opacity:.6">ca. {estimate} min</small>' if estimate else "")
            + "</div>", unsafe_allow_html=True
        )
        c_chk, c_btn, _ = st.columns([0.08, 0.22, 0.70])
        with c_chk:
            new_done = st.checkbox("", value=bool(done), key=f"{pfx}_chk_{eid}",
                                   label_visibility="collapsed")
            if new_done != bool(done):
                elapsed = 0
                if started_at:
                    try:
                        sa = datetime.fromisoformat(started_at)
                        elapsed = int((datetime.utcnow() - sa).total_seconds())
                    except Exception:
                        pass
                if new_done:
                    toggle_done(eid, True, elapsed_seconds=elapsed,
                                points=compute_points(elapsed, estimate))
                else:
                    toggle_done(eid, False, elapsed_seconds=0)
                st.rerun()
        with c_btn:
            if not done:
                if started_at:
                    if st.button("Stop & ✓", key=f"{pfx}_stop_{eid}"):
                        elapsed = 0
                        try:
                            sa = datetime.fromisoformat(started_at)
                            elapsed = int((datetime.utcnow() - sa).total_seconds())
                        except Exception:
                            pass
                        toggle_done(eid, True, elapsed_seconds=elapsed,
                                    points=compute_points(elapsed, estimate))
                        st.rerun()
                else:
                    if st.button("Start", key=f"{pfx}_start_{eid}"):
                        start_task(eid)
                        st.rerun()

    if highlights:
        st.markdown("### ⭐ Daily Highlight")
        for r in highlights:
            render_row(r, "fok-hl", "hl")

    if micros:
        st.markdown("### ⏱️ Micro-Commitments")
        for r in micros:
            render_row(r, "fok-mc", "mc")

    if brains:
        st.markdown("### 📝 To-Do Liste")
        for r in brains:
            render_row(r, "fok-br", "br")

    st.markdown("---")
    with st.expander("➕ Aufgabe schnell hinzufügen"):
        with st.form("fok_quick_add"):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_task = st.text_input("Aufgabe", label_visibility="collapsed",
                                          placeholder="Neue Aufgabe...")
            with col2:
                task_type = st.selectbox("Typ", ["micro", "brain", "highlight"],
                                          label_visibility="collapsed")
            if st.form_submit_button("Hinzufügen", use_container_width=True):
                if new_task.strip():
                    add_entry(task_type, new_task.strip(),
                               estimate=predict_duration(task_type))
                    st.rerun()


def render_alle_eintraege_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)
    st.title("Alle Einträge")

    all_rows = get_all_entries()
    if not all_rows:
        st.info("Noch keine Einträge — starte mit dem Tag planen.")
        return

    # Filter
    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
    with col_f1:
        show_filter = st.selectbox("Anzeigen", ["Alle", "Offen", "Erledigt"], key="ae_filter")
    with col_f2:
        type_filter = st.selectbox("Typ", ["Alle", "highlight", "micro", "brain"], key="ae_type")
    with col_f3:
        sort_by = st.selectbox("Sortierung", ["Deadline ↑", "Erstellt ↓", "Datum"], key="ae_sort")

    # Apply filters
    filtered = all_rows
    if show_filter == "Offen":
        filtered = [r for r in filtered if not r[9]]
    elif show_filter == "Erledigt":
        filtered = [r for r in filtered if r[9]]
    if type_filter != "Alle":
        filtered = [r for r in filtered if r[1] == type_filter]

    # Sort
    if sort_by == "Deadline ↑":
        filtered = sorted(filtered, key=lambda r: get_urgency(r[13])[1])
    elif sort_by == "Erstellt ↓":
        pass  # already ordered by id DESC
    elif sort_by == "Datum":
        filtered = sorted(filtered, key=lambda r: r[8], reverse=True)

    st.caption(f"{len(filtered)} Einträge")
    st.markdown("---")

    # Group by urgency when sorting by deadline
    if sort_by == "Deadline ↑":
        groups = [
            ("overdue",  "🔴 Überfällig"),
            ("today",    "🟠 Heute"),
            ("tomorrow", "🟡 Morgen"),
            ("soon",     "🟢 Bald (2–3 Tage)"),
            ("later",    "📅 Später"),
            ("none",     "📋 Kein Termin"),
        ]
        for g_key, g_label in groups:
            group_rows = [r for r in filtered if get_urgency(r[13])[0] == g_key]
            if not group_rows:
                continue
            st.markdown(f"#### {g_label}")
            for r in group_rows:
                _render_entry_card(r)
    else:
        for r in filtered:
            _render_entry_card(r)


def _render_entry_card(r):
    eid, etype, content, tags, priority, estimate, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at, deadline = r
    urg_level, urg_days, urg_label, urg_class = get_urgency(deadline)

    card_cls = (urg_class + " urg-done") if done else urg_class
    type_label = TYPE_LABELS.get(etype, etype)
    dl_badge = f'<span class="dl-badge">{urg_label}</span>' if urg_label else ""
    done_badge = '<span class="dl-badge" style="color:#4ade80">✅ Erledigt</span>' if done else ""

    st.markdown(
        f'<div class="{card_cls}">'
        f'<span style="font-size:12px;opacity:.6;text-transform:uppercase;letter-spacing:.5px">'
        f'{entry_date} · {type_label}</span>{dl_badge}{done_badge}<br>'
        f'<strong style="font-size:16px">{content}</strong>'
        + (f'<br><small style="opacity:.55">🏷️ {tags}</small>' if tags else "")
        + (f'<br><small style="opacity:.55">⏱️ ~{estimate} min</small>' if estimate else "")
        + (f'<br><small style="opacity:.55">⭐ {points} Punkte</small>' if done and points else "")
        + '</div>', unsafe_allow_html=True
    )

    if not done:
        c1, c2, c3, _ = st.columns([0.12, 0.18, 0.18, 0.52])
        with c1:
            if st.checkbox("✓", value=False, key=f"ae_chk_{eid}", label_visibility="collapsed"):
                elapsed = 0
                if started_at:
                    try:
                        sa = datetime.fromisoformat(started_at)
                        elapsed = int((datetime.utcnow() - sa).total_seconds())
                    except Exception:
                        pass
                toggle_done(eid, True, elapsed_seconds=elapsed,
                            points=compute_points(elapsed, estimate))
                st.rerun()
        with c2:
            btn_label = "Stop & ✓" if started_at else "Start"
            if st.button(btn_label, key=f"ae_startstop_{eid}"):
                if started_at:
                    elapsed = 0
                    try:
                        sa = datetime.fromisoformat(started_at)
                        elapsed = int((datetime.utcnow() - sa).total_seconds())
                    except Exception:
                        pass
                    toggle_done(eid, True, elapsed_seconds=elapsed,
                                points=compute_points(elapsed, estimate))
                else:
                    start_task(eid)
                st.rerun()
    else:
        c1, _ = st.columns([0.12, 0.88])
        with c1:
            if st.checkbox("✓", value=True, key=f"ae_chk_{eid}", label_visibility="collapsed"):
                pass
            else:
                toggle_done(eid, False, elapsed_seconds=0)
                st.rerun()


def render_statistics_page():
    st.title("📊 Deine Kaizen-Statistiken")
    stats = get_analytics_stats()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ Erledigt", stats['completed'])
    col2.metric("📝 Total", stats['total'])
    col3.metric("⏱️ Minuten", stats['total_minutes'])
    rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
    col4.metric("📈 Erfolgsquote", f"{rate:.1f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Aufgaben nach Typ")
        if stats['type_stats']:
            df = pd.DataFrame(stats['type_stats'], columns=['Type', 'Count', 'Avg_Sec', 'Total_Sec'])
            fig = px.pie(df, values='Count', names='Type',
                         color_discrete_sequence=['#00d4ff', '#ff6b6b', '#ffd93d'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Keine Daten")
    with col2:
        st.subheader("Ø Dauer pro Typ (Min)")
        if stats['type_stats']:
            df = pd.DataFrame(stats['type_stats'], columns=['Type', 'Count', 'Avg_Sec', 'Total_Sec'])
            df['Avg_Min'] = df['Avg_Sec'] / 60
            fig = px.bar(df, x='Type', y='Avg_Min', color='Type',
                         color_discrete_sequence=['#00d4ff', '#ff6b6b', '#ffd93d'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Keine Daten")

    st.markdown("---")
    st.subheader("Täglicher Fortschritt (30 Tage)")
    if stats['daily_trend']:
        df = pd.DataFrame(stats['daily_trend'], columns=['Date', 'Count', 'Total_Sec'])
        df['Minutes'] = df['Total_Sec'] / 60
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Count'], mode='lines+markers',
                                  name='Aufgaben', line=dict(color='#00d4ff', width=3)))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Minutes'], mode='lines+markers',
                                  name='Minuten', line=dict(color='#ff6b6b', width=3),
                                  yaxis='y2'))
        fig.update_layout(hovermode='x unified',
                           yaxis=dict(title='Aufgaben'),
                           yaxis2=dict(title='Minuten', overlaying='y', side='right'),
                           template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Noch keine Daten")


# ========== MAIN ==========

def main():
    st.set_page_config(page_title="Kaizen — ADHS-optimiert", layout="wide")
    init_db()

    if 'page' not in st.session_state:
        st.session_state.page = 'Start'

    PAGES = ["Start", "Planen", "Tagesfokus", "Alle Einträge", "Statistiken"]
    if st.session_state.page not in PAGES:
        st.session_state.page = "Start"

    st.sidebar.title("Kaizen Navigation")
    page = st.sidebar.selectbox("Seite wählen", PAGES,
                                  index=PAGES.index(st.session_state.page))
    st.session_state.page = page

    if page == "Start":
        render_start_page()
    elif page == "Planen":
        render_planen_page()
    elif page == "Tagesfokus":
        render_tagesfokus_page()
    elif page == "Alle Einträge":
        render_alle_eintraege_page()
    elif page == "Statistiken":
        render_statistics_page()

    level, progress, goal = get_level_and_progress()
    st.sidebar.header(f"Score: {total_points()} pts — Level {level}")
    st.sidebar.progress(int(progress / goal * 100))

    st.sidebar.header("Quick Actions")
    with st.sidebar.expander("Punkte & Level"):
        pts_input = st.number_input("Punkte pro Aufgabe",
                                     value=int(get_setting('points_per_task') or POINTS_PER_TASK), min_value=1)
        lvl_input = st.number_input("Punkte pro Level",
                                     value=int(get_setting('level_step') or LEVEL_STEP), min_value=10)
        if st.button("Speichern"):
            set_setting('points_per_task', pts_input)
            set_setting('level_step', lvl_input)
            st.sidebar.success("Gespeichert.")
        if st.button("Zurücksetzen"):
            set_setting('points_per_task', POINTS_PER_TASK)
            set_setting('level_step', LEVEL_STEP)
            st.sidebar.success("Zurückgesetzt.")

    with st.sidebar.expander("Export / Sync"):
        if st.checkbox("GitHub Gist"):
            token = st.text_input("Token", type="password")
            gist_id = st.text_input("Gist ID (leer → neu)")
            if st.button("Exportieren"):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('SELECT id, entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, done, completed_at, elapsed_seconds, deadline FROM entries')
                allrows = c.fetchall()
                conn.close()
                payload = json.dumps([dict(id=r[0], type=r[1], content=r[2], tags=r[3],
                                            priority=r[4], estimate=r[5], points=r[6],
                                            created_at=r[7], entry_date=r[8], done=r[9],
                                            completed_at=r[10], elapsed_seconds=r[11],
                                            deadline=r[12]) for r in allrows], ensure_ascii=False)
                if token and gist_id:
                    status, _ = gist_save(token, gist_id, payload)
                    st.write(f"Status: {status}")
                elif token:
                    status, resp = gist_create(token, payload)
                    st.write("OK:", resp.get('html_url') if status == 201 else status)
                else:
                    st.download_button("Download JSON", data=payload,
                                        file_name=f"kaizen_{date.today().isoformat()}.json")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Daten")
    if st.sidebar.button("Beispieldaten einfügen"):
        insert_sample_data()
        st.sidebar.success("Eingefügt.")
    if st.sidebar.button("Beispieldaten löschen"):
        delete_sample_data()
        st.sidebar.success("Gelöscht.")
    with st.sidebar.expander("⚠️ Alle Daten löschen"):
        confirm = st.text_input("Gib DELETE ein")
        if st.button("Löschen") and confirm == "DELETE":
            delete_all_data()
            st.sidebar.success("Alle Daten gelöscht.")

    st.sidebar.markdown("---")
    st.sidebar.caption("Tipp: Daily Highlight = eine Priorität. Deadline = künstlicher Druck.")


if __name__ == '__main__':
    main()
