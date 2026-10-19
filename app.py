from datetime import datetime
import pandas as pd
import requests
import streamlit as st

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Paris Film Radar", page_icon="🎬", layout="centered"
)

st.title("🎬 Paris Film Radar")
st.caption("Minimalist screening tracker powered by JSONBin")

# --- 2. JSONBin Configuration ---
try:
  API_KEY = st.secrets["JSONBIN_API_KEY"]
  BIN_ID = st.secrets["JSONBIN_BIN_ID"]
except Exception:
  st.error(
      "Missing JSONBin secrets! Please check your Streamlit Cloud Secrets"
      " configuration."
  )
  st.stop()

HEADERS = {"Content-Type": "application/json", "X-Master-Key": API_KEY}


# --- 3. Load & Save Data ---
@st.cache_data(ttl=0)
def load_data():
  try:
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
      record = response.json().get("record", [])
      if not record or not isinstance(record, list):
        return pd.DataFrame(
            columns=["Title", "Cinema", "Date", "Time", "Notes", "URL"]
        )
      return pd.DataFrame(record)
    else:
      st.error(f"Failed to load data from JSONBin: {response.text}")
      return pd.DataFrame(
          columns=["Title", "Cinema", "Date", "Time", "Notes", "URL"]
      )
  except Exception as e:
    st.error(f"Connection error: {e}")
    return pd.DataFrame(columns=["Title", "Cinema", "Date", "Time", "Notes", "URL"])


def save_data(df):
  try:
    # Convert dataframe to a list of dicts for JSON storage
    data_list = df.to_dict(orient="records")
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
    response = requests.put(url, json=data_list, headers=HEADERS)

    if response.status_code == 200:
      st.cache_data.clear()
      st.success("Changes saved successfully to cloud!")
    else:
      st.error(f"Error saving to cloud: {response.text}")
  except Exception as e:
    st.error(f"Save error: {e}")


df = load_data()

# --- 4. Bookmarklet / Query Param Ingestion ---
query_params = st.query_params
if "title" in query_params or "url" in query_params:
  st.info("📥 Incoming screening detected from bookmarklet!")
  incoming_title = query_params.get("title", "")
  incoming_cinema = query_params.get("cinema", "")
  incoming_url = query_params.get("url", "")
  incoming_notes = query_params.get("notes", "")

  with st.form("bookmarklet_review_form"):
    st.subheader("Review & Save Ingested Screening")
    b_title = st.text_input("Film Title", value=incoming_title)
    b_cinema = st.text_input("Cinema Name", value=incoming_cinema)
    b_date = st.date_input("Date", value=datetime.today())
    b_time = st.text_input("Time (e.g., 20:00)")
    b_notes = st.text_area("Notes", value=incoming_notes)
    b_url = st.text_input("Source URL", value=incoming_url)

    if st.form_submit_button("Confirm & Add to Radar"):
      new_row = pd.DataFrame([{
          "Title": b_title,
          "Cinema": b_cinema,
          "Date": str(b_date),
          "Time": b_time,
          "Notes": b_notes,
          "URL": b_url,
      }])
      df = pd.concat([df, new_row], ignore_index=True)
      save_data(df)
      st.query_params.clear()
      st.rerun()

# --- 5. Main UI & Screening Management ---
st.subheader("Upcoming Screenings")

if df.empty:
  st.info(
      "No screenings tracked yet. Add one below or via your iPhone bookmarklet!"
  )
else:
  edited_df = st.data_editor(
      df,
      num_rows="dynamic",
      use_container_width=True,
      key="screening_editor",
  )

  col1, col2 = st.columns([1, 4])
  with col1:
    if st.button("💾 Save Changes", type="primary"):
      save_data(edited_df)
  with col2:
    if st.button("🔄 Refresh Data"):
      st.cache_data.clear()
      st.rerun()

# --- 6. Quick Add Form Expander ---
with st.expander("➕ Add New Screening Manually"):
  with st.form("add_screening_form"):
    m_title = st.text_input("Film Title")
    m_cinema = st.text_input("Cinema Name")
    m_date = st.date_input("Date", value=datetime.today())
    m_time = st.text_input("Time (e.g., 20:00)")
    m_notes = st.text_area("Notes")
    m_url = st.text_input("Source URL")

    if st.form_submit_button("Add Screening"):
      new_row = pd.DataFrame([{
          "Title": m_title,
          "Cinema": m_cinema,
          "Date": str(m_date),
          "Time": m_time,
          "Notes": m_notes,
          "URL": m_url,
      }])
      df = pd.concat([df, new_row], ignore_index=True)
      save_data(df)
      st.rerun()
