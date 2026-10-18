import sqlite3
import streamlit as st
from datetime import datetime
import urllib.parse

# Function to parse an ICS text string
def parse_ics(ics_content):
    event_data = {
        "title": "Unknown Film",
        "cinema": "Paris Cinema",
        "screening_date": datetime.today().strftime("%Y-%m-%d"),
        "screening_time": "20:00",
        "end_time": "",
        "url": ""
    }
    
    lines = ics_content.splitlines()
    for line in lines:
        if line.startswith("SUMMARY:"):
            event_data["title"] = line.replace("SUMMARY:", "").strip()
        elif line.startswith("LOCATION:"):
            event_data["cinema"] = line.replace("LOCATION:", "").strip()
        elif line.startswith("DTSTART:"):
            dt_str = line.replace("DTSTART:", "").strip()
            # Parse format like 20231024T171500Z
            try:
                dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%SZ")
                event_data["screening_date"] = dt.strftime("%Y-%m-%d")
                event_data["screening_time"] = dt.strftime("%H:%M")
            except ValueError:
                pass
        elif line.startswith("DTEND:"):
            dt_str = line.replace("DTEND:", "").strip()
            try:
                dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%SZ")
                event_data["end_time"] = dt.strftime("%H:%M")
            except ValueError:
                pass
        elif line.startswith("URL:"):
            event_data["url"] = line.replace("URL:", "").strip()
            
    return event_data

# Streamlit Sidebar UI for ICS upload
st.sidebar.divider()
st.sidebar.header("📅 Import Filmorama ICS")
uploaded_ics = st.sidebar.file_uploader("Upload screening .ics file", type=["ics"])

if uploaded_ics is not None:
    ics_text = uploaded_ics.getvalue().decode("utf-8")
    parsed = parse_ics(ics_text)
    
    st.sidebar.write(f"**Title:** {parsed['title']}")
    st.sidebar.write(f"**Cinema:** {parsed['cinema']}")
    st.sidebar.write(f"**Time:** {parsed['screening_time']} - {parsed['end_time']}")
    
    if st.sidebar.button("Save to Dashboard"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            INSERT INTO screenings (title, cinema, screening_date, screening_time, end_time, format, status, url, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            parsed["title"], 
            parsed["cinema"], 
            parsed["screening_date"], 
            parsed["screening_time"], 
            parsed["end_time"], 
            "VOST", 
            "Scheduled", 
            parsed["url"], 
            "ICS Import"
        ))
        conn.commit()
        conn.close()
        st.sidebar.success("Saved successfully!")
        st.rerun()
