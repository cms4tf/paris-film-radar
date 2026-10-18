import sqlite3
import streamlit as st
from datetime import datetime
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Paris Film Radar", 
    page_icon="🎬", 
    layout="wide"
)

DB_NAME = "screenings.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS screenings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            cinema TEXT,
            screening_date TEXT,
            screening_time TEXT,
            end_time TEXT,
            format TEXT,
            status TEXT,
            url TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on load
init_db()

# --- Auto-save incoming bookmarklet data ---
query_params = st.query_params
if "title" in query_params and "cinema" in query_params:
    in_title = query_params.get("title")
    in_cinema = query_params.get("cinema")
    in_date = query_params.get("date", datetime.today().strftime("%Y-%m-%d"))
    in_time = query_params.get("time", "20:00")
    in_end_time = query_params.get("end_time", "")
    in_url = query_params.get("url", "")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        in_title, 
        in_cinema, 
        in_date, 
        in_time, 
        in_end_time, 
        "VOST", 
        "Scheduled", 
        in_url, 
        "Bookmarklet Import"
    ))
    conn.commit()
    conn.close()

    # Clear query params so it doesn't duplicate on page refresh
    st.query_params.clear()
    
    # Success banner
    st.success(f"✅ Automatically added: **{in_title}** at **{in_cinema}** ({in_time} - {in_end_time})")

# --- Main Dashboard UI ---
st.title("🎬 Paris Film Radar Dashboard")
st.write("Click your Filmorama bookmarklet on any screening page to instantly save it here.")

# Fetch and display screenings
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()
c.execute("SELECT id, title, cinema, screening_date, screening_time, end_time, format, status, url FROM screenings ORDER BY screening_date, screening_time")
rows = c.fetchall()
conn.close()

if rows:
    st.subheader("Your Saved Screenings")
    df = pd.DataFrame(rows, columns=["ID", "Title", "Cinema", "Date", "Start", "End", "Format", "Status", "URL"])
    st.dataframe(df, use_container_width=True)
    
    # Management section to delete entries if needed
    with st.expander("⚙️ Manage / Delete Screenings"):
        del_id = st.number_input("Enter ID of screening to delete", min_value=0, step=1)
        if st.button("Delete Screening"):
            if del_id > 0:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("DELETE FROM screenings WHERE id = ?", (del_id,))
                conn.commit()
                conn.close()
                st.success(f"Deleted screening ID {del_id}")
                st.rerun()
else:
    st.info("No screenings saved yet. Click your bookmarklet on Filmorama to add your first one!")
