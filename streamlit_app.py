import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Job Search CRM", layout="wide")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 1. Fetch data from Google Sheets
    data = conn.read(ttl=0) 
    
    # 2. Add missing columns if they don't exist in the sheet yet
    expected_cols = ["title", "company", "location", "apply_url", "status", "applied_date", "score", "notes"]
    for col in expected_cols:
        if col not in data.columns:
            data[col] = ""

    # 3. CRITICAL: Type Casting (This stops the crashing)
    # Convert 'applied_date' strings to actual Python Date objects
    data['applied_date'] = pd.to_datetime(data['applied_date'], errors='coerce')
    
    # Convert 'score' to numbers
    data['score'] = pd.to_numeric(data['score'], errors='coerce').fillna(0)
    
    # Fill empty statuses
    data['status'] = data['status'].fillna("Not Applied").replace("", "Not Applied")
    
    # Ensure notes are strings
    data['notes'] = data['notes'].fillna("")
    
    return data

df = load_data()

st.title("💼 Master Job Tracker")
st.info("Bot automatically adds new jobs here. Status is 'Not Applied' by default.")

# --- STATUS OPTIONS ---
all_status = ["Not Applied", "Interested", "Applied", "Interviewing", "Rejected", "Ghosted", "Offer"]

# --- CRM TABLE ---
if not df.empty:
    updated_df = st.data_editor(
        df,
        column_config={
            "apply_url": st.column_config.LinkColumn("Job Link"),
            "status": st.column_config.SelectboxColumn("Status", options=all_status),
            "applied_date": st.column_config.DateColumn("Date Applied"),
            "score": st.column_config.NumberColumn("Score", format="%d ⭐"),
            "notes": st.column_config.TextColumn("Notes", help="Write notes here!", width="large"),
            "title": st.column_config.Column(disabled=True),
            "company": st.column_config.Column(disabled=True),
            "location": st.column_config.Column(disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        key="crm_editor"
    )

    if st.button("💾 Push Changes to Google Sheets"):
        try:
            # We convert dates back to strings before sending to Google Sheets 
            # to ensure Google handles them correctly
            save_df = updated_df.copy()
            save_df['applied_date'] = save_df['applied_date'].dt.strftime('%Y-%m-%d').fillna("")
            
            conn.update(data=save_df)
            st.success("Synchronized! Your notes and statuses are updated.")
            st.balloons()
        except Exception as e:
            st.error(f"Error saving: {e}")
