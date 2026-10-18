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

    st.query_params.clear()
    st.success(f"✅ Automatically added: **{in_title}** at **{in_cinema}** ({in_time} - {in_end_time})")

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Your personal curated screening schedule.")

# --- Fetch Data ---
conn = sqlite3.connect(DB_NAME)
df = pd.read_sql_query("SELECT * FROM screenings ORDER BY screening_date, screening_time", conn)
conn.close()

if not df.empty:
    # --- Sidebar Filtering & Sorting Controls ---
    st.sidebar.header("Filter & Sort")
    
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

    # Sorting option within dates
    st.sidebar.divider()
    st.sidebar.header("Sorting within Dates")
    sort_option = st.sidebar.selectbox("Sort screenings by", ["Time", "Film", "Cinema"])

    # --- Display Separated by Date ---
    st.subheader("Screenings by Date")
    
    unique_dates = sorted(filtered_df["screening_date"].dropna().unique())
    
    if unique_dates:
        for d in unique_dates:
            # Parse YYYY-MM-DD into "Day of week, Date Month" (e.g., Monday, 19 October)
            try:
                dt_obj = datetime.strptime(d, "%Y-%m-%d")
                formatted_date_str = dt_obj.strftime("%A, %d %B")
            except ValueError:
                formatted_date_str = d

            st.markdown(f"### {formatted_date_str}")
            day_screenings = filtered_df[filtered_df["screening_date"] == d].copy()
            
            # Apply intra-date sorting
            if sort_option == "Film":
                day_screenings = day_screenings.sort_values(by="title")
            elif sort_option == "Cinema":
                day_screenings = day_screenings.sort_values(by="cinema")
            else:  # Time
                day_screenings = day_screenings.sort_values(by="screening_time")

            for _, row in day_screenings.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        if row["url"]:
                            st.markdown(f"**[{row['title']}]({row['url']})**")
                        else:
                            st.markdown(f"**{row['title']}**")
                    with col2:
                        st.text(f"📍 {row['cinema']}")
                    with col3:
                        time_str = f"{row['screening_time']}"
                        if row["end_time"]:
                            time_str += f" - {row['end_time']}"
                        st.text(time_str)
                    with col4:
                        if st.button("🗑️", key=f"del_{row['id']}"):
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("DELETE FROM screenings WHERE id = ?", (row['id'],))
                            conn.commit()
                            conn.close()
                            st.rerun()
            st.divider()
    else:
        st.info("No screenings match your current filters.")

    # Full data table view option
    with st.expander("View Raw Table & Management"):
        st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("No screenings saved yet. Use your Filmorama bookmarklet to add screenings.")
