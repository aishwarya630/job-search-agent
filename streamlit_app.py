import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SECURITY & CONFIG
st.set_page_config(page_title="Job CRM", layout="wide")

# Fetch PIN and URL from Secrets (Safe from GitHub prying eyes)
PIN = st.secrets["ACCESS_PIN"]
SHEET_URL = st.secrets["GSHEETS_URL"]

# --- PIN GATE ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Private Job CRM")
    user_input = st.text_input("Enter Access PIN", type="password")
    if st.button("Unlock Dashboard"):
        if user_input == PIN:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid PIN")
    st.stop()

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Read the 'Jobs' worksheet
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Jobs", ttl="1m")
except Exception as e:
    st.error(f"Connection Error: Ensure the Sheet URL is correct and shared. {e}")
    st.stop()

st.title("💼 Professional Job Tracker")

if not df.empty:
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters")
    
    # Fill missing status with 'Interested'
    df['status'] = df['status'].fillna('Interested')
    
    status_options = ["Interested", "Applied", "Interviewing", "Rejected", "Ghosted", "Offer"]
    selected_status = st.sidebar.multiselect("Filter by Status", status_options, default=["Interested", "Applied", "Interviewing"])
    
    # Filter the Data
    filtered_df = df[df['status'].isin(selected_status)]

    # --- THE INTERACTIVE EDITOR ---
    st.subheader("Manage Your Applications")
    st.info("💡 Edit cells directly and click 'Save Changes' below.")
    
    updated_df = st.data_editor(
        filtered_df,
        column_config={
            "apply_url": st.column_config.LinkColumn("Link"),
            "status": st.column_config.SelectboxColumn("Status", options=status_options),
            "applied_date": st.column_config.DateColumn("Date Applied"),
            "score": st.column_config.NumberColumn("Score", format="%d ⭐"),
        },
        width="stretch", # Replaced use_container_width per your logs
        hide_index=True
    )

    if st.button("💾 Save Changes to Google Sheets"):
        # This pushes updates back to the Google Sheet
        conn.update(spreadsheet=SHEET_URL, worksheet="Jobs", data=updated_df)
        st.success("CRM Updated Permanently!")
        st.balloons()
else:
    st.warning("Sheet found but it is empty. Check your headers!")
