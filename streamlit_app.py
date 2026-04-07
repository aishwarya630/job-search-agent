import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import os

# 1. SETUP
st.set_page_config(page_title="Job Search CRM", layout="wide")

# 2. PIN PROTECTION
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Private Job CRM")
    user_pin = st.text_input("Enter PIN to Access", type="password")
    if st.button("Unlock"):
        if user_pin == st.secrets["ACCESS_PIN"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Incorrect PIN")
    st.stop()

# 3. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheets_data():
    try:
        data = conn.read(ttl="1m")
        # --- CRITICAL DATA CLEANING TO PREVENT CRASHES ---
        # 1. Force Score to be Numeric
        data['score'] = pd.to_numeric(data['score'], errors='coerce').fillna(0)
        # 2. Force Applied Date to be Datetime (coerce invalid text to NaT)
        data['applied_date'] = pd.to_datetime(data['applied_date'], errors='coerce')
        # 3. Handle Status blanks
        if 'status' not in data.columns:
            data['status'] = "Interested"
        data['status'] = data['status'].fillna("Interested").replace("", "Interested")
        return data
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

df = load_gsheets_data()

# 4. INTERACTIVE DASHBOARD
st.title("💼 My Job Search CRM")

# --- SIDEBAR: SYNC LOGIC ---
st.sidebar.header("Data Management")
if st.sidebar.button("🔄 Sync New Jobs from Bot"):
    JSON_FILE = "dashboard_data.json"
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            bot_data = json.load(f)
        
        if bot_data:
            df_bot = pd.DataFrame(bot_data)
            
            if not df.empty:
                df_combined = pd.concat([df, df_bot]).drop_duplicates(subset=['apply_url'], keep='first')
            else:
                df_combined = df_bot
            
            for col in ["status", "applied_date", "notes"]:
                if col not in df_combined.columns:
                    df_combined[col] = "Interested" if col == "status" else ""

            conn.update(data=df_combined)
            st.sidebar.success(f"Imported {len(bot_data)} jobs!")
            st.rerun()
        else:
            st.sidebar.warning("Bot file is empty.")
    else:
        st.sidebar.error("dashboard_data.json not found.")

# --- MAIN CRM TABLE ---
if not df.empty:
    st.sidebar.header("Filter Board")
    
    all_status = ["Interested", "Applied", "Interviewing", "Rejected", "Ghosted", "Offer"]
    selected_status = st.sidebar.multiselect("Status Filter", all_status, default=["Interested", "Applied"])

    # Filtered View
    filtered_df = df[df['status'].isin(selected_status)]

    st.subheader(f"Managing {len(filtered_df)} Applications")
    
    # Editable Table
    updated_df = st.data_editor(
        filtered_df,
        column_config={
            "apply_url": st.column_config.LinkColumn("Job Link"),
            "status": st.column_config.SelectboxColumn("Status", options=all_status),
            "applied_date": st.column_config.DateColumn("Date Applied"),
            "score": st.column_config.NumberColumn("Score", format="%d ⭐"),
            # Prevent users from editing AI-generated data to keep things clean
            "title": st.column
