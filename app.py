import streamlit as st
from datetime import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection

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

OWNER_PASSWORD = "GODARD68"

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    """Reads all screenings from Google Sheets safely."""
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=[
                "id", "title", "cinema", "screening_date", "screening_time", 
                "end_time", "format", "status", "url", "notes", "poster_url", 
                "specialty_format", "presentation", "starred", "private", "synopsis"
            ])
        # Clean column types
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df["starred"] = pd.to_numeric(df["starred"], errors="coerce").fillna(0).astype(int)
        df["private"] = pd.to_numeric(df["private"], errors="coerce").fillna(0).astype(int)
        for c in df.columns:
            if c not in ["id", "starred", "private"]:
                df[c] = df[c].fillna("").astype(str)
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame()

def save_data(df):
    """Writes the updated dataframe back to Google Sheets."""
    conn.update(data=df)

def format_time_str(t_str):
    """Safely formats screening times to HH:MM format."""
    if not t_str:
        return ""
    clean_t = str(t_str).strip().replace('-', ':').replace('h', ':').replace('H', ':')
    parts = clean_t.split(':')
    if len(parts) >= 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    return clean_t

# Fetch data on run
df = get_data()

# --- Password-Protected Bookmarklet Data Ingestion ---
query_params = st.query_params
if "title" in query_params and "cinema" in query_params:
    provided_key = query_params.get("key", "")
    if provided_key == OWNER_PASSWORD:
        in_title = query_params.get("title")
        in_cinema = query_params.get("cinema")
        in_date = query_params.get("date", datetime.today().strftime("%Y-%m-%d"))
        in_time = format_time_str(query_params.get("time", "20:00"))
        in_end_time = format_time_str(query_params.get("end_time", ""))
        in_poster = query_params.get("poster", "")
        in_url = query_params.get("url", "")

        next_id = 1 if df.empty else df["id"].max() + 1
        new_row = {
            "id": next_id,
            "title": in_title,
            "cinema": in_cinema,
            "screening_date": in_date,
            "screening_time": in_time,
            "end_time": in_end_time,
            "format": "VOST",
            "status": "Scheduled",
            "url": in_url,
            "notes": "",
            "poster_url": in_poster,
            "specialty_format": "",
            "presentation": "",
            "starred": 0,
            "private": 0,
            "synopsis": ""
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)

        st.query_params.clear()
        st.success(f"Successfully added: **{in_title}** at **{in_cinema}** ({in_time})")
    else:
        st.query_params.clear()
        st.error("Unauthorized: Valid owner key required to add screenings via URL.")

# --- Dashboard Header ---
st.title("Paris Film Radar")
st.write("Corey's personal curated screening schedule.")
st.divider()

# --- Owner Authentication (Sidebar) ---
st.sidebar.divider()
st.sidebar.header("Owner Mode")

entered_password = st.sidebar.text_input("Enter password to edit", type="password")
is_admin = (entered_password == OWNER_PASSWORD)

if is_admin:
    st.sidebar.success("Owner mode unlocked.")
    
    # --- Owner-Only Manual Screening Creation Form ---
    with st.sidebar.expander("➕ Manually Add Screening"):
        with st.form("manual_add_form", clear_on_submit=True):
            add_title = st.text_input("Film Title*")
            add_cinema = st.text_input("Cinema Name*")
            add_date = st.date_input("Screening Date", datetime.today())
            add_time = st.text_input("Start Time (e.g., 20:30)", "20:00")
            add_end_time = st.text_input("End Time (optional)", "")
            add_url = st.text_input("Booking / Ticket URL", "")
            add_synopsis = st.text_area("Synopsis", "")
            
            all_fmt_options = ["16mm", "35mm", "70mm", "3D", "IMAX", "4DX"]
            add_fmts = st.multiselect("Specialty Formats", all_fmt_options)
            
            all_pres_options = ["Director", "Cast", "Crew", "Cinéclub", "Masterclass", "Open Air", "Cinéconcert", "Avant-Première"]
            add_pres = st.multiselect("Presentation / Event Types", all_pres_options)
            
            add_notes = st.text_input("Notes", "")
            add_starred = st.checkbox("Star this screening (Priority)")
            add_private = st.checkbox("Hide from public view")
            
            submit_add = st.form_submit_button("Save Screening")
            
            if submit_add:
                if not add_title.strip() or not add_cinema.strip():
                    st.error("Title and Cinema are required!")
                else:
                    formatted_time = format_time_str(add_time)
                    formatted_end_time = format_time_str(add_end_time)
                    fmt_str = ", ".join(add_fmts)
                    pres_str = ", ".join(add_pres)
                    date_str = add_date.strftime("%Y-%m-%d")

                    next_id = 1 if df.empty else int(df["id"].max()) + 1
                    new_row = {
                        "id": next_id,
                        "title": add_title.strip(),
                        "cinema": add_cinema.strip(),
                        "screening_date": date_str,
                        "screening_time": formatted_time,
                        "end_time": formatted_end_time,
                        "format": "VOST",
                        "status": "Scheduled",
                        "url": add_url.strip(),
                        "notes": add_notes.strip(),
                        "poster_url": "",
                        "specialty_format": fmt_str,
                        "presentation": pres_str,
                        "starred": 1 if add_starred else 0,
                        "private": 1 if add_private else 0,
                        "synopsis": add_synopsis.strip()
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)

                    st.success(f"Added **{add_title}**!")
                    st.rerun()

# --- Filter & Display ---
if not df.empty:
    st.sidebar.header("Filter & View")
    
    all_films = ["All"] + sorted([x for x in df["title"].unique() if x])
    selected_film = st.sidebar.selectbox("Filter by Film", all_films)

    all_dates = ["All"] + sorted([x for x in df["screening_date"].unique() if x])
    selected_date = st.sidebar.selectbox("Filter by Date", all_dates)

    all_cinemas = ["All"] + sorted([x for x in df["cinema"].unique() if x])
    selected_cinema = st.sidebar.selectbox("Filter by Cinema", all_cinemas)
    
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
    elif primary_group == "Film":
        sort_options = ["Date", "Cinema"]
    else:
        sort_options = ["Date", "Film"]
        
    secondary_sort = st.sidebar.selectbox("Sort within group by", sort_options, index=0)

    st.subheader(f"Screenings Grouped by {primary_group}")
    
    group_col_map = {"Date": "screening_date", "Film": "title", "Cinema": "cinema"}
    g_col = group_col_map[primary_group]
    unique_groups = sorted([x for x in filtered_df[g_col].unique() if x])
    
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

            st.markdown(f"<h3 style='text-align: center;'>{header_str}</h3>", unsafe_allow_html=True)
            group_screenings = filtered_df[filtered_df[g_col] == g_val].copy()

            if primary_group == "Film" and not group_screenings.empty:
                first_row = group_screenings.iloc[0]
                synopsis_text = first_row.get("synopsis", "")
                if synopsis_text:
                    st.info(synopsis_text)
            
            sort_col_map = {"Time": "screening_time", "Cinema": "cinema", "Film": "title", "Date": "screening_date"}
            group_screenings = group_screenings.sort_values(by=sort_col_map[secondary_sort])

            for _, row in group_screenings.iterrows():
                is_private_item = bool(row.get("private", 0))
                is_starred_item = (row.get("starred", 0) == 1)

                if is_private_item and not is_admin:
                    with st.container():
                        st.markdown("*[Private schedule]*")
                        st.divider()
                    continue

                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 2]) if primary_group != "Film" else st.columns([3, 3, 2])

                    if primary_group == "Film":
                        with col1:
                            display_cinema = f"{'★ ' if is_starred_item else ''}{row.get('cinema', '')}"
                            if is_starred_item:
                                st.markdown(f'<span class="starred-red">{display_cinema}</span>', unsafe_allow_html=True)
                            else:
                                st.write(display_cinema)
                        with col2:
                            dt_val = f"{row['screening_date']} @ {format_time_str(row['screening_time'])}"
                            if row.get("end_time"):
                                dt_val += f" - {format_time_str(row['end_time'])}"
                            if is_starred_item:
                                st.markdown(f'<span class="starred-red">{dt_val}</span>', unsafe_allow_html=True)
                            else:
                                st.write(dt_val)
                        with col3:
                            action_parts = []
                            if row.get("url"): action_parts.append(f"[Tickets ↗]({row['url']})")
                            if is_starred_item: action_parts.append("Starred")
                            if row.get("specialty_format"): action_parts.append(row['specialty_format'])
                            if row.get("presentation"): action_parts.append(row['presentation'])
                            if row.get("notes"): action_parts.append(row['notes'])
                            action_str = " • ".join(action_parts)
                            if is_starred_item:
                                st.markdown(f'<span class="starred-red">{action_str}</span>', unsafe_allow_html=True)
                            else:
                                st.markdown(action_str)
                    else:
                        raw_title = f"{'★ ' if is_starred_item else ''}{row['title']}"
                        if is_private_item and is_admin:
                            raw_title = f"[PRIVATE] {raw_title}"

                        with col1:
                            if row.get("url"):
                                if is_starred_item:
                                    st.markdown(f'<span class="starred-red"><a href="{row["url"]}" target="_blank">{raw_title}</a></span>', unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**[{raw_title}]({row['url']})**")
                            else:
                                if is_starred_item:
                                    st.markdown(f'<span class="starred-red">{raw_title}</span>', unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**{raw_title}**")
                            
                            tag_parts = []
                            if is_starred_item: tag_parts.append("Starred / Priority Selection")
                            if row.get("specialty_format"): tag_parts.append(row['specialty_format'])
                            if row.get("presentation"): tag_parts.append(row['presentation'])
                            if row.get("notes"): tag_parts.append(row['notes'])
                            if tag_parts:
                                full_tag_str = " • ".join(tag_parts)
                                if is_starred_item:
                                    st.markdown(f'<span class="starred-red" style="font-size: 0.85em;">{full_tag_str}</span>', unsafe_allow_html=True)
                                else:
                                    st.caption(full_tag_str)

                        with col2:
                            cinema_val = str(row['cinema']) if row['cinema'] else ''
                            if is_starred_item:
                                st.markdown(f'<span class="starred-red">{cinema_val}</span>', unsafe_allow_html=True)
                            else:
                                st.write(cinema_val)

                        with col3:
                            time_val = format_time_str(row['screening_time'])
                            if row.get("end_time"): time_val += f" - {format_time_str(row['end_time'])}"
                            if is_starred_item:
                                st.markdown(f'<span class="starred-red">{time_val}</span>', unsafe_allow_html=True)
                            else:
                                st.write(time_val)

                    # Owner Actions (Edit / Delete)
                    if is_admin:
                        _, action_edit, action_del = st.columns([6, 1, 1])
                        with action_edit:
                            edit_key = f"editing_{row['id']}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = False
                            if st.button("Edit", key=f"btn_edit_{row['id']}"):
                                st.session_state[edit_key] = not st.session_state[edit_key]
                        with action_del:
                            if st.button("Delete", key=f"del_{row['id']}"):
                                df = df[df["id"] != row["id"]]
                                save_data(df)
                                st.rerun()

                        if st.session_state.get(f"editing_{row['id']}", False):
                            with st.container():
                                st.markdown("---")
                                st.markdown(f"**Editing screening ID {row['id']}**")
                                edit_title = st.text_input("Film Title", value=row['title'], key=f"edit_title_{row['id']}")
                                edit_cinema = st.text_input("Cinema", value=row['cinema'], key=f"edit_cinema_{row['id']}")
                                try:
                                    default_dt = datetime.strptime(row['screening_date'], "%Y-%m-%d").date()
                                except ValueError:
                                    default_dt = datetime.today().date()
                                edit_date = st.date_input("Screening Date", value=default_dt, key=f"edit_date_{row['id']}")
                                
                                col_t1, col_t2 = st.columns(2)
                                with col_t1: edit_time = st.text_input("Start Time", value=row['screening_time'], key=f"edit_time_{row['id']}")
                                with col_t2: edit_end_time = st.text_input("End Time", value=row.get('end_time', '') or '', key=f"edit_endtime_{row['id']}")

                                edit_url = st.text_input("Booking / Ticket URL", value=row.get('url', '') or '', key=f"edit_url_{row['id']}")

                                col_s1, col_s2 = st.columns(2)
                                with col_s1: new_starred = st.checkbox("Star this screening", value=bool(row.get("starred", 0)), key=f"star_chk_{row['id']}")
                                with col_s2: new_private = st.checkbox("Hide from public view", value=bool(row.get("private", 0)), key=f"priv_chk_{row['id']}")

                                new_synopsis = st.text_area("Film Synopsis", value=row.get("synopsis", "") or "", key=f"synopsis_{row['id']}")
                                
                                all_fmt_options = ["16mm", "35mm", "70mm", "3D", "IMAX", "4DX"]
                                existing_fmt_list = [f.strip() for f in (row.get("specialty_format", "") or "").split(",") if f.strip()]
                                default_fmt_selected = [f for f in existing_fmt_list if f in all_fmt_options]
                                custom_fmt_initial = ", ".join([f for f in existing_fmt_list if f not in all_fmt_options])

                                selected_fmt_list = st.multiselect("Specialty Formats", all_fmt_options, default=default_fmt_selected, key=f"fmt_multi_{row['id']}")
                                custom_fmt_input = st.text_input("Or specify custom format(s)", value=custom_fmt_initial, key=f"fmt_custom_{row['id']}")

                                combined_fmts = selected_fmt_list.copy()
                                if custom_fmt_input.strip():
                                    combined_fmts.extend([c.strip() for c in custom_fmt_input.split(",") if c.strip()])
                                final_fmt = ", ".join(combined_fmts)

                                all_pres_options = ["Director", "Cast", "Crew", "Cinéclub", "Masterclass", "Open Air", "Cinéconcert", "Avant-Première"]
                                default_pres_list = [p.strip() for p in (row.get("presentation", "") or "").split(",") if p.strip() in all_pres_options]
                                selected_pres_list = st.multiselect("Presentation / Event Types", all_pres_options, default=default_pres_list, key=f"pres_multi_{row['id']}")
                                final_pres = ", ".join(selected_pres_list)

                                new_notes = st.text_input("Additional Notes", value=row.get("notes", "") or "", key=f"notes_{row['id']}")

                                if st.button("Save Changes", key=f"save_{row['id']}"):
                                    if not edit_title.strip() or not edit_cinema.strip():
                                        st.error("Title and Cinema cannot be empty!")
                                    else:
                                        idx = df[df["id"] == row["id"]].index[0]
                                        df.at[idx, "title"] = edit_title.strip()
                                        df.at[idx, "cinema"] = edit_cinema.strip()
                                        df.at[idx, "screening_date"] = edit_date.strftime("%Y-%m-%d")
                                        df.at[idx, "screening_time"] = format_time_str(edit_time)
                                        df.at[idx, "end_time"] = format_time_str(edit_end_time)
                                        df.at[idx, "url"] = edit_url.strip()
                                        df.at[idx, "specialty_format"] = final_fmt
                                        df.at[idx, "presentation"] = final_pres
                                        df.at[idx, "notes"] = new_notes.strip()
                                        df.at[idx, "starred"] = 1 if new_starred else 0
                                        df.at[idx, "private"] = 1 if new_private else 0
                                        df.at[idx, "synopsis"] = new_synopsis.strip()

                                        save_data(df)
                                        st.session_state[f"editing_{row['id']}"] = False
                                        st.success("Screening successfully updated!")
                                        st.rerun()
                                st.markdown("---")
            st.divider()
    else:
        st.info("No screenings match your current filters.")
else:
    st.info("No screenings saved yet. Use your bookmarklet or sidebar to add screenings.")
