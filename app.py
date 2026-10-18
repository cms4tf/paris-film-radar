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

# Global CSS override for red starred items (title, star, hyperlinks, hover)
st.markdown("""
    <style>
    .starred-red, 
    .starred-red a, 
    .starred-red span, 
    .starred-red p, 
    .starred-red div {
        color: #dc2626 !important;
        fill: #dc2626 !important;
    }
    .starred-red a {
        text-decoration: underline;
        font-weight: bold;
    }
    .starred-red a:hover {
        color: #b91c1c !important;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- Auto-save incoming bookmarklet data (Protected by Owner Password) ---
query_params = st.query_params
if "title" in query_params and "cinema" in query_params:
    in_title = query_params.get("title")
    in_cinema = query_params.get("cinema")
    in_date = query_params.get("date", datetime.today().strftime("%Y-%m-%d"))
    in_time = query_params.get("time", "20:00")
    in_end_time = query_params.get("end_time", "")
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
    st.success(f"Successfully added: **{in_title}** at **{in_cinema}** ({in_time} - {in_end_time})")

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")

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
    # --- Sidebar Filtering, Grouping & Sorting Controls ---
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

            # Display manual synopsis under header only when grouping by Film
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

                    # Title & Link formatting
                    raw_title = f"★ {row['title']}" if is_starred_item else row['title']
                    if is_private_item and is_admin:
                        raw_title = f"[PRIVATE] {raw_title}"

                    with col1:
                        if is_starred_item:
                            if row["url"]:
                                title_html = f'<div class="starred-red"><strong><a href="{row["url"]}" target="_blank">{raw_title}</a></strong></div>'
                            else:
                                title_html = f'<div class="starred-red"><strong>{raw_title}</strong></div>'
                            st.markdown(title_html, unsafe_allow_html=True)
                        else:
                            if row["url"]:
                                st.markdown(f"**[{raw_title}]({row['url']})**")
                            else:
                                st.markdown(f"**{raw_title}**")

                    # Cinema column
