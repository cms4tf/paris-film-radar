import sqlite3
import streamlit as st
from datetime import datetime
import pandas as pd
import random

# Page Configuration
st.set_page_config(
    page_title="Paris Film Radar", 
    page_icon="🎬", 
    layout="wide"
)

# Global CSS override for red starred items
st.markdown("""
    <style>
    .starred-red, 
    .starred-red a, 
    .starred-red span {
        color: #dc2626 !important;
        font-weight: bold;
    }
    .starred-red a {
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "screenings.db"

def format_time_str(t_str):
    """Safely formats screening times to HH:MM format (e.g., 21-30 or 21h30 -> 21:30)"""
    if not t_str:
        return ""
    clean_t = str(t_str).strip().replace('-', ':').replace('h', ':').replace('H', ':')
    parts = clean_t.split(':')
    if len(parts) >= 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    return clean_t

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
            notes TEXT,
            poster_url TEXT,
            specialty_format TEXT,
            presentation TEXT,
            starred INTEGER DEFAULT 0,
            private INTEGER DEFAULT 0,
            synopsis TEXT
        )
    ''')
    for col, col_type in [
        ("poster_url", "TEXT"), 
        ("notes", "TEXT"), 
        ("specialty_format", "TEXT"), 
        ("presentation", "TEXT"),
        ("starred", "INTEGER DEFAULT 0"),
        ("private", "INTEGER DEFAULT 0"),
        ("synopsis", "TEXT")
    ]:
        try:
            c.execute(f"ALTER TABLE screenings ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
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
    in_time = format_time_str(query_params.get("time", "20:00"))
    in_end_time = format_time_str(query_params.get("end_time", ""))
    in_poster = query_params.get("poster", "")
    in_url = query_params.get("url", "")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes, poster_url, specialty_format, presentation, starred, private, synopsis) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        in_title, 
        in_cinema, 
        in_date, 
        in_time, 
        in_end_time, 
        "VOST", 
        "Scheduled", 
        in_url, 
        "",
        in_poster,
        "",
        "",
        0,
        0,
        ""
    ))
    conn.commit()
    conn.close()

    st.query_params.clear()
    st.success(f"Successfully added: **{in_title}** at **{in_cinema}** ({in_time})")

# --- Posteritati Image Database Pool ---
POSTERITATI_POSTERS = [
    ("À bout de souffle (1960)", "https://posteritati.com/posters/000/000/025/breathless-original-french-petite-movie-poster.jpg"),
    ("Pierrot le fou (1965)", "https://posteritati.com/posters/000/000/025/pierrot-le-fou-original-french-grande-movie-poster.jpg"),
    ("Bande à part (1964)", "https://posteritati.com/posters/000/000/025/bande-a-part-original-french-grande-movie-poster.jpg"),
    ("Alphaville (1965)", "https://posteritati.com/posters/000/000/025/alphaville-original-french-grande-movie-poster.jpg"),
    ("Les Quatre Cents Coups (1959)", "https://posteritati.com/posters/000/000/025/the-400-blows-original-french-grande-movie-poster.jpg"),
    ("Vivre sa vie (1962)", "https://posteritati.com/posters/000/000/025/vivre-sa-vie-original-french-grande-movie-poster.jpg")
]

# Randomize once per session load
if "current_poster" not in st.session_state:
    st.session_state["current_poster"] = random.choice(POSTERITATI_POSTERS)

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")

# Display Posteritati Banner
poster_title, poster_url = st.session_state["current_poster"]
st.image(poster_url, caption=f"Posteritati Archive: {poster_title}", use_column_width=True)
st.divider()

# --- Owner Authentication (Sidebar) ---
st.sidebar.divider()
st.sidebar.header
