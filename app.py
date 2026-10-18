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

# Global style override for red starred links and details
st.markdown("""
    <style>
    .starred-title, .starred-title a {
        color: #dc2626 !important;
        text-decoration: underline;
        font-weight: bold;
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
    # Safe migrations if table already existed without these columns
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
    in_synopsis = query_params.get("synopsis", "")  # Captures synopsis passed from bookmarklet

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
        in_synopsis
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
    
    # Overall Filters
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

    # Grouping & Secondary Sorting Options
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

                # Public placeholder for private screenings
                if is_private_item and not is_admin:
                    with st.container():
                        st.markdown("*[Private schedule]*")
                        st.divider()
                    continue

                with st.container():
                    # Main screening info row
                    col1, col2, col3 = st.columns([4, 2, 2])

                    with col1:
                        raw_title = f"★ {row['title']}" if is_starred_item else row['title']
                        if is_private_item and is_admin:
                            raw_title = f"[PRIVATE] {raw_title}"

                        if is_starred_item:
                            if row["url"]:
                                html_title = f'<span class="starred-title"><a href="{row["url"]}" target="_blank">{raw_title}</a></span>'
                            else:
                                html_title = f'<span class="starred-title">{raw_title}</span>'
                            st.markdown(html_title, unsafe_allow_html=True)
                        else:
                            if row["url"]:
                                st.markdown(f"**[{raw_title}]({row['url']})**")
                            else:
                                st.markdown(f"**{raw_title}**")

                    with col2:
                        cinema_text = row['cinema']
                        if is_starred_item:
                            st.markdown(f":red[{cinema_text}]")
                        else:
                            st.text(cinema_text)

                    with col3:
                        time_str = f"{row['screening_time']}"
                        if row["end_time"]:
                            time_str += f" - {row['end_time']}"
                        
                        if is_starred_item:
                            st.markdown(f":red[{time_str}]")
                        else:
                            st.text(time_str)
                    
                    # Display saved formatting/presentation tags cleanly
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
                            st.markdown(f":red[**{full_tag_str}**]")
                        else:
                            st.caption(full_tag_str)

                    # Owner Action Row right-justified with tight button placement
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

                        # Owner Edit Form (Toggled by the Edit button)
                        if st.session_state.get(f"editing_{row['id']}", False):
                            with st.container():
                                st.markdown("---")
                                
                                # Star & Private Toggles
                                col_t1, col_t2 = st.columns(2)
                                with col_t1:
                                    current_starred = bool(row.get("starred", 0))
                                    new_starred = st.checkbox("Star this screening (Priority)", value=current_starred, key=f"star_chk_{row['id']}")
                                with col_t2:
                                    current_private = bool(row.get("private", 0))
                                    new_private = st.checkbox("Hide from public view", value=current_private, key=f"priv_chk_{row['id']}")

                                # Film Synopsis input
                                current_synopsis = row.get("synopsis", "") if row.get("synopsis") is not None else ""
