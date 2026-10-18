import sqlite3
import streamlit as st
from datetime import datetime
import pandas as pd
import urllib.request
import re

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

def fetch_random_posteritati():
    """Fetches a random poster dynamically from posteritati.com across their entire archive."""
    try:
        req = urllib.request.Request(
            "https://posteritati.com/random",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Match image CDN links across Posteritati's catalog
            img_match = re.search(r'https://posteritati\.com/posters/[^\s"\'<>]+\.(?:jpg|png|jpeg)', html, re.IGNORECASE)
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            
            poster_url = img_match.group(0) if img_match else None
            title_text = title_match.group(1).replace('- Posteritati', '').strip() if title_match else "Posteritati Archive"
            
            if poster_url:
                return title_text, poster_url
    except Exception:
        pass
    
    # Generic fallback if remote connection is restricted
    return "Posteritati Gallery Archive", "https://posteritati.com/posters/000/000/025/breathless-original-french-petite-movie-poster.jpg"

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

# Fetch random poster across Posteritati's entire database per session load
if "current_poster" not in st.session_state:
    st.session_state["current_poster"] = fetch_random_posteritati()

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")

# Display Dynamic Posteritati Banner
poster_title, poster_url = st.session_state["current_poster"]
st.image(poster_url, caption=f"Posteritati Archive: {poster_title}", use_column_width=True)
st.divider()

# --- Owner Authentication (Sidebar) ---
st.sidebar.divider()
st.sidebar.header("Owner Mode")

owner_password = "GODARD68"
entered_password = st.sidebar.text_input("Enter password to edit", type="password")
is_admin = (entered_password == owner_password)

if is_admin:
    st.sidebar.success("Owner mode unlocked.")

# --- Fetch Data ---
conn = sqlite3.connect(DB_NAME)
df = pd.read_sql_query("SELECT * FROM screenings ORDER BY screening_date, screening_time", conn)
conn.close()

if not df.empty:
    # --- Sidebar Filtering Controls ---
    st.sidebar.header("Filter & View")
    
    all_films = ["All"] + sorted(df["title"].dropna().unique().tolist())
    selected_film = st.sidebar.selectbox("Filter by Film", all_films)

    all_dates = ["All"] + sorted(df["screening_date"].dropna().unique().tolist())
    selected_date = st.sidebar.selectbox("Filter by Date", all_dates)

    all_cinemas = ["All"] + sorted(df["cinema"].dropna().unique().tolist())
    selected_cinema = st.sidebar.selectbox("Filter by Cinema", all_cinemas)
    
    # Apply Overall Filters
    filtered_df = df.copy()
    if selected_film != "All":
        filtered_df = filtered_df[filtered_df["title"] == selected_film]
    if selected_date != "All":
        filtered_df = filtered_df[filtered_df["screening_date"] == selected_date]
    if selected_cinema != "All":
        filtered_df = filtered_df[filtered_df["cinema"] == selected_cinema]

    st.sidebar.divider()
    st.sidebar.header("Grouping & Sorting")
    
    primary_group = st.sidebar.selectbox("Group by", ["Date", "Film", "Cinema"], index=0)
    
    if primary_group == "Date":
        sort_options = ["Cinema", "Film", "Time"]
        default_sort_index = 0
    elif primary_group == "Film":
        sort_options = ["Date", "Cinema"]
        default_sort_index = 0
    else:
        sort_options = ["Date", "Film"]
        default_sort_index = 0
        
    secondary_sort = st.sidebar.selectbox("Sort within group by", sort_options, index=default_sort_index)

    # --- Display Grouped & Sorted Screenings ---
    st.subheader(f"Screenings Grouped by {primary_group}")
    
    group_col_map = {"Date": "screening_date", "Film": "title", "Cinema": "cinema"}
    g_col = group_col_map[primary_group]
    
    unique_groups = sorted(filtered_df[g_col].dropna().unique())
    
    if unique_groups:
        for g_val in unique_groups:
            if primary_group == "Date":
                try:
                    dt_obj = datetime.strptime(g_val, "%Y-%m-%d")
                    header_str = dt_obj.strftime("%A, %d %B")
                except ValueError:
                    header_str = g_val
            else:
                header_str = g_val

            st.markdown(f"### {header_str}")
            group_screenings = filtered_df[filtered_df[g_col] == g_val].copy()

            # Display synopsis under header only when grouping by Film
            if primary_group == "Film" and not group_screenings.empty:
                first_row = group_screenings.iloc[0]
                synopsis_text = first_row.get("synopsis", "")
                if synopsis_text:
                    st.info(synopsis_text)
            
            sort_col_map = {
                "Time": "screening_time", 
                "Cinema": "cinema", 
                "Film": "title", 
                "Date": "screening_date"
            }
            s_col = sort_col_map[secondary_sort]
            group_screenings = group_screenings.sort_values(by=s_col)

            for _, row in group_screenings.iterrows():
                is_private_item = bool(row.get("private", 0))
                is_starred_item = (row.get("starred", 0) == 1)

                if is_private_item and not is_admin:
                    with st.container():
                        st.markdown("*[Private schedule]*")
                        st.divider()
                    continue

                with st.container():
                    col1, col2, col3 = st.columns([4, 2, 2])

                    raw_title = f"★ {row['title']}" if is_starred_item else row['title']
                    if is_private_item and is_admin:
                        raw_title = f"[PRIVATE] {raw_title}"

                    # Title & Link Column
                    with col1:
                        if is_starred_item:
                            if row.get("url"):
                                st.markdown(f'<span class="starred-red"><a href="{row["url"]}" target="_blank">{raw_title}</a></span>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<span class="starred-red">{raw_title}</span>', unsafe_allow_html=True)
                        else:
                            if row.get("url"):
                                st.markdown(f"**[{raw_title}]({row['url']})**")
                            else:
                                st.markdown(f"**{raw_title}**")

                    # Cinema Column
                    with col2:
                        cinema_val = str(row['cinema']) if row['cinema'] else ''
                        if is_starred_item:
                            st.markdown(f'<span class="starred-red">{cinema_val}</span>', unsafe_allow_html=True)
                        else:
                            st.write(cinema_val)

                    # Time Column
                    with col3:
                        time_val = format_time_str(row['screening_time'])
                        if row.get("end_time"):
                            time_val += f" - {format_time_str(row['end_time'])}"
                        
                        if is_starred_item:
                            st.markdown(f'<span class="starred-red">{time_val}</span>', unsafe_allow_html=True)
                        else:
                            st.write(time_val)
                    
                    # Tags & Notes Row
                    tag_parts = []
                    if is_starred_item:
                        tag_parts.append("Starred / Priority Selection")
                    if row.get("specialty_format"):
                        tag_parts.append(row['specialty_format'])
                    if row.get("presentation"):
                        tag_parts.append(row['presentation'])
                    if row.get("notes"):
                        tag_parts.append(row['notes'])
                    
                    if tag_parts:
                        full_tag_str = " • ".join(tag_parts)
                        if is_starred_item:
                            st.markdown(f'<span class="starred-red">{full_tag_str}</span>', unsafe_allow_html=True)
                        else:
                            st.caption(full_tag_str)

                    # Owner Actions (Edit / Delete)
                    if is_admin:
                        action_spacer, action_edit, action_del = st.columns([6, 1, 1])
                        with action_edit:
                            edit_key = f"editing_{row['id']}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = False
                            
                            if st.button("Edit", key=f"btn_edit_{row['id']}"):
                                st.session_state[edit_key] = not st.session_state[edit_key]
                        with action_del:
                            if st.button("Delete", key=f"del_{row['id']}"):
                                conn = sqlite3.connect(DB_NAME)
                                c = conn.cursor()
                                c.execute("DELETE FROM screenings WHERE id = ?", (row['id'],))
                                conn.commit()
                                conn.close()
                                st.rerun()

                        # Owner Edit Box
                        if st.session_state.get(f"editing_{row['id']}", False):
                            with st.container():
                                st.markdown("---")
                                col_t1,
