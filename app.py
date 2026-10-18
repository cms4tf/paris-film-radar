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
    """Dynamically fetches a completely random poster from posteritati.com/random"""
    try:
        req = urllib.request.Request(
            "https://posteritati.com/random",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Extract Image URL
            img_match = re.search(r'https://posteritati\.com/posters/[^\s"\'<>]+\.(?:jpg|png|jpeg)', html, re.IGNORECASE)
            # Extract Film Title from <title> tag
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            
            poster_url = img_match.group(0) if img_match else None
            title_text = title_match.group(1).replace('- Posteritati', '').strip() if title_match else "Random Archive Poster"
            
            if poster_url:
                return title_text, poster_url
    except Exception:
        pass
    
    # Fallback if request times out or is blocked
    return "Breathless (1960)", "https://posteritati.com/posters/000/000/025/breathless-original-french-petite-movie-poster.jpg"

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

# Fetch completely random Posteritati poster on session load
if "current_poster" not in st.session_state:
    st.session_state["current_poster"] = fetch_random_posteritati()

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")

# Display Random Posteritati Banner
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
                                col_t1, col_t2 = st.columns(2)
                                with col_t1:
                                    current_starred = bool(row.get("starred", 0))
                                    new_starred = st.checkbox("Star this screening (Priority)", value=current_starred, key=f"star_chk_{row['id']}")
                                with col_t2:
                                    current_private = bool(row.get("private", 0))
                                    new_private = st.checkbox("Hide from public view", value=current_private, key=f"priv_chk_{row['id']}")

                                current_synopsis = row.get("synopsis", "") if row.get("synopsis") is not None else ""
                                new_synopsis = st.text_area("Film Synopsis", value=current_synopsis, key=f"synopsis_{row['id']}")

                                all_fmt_options = ["16mm", "35mm", "70mm", "3D", "IMAX", "4DX"]
                                current_fmt_str = row.get("specialty_format", "") if row.get("specialty_format") is not None else ""
                                
                                existing_fmt_list = [f.strip() for f in current_fmt_str.split(",") if f.strip()]
                                default_fmt_selected = [f for f in existing_fmt_list if f in all_fmt_options]
                                custom_fmt_initial = ", ".join([f for f in existing_fmt_list if f not in all_fmt_options])

                                selected_fmt_list = st.multiselect("Specialty Formats", all_fmt_options, default=default_fmt_selected, key=f"fmt_multi_{row['id']}")
                                custom_fmt_input = st.text_input("Or specify custom format(s)", value=custom_fmt_initial, key=f"fmt_custom_{row['id']}")

                                combined_fmts = selected_fmt_list.copy()
                                if custom_fmt_input.strip():
                                    combined_fmts.extend([c.strip() for c in custom_fmt_input.split(",") if c.strip()])
                                final_fmt = ", ".join(combined_fmts)

                                all_pres_options = ["Director", "Cast", "Crew", "Cinéclub", "Masterclass", "Open Air", "Cinéconcert", "Avant-Première"]
                                current_pres_str = row.get("presentation", "") if row.get("presentation") is not None else ""
                                default_pres_list = [p.strip() for p in current_pres_str.split(",") if p.strip() in all_pres_options]
                                
                                selected_pres_list = st.multiselect("Presentation / Event Types", all_pres_options, default=default_pres_list, key=f"pres_multi_{row['id']}")
                                final_pres = ", ".join(selected_pres_list)

                                current_notes = row["notes"] if row["notes"] is not None else ""
                                new_notes = st.text_input("Additional Notes", value=current_notes, key=f"notes_{row['id']}")

                                if st.button("Save Changes", key=f"save_{row['id']}"):
                                    conn = sqlite3.connect(DB_NAME)
                                    c = conn.cursor()
                                    c.execute("""
                                        UPDATE screenings 
                                        SET specialty_format = ?, presentation = ?, notes = ?, starred = ?, private = ?, synopsis = ? 
                                        WHERE id = ?
                                    """, (final_fmt, final_pres, new_notes, 1 if new_starred else 0, 1 if new_private else 0, new_synopsis, row['id']))
                                    conn.commit()
                                    conn.close()
                                    st.session_state[f"editing_{row['id']}"] = False
                                    st.success("Updated!")
                                    st.rerun()
                                st.markdown("---")

            st.divider()
    else:
        st.info("No screenings match your current filters.")

    if is_admin:
        with st.expander("View Raw Table & Management"):
            st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("No screenings saved yet. Use your Filmorama bookmarklet to add screenings.")
