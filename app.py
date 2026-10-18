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
            notes TEXT,
            poster_url TEXT,
            specialty_format TEXT,
            presentation TEXT
        )
    ''')
    # Safe migrations if table already existed without these columns
    for col, col_type in [
        ("poster_url", "TEXT"), 
        ("notes", "TEXT"), 
        ("specialty_format", "TEXT"), 
        ("presentation", "TEXT")
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
        INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes, poster_url, specialty_format, presentation) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ""
    ))
    conn.commit()
    conn.close()

    st.query_params.clear()
    st.success(f"Successfully added: **{in_title}** at **{in_cinema}** ({in_time} - {in_end_time})")

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")

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

    # --- Owner Authentication (Sidebar) ---
    st.sidebar.divider()
    st.sidebar.header("Owner Mode")
    
    owner_password = "GODARD68"
    entered_password = st.sidebar.text_input("Enter password to edit", type="password")
    is_admin = (entered_password == owner_password)

    if is_admin:
        st.sidebar.success("Owner mode unlocked.")

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
            
            sort_col_map = {
                "Time": "screening_time", 
                "Cinema": "cinema", 
                "Film": "title", 
                "Date": "screening_date"
            }
            s_col = sort_col_map[secondary_sort]
            group_screenings = group_screenings.sort_values(by=s_col)

            for _, row in group_screenings.iterrows():
                with st.container():
                    if is_admin:
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    else:
                        col1, col2, col3 = st.columns([3, 2, 2])

                    with col1:
                        if row["url"]:
                            st.markdown(f"**[{row['title']}]({row['url']})**")
                        else:
                            st.markdown(f"**{row['title']}**")
                    with col2:
                        st.text(row['cinema'])
                    with col3:
                        time_str = f"{row['screening_time']}"
                        if row["end_time"]:
                            time_str += f" - {row['end_time']}"
                        st.text(time_str)
                    
                    if is_admin:
                        with col4:
                            if st.button("Delete", key=f"del_{row['id']}"):
                                conn = sqlite3.connect(DB_NAME)
                                c = conn.cursor()
                                c.execute("DELETE FROM screenings WHERE id = ?", (row['id'],))
                                conn.commit()
                                conn.close()
                                st.rerun()

                    # Display saved formatting/presentation tags cleanly for public viewers
                    if not is_admin:
                        tag_parts = []
                        if row.get("specialty_format"):
                            tag_parts.append(row['specialty_format'])
                        if row.get("presentation"):
                            tag_parts.append(row['presentation'])
                        if row.get("notes"):
                            tag_parts.append(row['notes'])
                        if tag_parts:
                            st.caption(" • ".join(tag_parts))

                    # Owner Edit Controls for Specialty Format, Presentation & Notes
                    if is_admin:
                        with st.expander("Edit Screening Details & Notes", expanded=False):
                            # Specialty Format Selection
                            format_options = ["None", "16mm", "35mm", "70mm", "3D", "IMAX", "4DX", "Other"]
                            current_fmt = row.get("specialty_format", "")
                            
                            base_fmt = current_fmt if current_fmt in format_options[1:] else ("Other" if current_fmt else "None")
                            fmt_index = format_options.index(base_fmt) if base_fmt in format_options else 0
                            
                            selected_fmt = st.selectbox("Specialty Format", format_options, index=fmt_index, key=f"fmt_sel_{row['id']}")
                            
                            final_fmt = ""
                            if selected_fmt == "Other":
                                custom_fmt = st.text_input("Specify Format", value=current_fmt if current_fmt not in format_options else "", key=f"fmt_custom_{row['id']}")
                                final_fmt = custom_fmt
                            elif selected_fmt != "None":
                                final_fmt = selected_fmt

                            # Presentation Selection
                            pres_options = ["None", "Director", "Cast", "Crew", "Cinéclub", "Masterclass", "Open Air", "Cinéconcert", "Other"]
                            current_pres = row.get("presentation", "")
                            
                            base_pres = current_pres if current_pres in pres_options[1:] else ("Other" if current_pres else "None")
                            pres_index = pres_options.index(base_pres) if base_pres in pres_options else 0
                            
                            selected_pres = st.selectbox("Presentation / Event Type", pres_options, index=pres_index, key=f"pres_sel_{row['id']}")
                            
                            final_pres = ""
                            if selected_pres == "Other":
                                custom_pres = st.text_input("Specify Presentation Details", value=current_pres if current_pres not in pres_options else "", key=f"pres_custom_{row['id']}")
                                final_pres = custom_pres
                            elif selected_pres != "None":
                                final_pres = selected_pres

                            # General Notes
                            current_notes = row["notes"] if row["notes"] is not None else ""
                            new_notes = st.text_input("Additional Notes", value=current_notes, key=f"notes_{row['id']}")

                            # Save changes button for this item
                            if st.button("Save Changes", key=f"save_{row['id']}"):
                                conn = sqlite3.connect(DB_NAME)
                                c = conn.cursor()
                                c.execute("""
                                    UPDATE screenings 
                                    SET specialty_format = ?, presentation = ?, notes = ? 
                                    WHERE id = ?
                                """, (final_fmt, final_pres, new_notes, row['id']))
                                conn.commit()
                                conn.close()
                                st.success("Updated!")
                                st.rerun()

            st.divider()
    else:
        st.info("No screenings match your current filters.")

    # Full data table view option (Only visible to owner)
    if is_admin:
        with st.expander("View Raw Table & Management"):
            st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("No screenings saved yet. Use your Filmorama bookmarklet to add screenings.")
