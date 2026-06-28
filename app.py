import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from datetime import datetime, date, timedelta
import time
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

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


def add_entry(entry_type, content, tags=None, priority=0, estimate=0, points=0, entry_date=None):
    now = datetime.utcnow().isoformat()
    entry_date = entry_date or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO entries (entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, last_modified)
                 VALUES (?,?,?,?,?,?,?,?,?)''',
              (entry_type, content, tags or "", priority, estimate, points, now, entry_date, now))
    conn.commit()
    conn.close()


def get_today_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at
                 FROM entries WHERE entry_date=? ORDER BY id DESC''', (date.today().isoformat(),))
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at
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


def clear_start(entry_id):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE entries SET started_at=NULL, last_modified=? WHERE id=?', (now, entry_id))
    conn.commit()
    conn.close()


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

# ========== ANALYTICS & PREDICTION ==========
def get_average_duration_by_type(entry_type):
    """Schätze Duration basierend auf Task-Typ Durchschnitt"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT AVG(elapsed_seconds) FROM entries 
        WHERE entry_type = ? AND done = 1 AND elapsed_seconds > 0
    """, (entry_type,))
    result = c.fetchone()[0]
    conn.close()
    return int(result / 60) if result else None

def get_average_duration_by_tags(tags_str):
    """Schätze Duration basierend auf Tags (Komma-separiert)"""
    if not tags_str:
        return None
    tags_list = [t.strip() for t in tags_str.split(',')]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    durations = []
    for tag in tags_list:
        c.execute("""
            SELECT AVG(elapsed_seconds) FROM entries 
            WHERE tags LIKE ? AND done = 1 AND elapsed_seconds > 0
        """, (f'%{tag}%',))
        result = c.fetchone()[0]
        if result:
            durations.append(int(result / 60))
    
    conn.close()
    return int(np.mean(durations)) if durations else None

def predict_duration(entry_type, tags=None, estimate_minutes=None):
    """
    Intelligente Duration-Vorhersage basierend auf:
    1. Historische Durchschnitte nach Type
    2. Tags-basierte Muster
    3. Benutzereingabe (estimate)
    """
    if estimate_minutes and estimate_minutes > 0:
        return estimate_minutes  # User-Input hat Priorität
    
    tag_avg = get_average_duration_by_tags(tags) if tags else None
    type_avg = get_average_duration_by_type(entry_type)
    
    predictions = [p for p in [tag_avg, type_avg] if p is not None]
    
    if predictions:
        return int(np.mean(predictions))
    
    # Fallback Defaults nach Type
    defaults = {"brain": 5, "highlight": 25, "micro": 2}
    return defaults.get(entry_type, 10)

def get_analytics_stats():
    """Sammle alle Analytics-Daten für Dashboard"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Total stats
    c.execute("SELECT COUNT(*) FROM entries WHERE done = 1")
    completed_tasks = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM entries")
    total_tasks = c.fetchone()[0]
    
    c.execute("SELECT SUM(elapsed_seconds) FROM entries WHERE done = 1")
    total_time = c.fetchone()[0] or 0
    
    # Tasks by type
    c.execute("""
        SELECT entry_type, COUNT(*), AVG(elapsed_seconds), SUM(elapsed_seconds)
        FROM entries WHERE done = 1
        GROUP BY entry_type
    """)
    type_stats = c.fetchall()
    
    # Tasks by tag
    c.execute("""
        SELECT tags, COUNT(*), AVG(elapsed_seconds)
        FROM entries WHERE done = 1 AND tags IS NOT NULL AND tags != ''
        GROUP BY tags
    """)
    tag_stats = c.fetchall()
    
    # Daily completion trend (last 30 days)
    c.execute("""
        SELECT DATE(completed_at) as day, COUNT(*), SUM(elapsed_seconds)
        FROM entries WHERE done = 1 AND completed_at IS NOT NULL
        AND completed_at > datetime('now', '-30 days')
        GROUP BY DATE(completed_at)
        ORDER BY day
    """)
    daily_trend = c.fetchall()
    
    conn.close()
    
    return {
        "completed": completed_tasks,
        "total": total_tasks,
        "total_minutes": int(total_time / 60),
        "type_stats": type_stats,
        "tag_stats": tag_stats,
        "daily_trend": daily_trend
    }

# ========== LOFI START PAGE ==========
def render_lofi_start_page():
    """Coole Lofi Rain Japan Startseite"""
    # CSS für Lofi Vibe
    lofi_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kdam+Thmor+Pro&display=swap');
    
    /* Rain Animation */
    @keyframes rain {
        0% { transform: translateY(-100vh) translateX(0px); opacity: 1; }
        100% { transform: translateY(100vh) translateX(0px); opacity: 0; }
    }
    
    @keyframes fade_in {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .lofi-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
        position: relative;
        overflow: hidden;
        padding: 60px 40px;
        border-radius: 20px;
        margin: 20px 0;
        text-align: center;
    }
    
    .rain {
        position: absolute;
        width: 2px;
        height: 10px;
        background: rgba(255, 255, 255, 0.3);
        left: calc(var(--i) * 1%);
        animation: rain 1s linear infinite;
        animation-delay: calc(var(--i) * 0.1s);
    }
    
    .lofi-content {
        position: relative;
        z-index: 10;
        animation: fade_in 1s ease-out;
    }
    
    .lofi-title {
        font-size: 3.5em;
        font-weight: bold;
        color: #00d4ff;
        margin: 20px 0;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        font-family: 'Kdam Thmor Pro', cursive;
        letter-spacing: 2px;
    }
    
    .lofi-subtitle {
        font-size: 1.3em;
        color: #e0e0e0;
        margin: 15px 0;
        font-style: italic;
    }
    
    .lofi-button {
        background: linear-gradient(135deg, #00d4ff, #0099cc);
        border: none;
        padding: 18px 50px;
        font-size: 1.2em;
        color: #1a1a2e;
        border-radius: 50px;
        cursor: pointer;
        font-weight: bold;
        margin-top: 30px;
        transition: all 0.3s ease;
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.4);
        animation: pulse 2s ease-in-out infinite;
    }
    
    .lofi-button:hover {
        transform: translateY(-3px);
        box-shadow: 0 0 50px rgba(0, 212, 255, 0.8);
    }
    
    .lofi-stats {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 20px;
        margin-top: 40px;
    }
    
    .lofi-stat-box {
        background: rgba(0, 212, 255, 0.1);
        border: 2px solid rgba(0, 212, 255, 0.3);
        padding: 20px;
        border-radius: 15px;
        color: #00d4ff;
    }
    
    .lofi-stat-number {
        font-size: 2.5em;
        font-weight: bold;
    }
    
    .lofi-stat-label {
        font-size: 0.9em;
        color: #e0e0e0;
        margin-top: 10px;
    }
    </style>
    """
    
    st.markdown(lofi_css, unsafe_allow_html=True)
    
    # HTML mit Rain Animation
    stats = get_analytics_stats()
    
    html_content = f"""
    <div class="lofi-container">
        {"".join([f'<div class="rain" style="--i: {i};"></div>' for i in range(50)])}
        
        <div class="lofi-content">
            <div class="lofi-title">🌧️ KAIZEN</div>
            <div class="lofi-subtitle">Start deinen perfekten Tag • Eins nach dem anderen</div>
            
            <div class="lofi-stats">
                <div class="lofi-stat-box">
                    <div class="lofi-stat-number">{stats['completed']}</div>
                    <div class="lofi-stat-label">Aufgaben erledigt</div>
                </div>
                <div class="lofi-stat-box">
                    <div class="lofi-stat-number">{stats['total_minutes']}</div>
                    <div class="lofi-stat-label">Minuten investiert</div>
                </div>
                <div class="lofi-stat-box">
                    <div class="lofi-stat-number">{total_points()}</div>
                    <div class="lofi-stat-label">Punkte gesammelt</div>
                </div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Button zum Starten (normaler Streamlit-Button darunter)
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Tag starten", use_container_width=True, key="lofi_start_btn"):
            st.session_state.page = "Heute"
            st.rerun()
    
    st.write("")
    st.markdown("---")
    st.write("💡 **Was dich erwartet:** Brain Dump → Daily Highlight → Micro-Commitment")

# ========== STATISTICS DASHBOARD ==========
def render_statistics_page():
    """Visuelles Analytics Dashboard mit Grafiken"""
    st.title("📊 Deine Kaizen-Statistiken")
    
    stats = get_analytics_stats()
    
    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ Erledigt", stats['completed'])
    with col2:
        st.metric("📝 Total", stats['total'])
    with col3:
        st.metric("⏱️ Minuten", stats['total_minutes'])
    with col4:
        completion_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        st.metric("📈 Erfolgsquote", f"{completion_rate:.1f}%")
    
    st.markdown("---")
    
    # Grafiken Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Aufgaben nach Typ")
        if stats['type_stats']:
            type_data = pd.DataFrame(stats['type_stats'], columns=['Type', 'Count', 'Avg_Seconds', 'Total_Seconds'])
            fig = px.pie(type_data, values='Count', names='Type', 
                        color_discrete_sequence=['#00d4ff', '#ff6b6b', '#ffd93d'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Keine Daten vorhanden")
    
    with col2:
        st.subheader("Durchschnittliche Dauer pro Typ (Minuten)")
        if stats['type_stats']:
            type_data = pd.DataFrame(stats['type_stats'], columns=['Type', 'Count', 'Avg_Seconds', 'Total_Seconds'])
            type_data['Avg_Minutes'] = type_data['Avg_Seconds'] / 60
            fig = px.bar(type_data, x='Type', y='Avg_Minutes', 
                        color='Type', color_discrete_sequence=['#00d4ff', '#ff6b6b', '#ffd93d'],
                        labels={'Avg_Minutes': 'Minuten', 'Type': 'Aufgabentyp'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Keine Daten vorhanden")
    
    st.markdown("---")
    
    # Daily Trend
    st.subheader("Täglicher Fortschritt (letzte 30 Tage)")
    if stats['daily_trend']:
        daily_data = pd.DataFrame(stats['daily_trend'], columns=['Date', 'Count', 'Total_Seconds'])
        daily_data['Minutes'] = daily_data['Total_Seconds'] / 60
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_data['Date'], y=daily_data['Count'],
            mode='lines+markers', name='Aufgaben',
            line=dict(color='#00d4ff', width=3),
            marker=dict(size=8)
        ))
        fig.add_trace(go.Scatter(
            x=daily_data['Date'], y=daily_data['Minutes'],
            mode='lines+markers', name='Minuten',
            line=dict(color='#ff6b6b', width=3),
            marker=dict(size=8),
            yaxis='y2'
        ))
        
        fig.update_layout(
            hovermode='x unified',
            yaxis=dict(title='Aufgaben'),
            yaxis2=dict(title='Minuten', overlaying='y', side='right'),
            template='plotly_dark'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Noch keine Daten vorhanden")
    
    st.markdown("---")
    
    # Tags Analytics
    st.subheader("Top Tags")
    if stats['tag_stats']:
        tag_list = []
        for tags, count, avg_seconds in stats['tag_stats']:
            if tags:
                for tag in str(tags).split(','):
                    tag_list.append({'Tag': tag.strip(), 'Count': count, 'Avg_Minutes': avg_seconds / 60 if avg_seconds else 0})
        
        if tag_list:
            tag_data = pd.DataFrame(tag_list).groupby('Tag').agg({'Count': 'sum', 'Avg_Minutes': 'mean'}).reset_index()
            tag_data = tag_data.sort_values('Count', ascending=False).head(10)
            
            fig = px.bar(tag_data, x='Tag', y='Count', 
                        color='Avg_Minutes', color_continuous_scale='viridis',
                        labels={'Count': 'Anzahl', 'Avg_Minutes': 'Ø Minuten'})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Noch keine Tag-Daten")


def render_start_page():
    """Alias für Lofi Start Page"""
    render_lofi_start_page()


def main():
    st.set_page_config(page_title="Kaizen — ADHS-optimiert", layout="wide")

    init_db()

    if 'page' not in st.session_state:
        st.session_state.page = 'Start'

    st.sidebar.title("Kaizen Navigation")
    pages = ["Start", "Heute", "Alle Einträge", "Statistiken"]
    page = st.sidebar.selectbox("Seite wählen", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    st.session_state.page = page

    if page == "Start":
        render_start_page()
    
    elif page == "Heute":
        st.title("Kaizen — Tageslog (ADHS-freundlich)")
        st.markdown("""
        Einfache 3‑Schritte-Tageseinheit: Brain Dump, Daily Highlight, Micro-Commitment.
        Ziel: den Kopf leeren, eine einzige Priorität setzen und mit einem winzigen Schritt Momentum erzeugen.
        """)

        # Brain Dump
        st.header("Brain Dump — Alles raus")
        with st.form("brain_form"):
            brain_text = st.text_area("Schreib alles auf, was dir gerade im Kopf ist", height=120)
            tags = st.text_input("Tags (Komma-getrennt)")
            submitted = st.form_submit_button("Hinzufügen")
            if submitted and brain_text.strip():
                add_entry("brain", brain_text.strip(), tags=tags, estimate=predict_duration("brain", tags=tags))
                st.success("Gespeichert — gut gemacht.")

        # Daily Highlight
        st.header("Daily Highlight — EINE Aufgabe")
        today_entries = get_today_entries()
        brain_texts = [r[2] for r in today_entries if r[1]=="brain"]
        with st.form("highlight_form"):
            choice = st.selectbox("Aus Brain Dump wählen (optional)", [""] + brain_texts)
            highlight = st.text_input("Oder tippe eine neue Highlight-Aufgabe", value="" if not choice else choice)
            tags = st.text_input("Tags (optional)")
            
            # Smart Duration Prediction
            predicted_duration = predict_duration("highlight", tags=tags if tags else None)
            st.info(f"🤖 Basierend auf deiner Historie: ~{predicted_duration} Minuten")
            
            estimate = st.number_input("Geschätzte Minuten", min_value=0, step=5, value=predicted_duration)
            date_input = st.date_input("Fälligkeit / Eintragsdatum", value=date.today())
            set_hl = st.form_submit_button("Als Daily Highlight setzen")
            if set_hl and highlight.strip():
                add_entry("highlight", highlight.strip(), tags=tags, estimate=estimate, entry_date=date_input.isoformat())
                st.success("Daily Highlight gesetzt — fokussiere dich auf diese Aufgabe.")

        # Micro-Commitment
        st.header("Micro-Commitment — 2 Minuten")
        with st.form("micro_form"):
            micro = st.text_input("2-Minuten-Aktion (z.B. E‑Mail beantworten)")
            tags = st.text_input("Tags (optional)")
            date_input = st.date_input("Fälligkeit / Eintragsdatum", value=date.today())
            start = st.form_submit_button("Start 2-Minuten")
            if start and micro.strip():
                add_entry("micro", micro.strip(), tags=tags, estimate=predict_duration("micro", tags=tags), entry_date=date_input.isoformat())
                st.info("Micro-Commitment gespeichert. Starte den Timer unten.")

        if st.button("Timer 2 Minuten anzeigen/starten"):
            placeholder = st.empty()
            total = 120
            for i in range(total, -1, -1):
                mins, secs = divmod(i, 60)
                placeholder.markdown(f"**Verbleibend:** {mins:02d}:{secs:02d}")
                time.sleep(1)
            placeholder.markdown("**Fertig!** Gut gemacht. Markiere dein Micro-Commitment als erledigt.")

        st.header("Heute — Einträge")
        rows = get_today_entries()
        if not rows:
            st.write("Noch nichts für heute — fang mit einem Brain Dump an.")
        else:
            for r in rows:
                eid, etype, content, tags, priority, estimate, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at = r
                cols = st.columns([0.55, 0.15, 0.15, 0.15])
                with cols[0]:
                    st.write(f"**{etype}** — {content}")
                    if tags:
                        st.caption(f"Tags: {tags}")
                    if estimate:
                        st.caption(f"Schätzung: {estimate} min")
                    st.caption(f"Datum: {entry_date}")
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
                        st.rerun()
                    stop_btn = st.button("Stop", key=f"stop_{eid}")
                    if stop_btn:
                        elapsed = 0
                        if started_at:
                            try:
                                sa = datetime.fromisoformat(started_at)
                                elapsed = int((datetime.utcnow() - sa).total_seconds())
                            except Exception:
                                elapsed = 0
                        pts = compute_points(elapsed, estimate)
                        toggle_done(eid, True, elapsed_seconds=elapsed, points=pts)
                        st.rerun()
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
                        st.rerun()
    
    elif page == "Alle Einträge":
        st.title("Kaizen — Alle Einträge")
        st.header("Sammelübersicht")
        all_rows = get_all_entries()
        if not all_rows:
            st.write("Noch keine Einträge vorhanden.")
        else:
            for r in all_rows:
                eid, etype, content, tags, priority, estimate, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at = r
                cols = st.columns([0.55, 0.15, 0.15, 0.15])
                with cols[0]:
                    st.write(f"**{entry_date} | {etype}** — {content}")
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
                    if not done:
                        start_btn = st.button("Start", key=f"all_start_{eid}")
                        if start_btn:
                            start_task(eid)
                            st.rerun()
                        stop_btn = st.button("Stop", key=f"all_stop_{eid}")
                        if stop_btn:
                            elapsed = 0
                            if started_at:
                                try:
                                    sa = datetime.fromisoformat(started_at)
                                    elapsed = int((datetime.utcnow() - sa).total_seconds())
                                except Exception:
                                    elapsed = 0
                            pts = compute_points(elapsed, estimate)
                            toggle_done(eid, True, elapsed_seconds=elapsed, points=pts)
                            st.rerun()
                with cols[3]:
                    new = st.checkbox("Erledigt", value=bool(done), key=f"all_done_{eid}")
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
                        st.rerun()
    
    elif page == "Statistiken":
        render_statistics_page()

    # Scoring and level (Sidebar - on all pages)
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
