import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SECURITY & CONFIG
st.set_page_config(page_title="Job CRM", layout="wide")
PIN = st.secrets["ACCESS_PIN"]

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
# This pulls live data from your spreadsheet
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl="1m") # Refresh data every minute
except Exception as e:
    st.error("Could not connect to Google Sheets. Check your URL in Secrets.")
    st.stop()

st.title("💼 Professional Job Tracker")

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")
if not df.empty:
    status_list = df['status'].unique().tolist()
    selected_status = st.sidebar.multiselect("Filter by Status", status_list, default=status_list)
    
    # Hide Columns
    all_cols = df.columns.tolist()
    visible_cols = st.sidebar.multiselect("Show Columns", all_cols, default=["title", "company", "status", "applied_date", "score"])

    # --- THE INTERACTIVE EDITOR ---
    # This is where you actually manage your jobs
    filtered_df = df[df['status'].isin(selected_status)]
    
    st.subheader("Edit Your Applications")
    st.info("Tip: Edit the 'Status' or 'Notes' below, then click the Save button.")
    
    updated_df = st.data_editor(
        filtered_df[visible_cols],
        column_config={
            "apply_url": st.column_config.LinkColumn("Job Link"),
            "status": st.column_config.SelectboxColumn(
                "Status", options=["Interested", "Applied", "Interviewing", "Rejected", "Ghosted", "Offer"]
            ),
            "applied_date": st.column_config.DateColumn("Date Applied"),
            "score": st.column_config.NumberColumn("Match", format="%d/10 ⭐"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic" # Allows you to manually add jobs!
    )

    if st.button("💾 Save Changes to Google Sheets"):
        # This pushes your edits back to the cloud permanently
        conn.update(data=updated_df)
        st.success("CRM Updated!")
        st.balloons()
else:
    st.warning("No data found in Google Sheets.")
