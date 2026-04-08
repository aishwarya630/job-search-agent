import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Job Search CRM", layout="wide")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # TTL=0 means it fetches fresh data from the sheet every time you refresh
    data = conn.read(ttl=0) 
    # Ensure notes column exists
    if 'notes' not in data.columns:
        data['notes'] = ""
    return data

df = load_data()

st.title("💼 Master Job Tracker")
st.info("Bot automatically adds new jobs here every 15 mins. Status is 'Not Applied' by default.")

# --- STATUS OPTIONS ---
all_status = ["Not Applied", "Interested", "Applied", "Interviewing", "Rejected", "Ghosted", "Offer"]

# --- CRM TABLE ---
if not df.empty:
    # Ensure data is clean for the editor
    df['status'] = df['status'].fillna("Not Applied").replace("", "Not Applied")
    
    # We edit the WHOLE dataframe now
    updated_df = st.data_editor(
        df,
        column_config={
            "apply_url": st.column_config.LinkColumn("Job Link"),
            "status": st.column_config.SelectboxColumn("Status", options=all_status),
            "applied_date": st.column_config.DateColumn("Date Applied"),
            "score": st.column_config.NumberColumn("Score", format="%d ⭐"),
            "notes": st.column_config.TextColumn("Notes", help="Write your interview notes here!", width="large"),
            "title": st.column_config.Column(disabled=True),
            "company": st.column_config.Column(disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        key="crm_editor"
    )

    # If the user changed ANYTHING in the table
    if st.button("💾 Push Changes to Google Sheets"):
        try:
            conn.update(data=updated_df)
            st.success("Synchronized! Your notes and statuses are now updated in Google Sheets.")
            st.balloons()
        except Exception as e:
            st.error(f"Error saving: {e}")
