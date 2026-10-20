from datetime import datetime
import json
import sqlite3
import pandas as pd
import requests
import streamlit as st

# Page Configuration
st.set_page_config(page_title="Paris Film Radar", page_icon="", layout="wide")

# Global CSS override for red starred items
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

DB_NAME = "screenings.db"
OWNER_PASSWORD = "GODARD68"

# --- GitHub Gist Configuration ---
try:
  GIST_TOKEN = st.secrets["GIST_TOKEN"]
  GIST_ID = st.secrets["GIST_ID"]
  GIST_FILENAME = st.secrets.get("GIST_FILENAME", "screenings.json")
except Exception:
  st.error("Missing GitHub Gist secrets in Streamlit Cloud Secrets configuration.")
  st.stop()

GIST_HEADERS = {
    "Authorization": f"token {GIST_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def push_local_to_gist():
  """Pushes local SQLite database up to the GitHub Gist safely"""
  try:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM screenings")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()

    payload = {
        "files": {GIST_FILENAME: {"content": json.dumps(rows, indent=2)}}
    }
    url = f"https://api.github.com/gists/{GIST_ID}"
    requests.patch(url, json=payload, headers=GIST_HEADERS, timeout=5)
  except Exception:
    pass


def pull_gist_to_local():
  """Pulls remote Gist data down to local SQLite on startup without losing data"""
  try:
    url = f"https://api.github.com/gists/{GIST_ID}"
    response = requests.get(url, headers=GIST_HEADERS, timeout=5)
    if response.status_code == 200:
      gist_data = response.json()
      files = gist_data.get("files", {})
      if GIST_FILENAME in files:
        content = files[GIST_FILENAME].get("content", "[]")
        records = json.loads(content)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM screenings")
        local_count = c.fetchone()[0]

        if records and isinstance(records, list):
          c.execute("DELETE FROM screenings")
          for r in records:
            c.execute(
                """
                        INSERT OR REPLACE INTO screenings (id, title, cinema, screening_date, screening_time, end_time, format, status, url, notes, poster_url, specialty_format, presentation, starred, private, synopsis)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                (
                    r.get("id"),
                    r.get("title"),
                    r.get("cinema"),
                    r.get("screening_date"),
                    r.get("screening_time"),
                    r.get("end_time"),
                    r.get("format", "VOST"),
                    r.get("status", "Scheduled"),
                    r.get("url"),
                    r.get("notes"),
                    r.get("poster_url"),
                    r.get("specialty_format"),
                    r.get("presentation"),
                    r.get("starred", 0),
                    r.get("private", 0),
                    r.get("synopsis"),
                ),
            )
          conn.commit()
        elif not records and local_count > 0:
          conn.close()
          push_local_to_gist()
          return
        conn.close()
  except Exception:
    pass


def format_time_str(t_str):
  """Safely formats screening times to HH:MM format (e.g., 21-30 or 21h30 -> 21:30)"""
  if not t_str:
    return ""
  clean_t = (
      str(t_str).strip().replace("-", ":").replace("h", ":").replace("H", ":")
  )
  parts = clean_t.split(":")
  if len(parts) >= 2:
    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
  return clean_t


def init_db():
  conn = sqlite3.connect(DB_NAME)
  c = conn.cursor()
  c.execute("""
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
    """)
  for col, col_type in [
      ("poster_url", "TEXT"),
      ("notes", "TEXT"),
      ("specialty_format", "TEXT"),
      ("presentation", "TEXT"),
      ("starred", "INTEGER DEFAULT 0"),
      ("private", "INTEGER DEFAULT 0"),
      ("synopsis", "TEXT"),
  ]:
    try:
      c.execute(f"ALTER TABLE screenings ADD COLUMN {col} {col_type}")
    except sqlite3.OperationalError:
      pass
  conn.commit()
  conn.close()


# Initialize database and sync storage on load
init_db()
pull_gist_to_local()

# --- Password-Protected Bookmarklet Data Ingestion ---
query_params = st.query_params
if "title" in query_params and "cinema" in query_params:
  provided_key = query_params.get("key", "")
  if provided_key == OWNER_PASSWORD:
    in_title = query_params.get("title")
    in_cinema = query_params.get("cinema")
    in_date = query_params.get(
        "date", datetime.today().strftime("%Y-%m-%d")
    )
    in_time = format_time_str(query_params.get("time", "20:00"))
    in_end_time = format_time_str(query_params.get("end_time", ""))
    in_poster = query_params.get("poster", "")
    in_url = query_params.get("url", "")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes, poster_url, specialty_format, presentation, starred, private, synopsis) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
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
            "",
        ),
    )
    conn.commit()
    conn.close()

    # Sync to Gist
    push_local_to_gist()

    st.query_params.clear()
    st.success(
        f"Successfully added: **{in_title}** at **{in_cinema}** ({in_time})"
    )
  else:
    st.query_params.clear()
    st.error(
        "Unauthorized: Valid owner key required to add screenings via URL."
    )

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")
st.divider()

# --- Owner Authentication (Sidebar) ---
st.sidebar.divider()
st.sidebar.header("Owner Mode")

entered_password = st.sidebar.text_input("Enter password to edit", type="password")
is_admin = entered_password == OWNER_PASSWORD

if is_admin:
  st.sidebar.success("Owner mode unlocked.")

  # --- Owner-Only Manual Screening Creation Form ---
  with st.sidebar.expander(" Manually Add Screening"):
    with st.form("manual_add_form", clear_on_submit=True):
      add_title = st.text_input("Film Title*")
      add_cinema = st.text_input("Cinema Name*")
      add_date = st.date_input("Screening Date", datetime.today())
      add_time = st.text_input("Start Time (e.g., 20:30)", "20:00")
      add_end_time = st.text_input("End Time (optional)", "")
      add_url = st.text_input("Booking / Ticket URL", "")
      add_synopsis = st.text_area
