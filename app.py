import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

DB_NAME = "paris_film_radar.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS screenings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        cinema TEXT NOT NULL,
        screening_date TEXT,
        screening_time TEXT,
        end_time TEXT,
        format TEXT,
        status TEXT,
        url TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

is_popup = "popup" in st.query_params

# Handle incoming parameters from bookmarklet
if "title" in st.query_params:
    t = st.query_params.get("title")
    cin = st.query_params.get("cinema", "Paris Cinema")
    d = st.query_params.get("date", "")
    tm = st.query_params.get("time", "")
    et = st.query_params.get("end_time", "")
    u = st.query_params.get("url", "")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM screenings WHERE title = ? AND cinema = ? AND screening_date = ? AND screening_time = ?", (t, cin, d, tm))
    if not c.fetchone():
        c.execute("INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (t, cin, d, tm, et, "VOST", "Scheduled", u, "Bookmarklet Import"))
        conn.commit()
    conn.close()
    
    st.session_state["last_imported_url"] = u
    st.session_state["last_imported_title"] = t
    st.query_params.clear()

# If opened via popup, show a nice confirmation and auto-close the window via JavaScript
if is_popup:
    st.success("🎬 Successfully saved to Film Radar!")
    st.markdown("<p style='text-align: center; color: gray;'>This window will close automatically...</p>", unsafe_allow_html=True)
    st.markdown('<script>setTimeout(function() { window.close(); }, 1500);</script>', unsafe_allow_html=True)
    st.stop()

def load_screenings():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query("SELECT * FROM screenings", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

st.set_page_config(page_title="Paris Film Screening Radar", page_icon="🎟️", layout="wide")
st.title("🎬 Paris Film Screening Radar")

if "last_imported_title" in st.session_state:
    st.success(f"Successfully saved **{st.session_state['last_imported_title']}**!")
    if st.session_state.get("last_imported_url"):
        st.markdown(f"👉 [Click here to return to your cinema page]({st.session_state['last_imported_url']})")
    if st.button("Clear Notification"):
        del st.session_state["last_imported_title"]
        st.rerun()

if st.button("🔄 Refresh"):
    st.rerun()

st.sidebar.header("➕ Add Screening Manually")
with st.sidebar.form("manual_add_form"):
    m_title = st.text_input("Film Title")
    m_cinema = st.text_input("Cinema Name", value="Paris Cinema")
    m_date = st.date_input("Date", value=datetime.today())
    m_time = st.text_input("Start Time (e.g. 20:00)", value="20:00")
    m_end_time = st.text_input("End Time (optional, e.g. 22:00)", value="")
    submitted = st.form_submit_button("Add to Database")
    if submitted:
        if m_title:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            date_str = m_date.strftime("%Y-%m-%d")
            c.execute("SELECT id FROM screenings WHERE title = ? AND cinema = ? AND screening_date = ? AND screening_time = ?", (m_title, m_cinema, date_str, m_time))
            if not c.fetchone():
                c.execute("INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (m_title, m_cinema, date_str, m_time, m_end_time, "VOST", "Scheduled", "", "Manual Entry"))
                conn.commit()
                st.success(f"Added \"{m_title}\"!")
                st.rerun()
            else:
                st.warning("This exact screening already exists!")
            conn.close()
        else:
            st.error("Please enter a film title.")

st.sidebar.divider()
st.sidebar.header("Display Controls")
group_by = st.sidebar.selectbox("Group By", ["Date", "Film"])
sort_by = st.sidebar.selectbox("Sort Within Group By", ["Showtime", "Film", "Cinema", "Date"])

sort_col_map = {
    "Showtime": "screening_time",
    "Film": "title",
    "Cinema": "cinema",
    "Date": "screening_date"
}
secondary_sort = sort_col_map.get(sort_by, "screening_time")

df = load_screenings()
if df.empty:
    st.info("Database is empty. Click your bookmarklet or add a screening manually using the sidebar!")
else:
    if group_by == "Date":
        df = df.sort_values(by=["screening_date", secondary_sort])
        for date_str, group in df.groupby("screening_date"):
            header_label = date_str
            try:
                dt_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
                header_label = dt_obj.strftime("%A, %B %d, %Y")
            except Exception:
                pass
            st.subheader(f"{header_label}")
            for _, row in group.iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1: st.markdown(f"**{row['title']}**")
                with c2: 
                    end_val = row.get("end_time", "")
                    end_str = f" - {end_val}" if pd.notna(end_val) and end_val else ""
                    info_text = f"📍 {row['cinema']} | 🕒 {row['screening_time']}{end_str}"
                    st.text(info_text)
                with c3: st.markdown(f"🔵 *{row.get('status', 'Scheduled')}*")
                with c4:
                    if st.button("Delete", key=f"del_{row['id']}"):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("DELETE FROM screenings WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.rerun()
            st.divider()
    else:
        df = df.sort_values(by=["title", secondary_sort])
        for film_title, group in df.groupby("title"):
            st.subheader(f"{film_title}")
            for _, row in group.iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1: st.markdown(f"📍 **{row['cinema']}**")
                with c2: 
                    end_val = row.get("end_time", "")
                    end_str = f" - {end_val}" if pd.notna(end_val) and end_val else ""
                    st.text(f"📅 {row['screening_date']} | 🕒 {row['screening_time']}{end_str}")
                with c3: st.markdown(f"🔵 *{row.get('status', 'Scheduled')}*")
                with c4:
                    if st.button("Delete", key=f"del_{row['id']}"):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("DELETE FROM screenings WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.rerun()
            st.divider()
