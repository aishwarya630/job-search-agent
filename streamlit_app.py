import streamlit as st
from streamlit_gsheets import GSheetsConnection

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

# 3. CONNECTION (Uses the [connections.gsheets] block from secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # We don't pass the URL here because it's already in the Secrets
    df = conn.read(ttl="1m")
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.info("Check that your Streamlit Secrets have the [connections.gsheets] block.")
    st.stop()

# 4. INTERACTIVE DASHBOARD
st.title("💼 My Job Search CRM")

if not df.empty:
    st.sidebar.header("Filter Board")
    
    # Check if 'status' column exists, if not, create it
    if 'status' not in df.columns:
        df['status'] = "Interested"

    all_status = ["Interested", "Applied", "Interviewing", "Rejected", "Ghosted", "Offer"]
    selected_status = st.sidebar.multiselect("Status Filter", all_status, default=["Interested", "Applied"])

    # Filtered View
    filtered_df = df[df['status'].isin(selected_status)]

    st.subheader("Manage Your Applications")
    updated_df = st.data_editor(
        filtered_df,
        column_config={
            "apply_url": st.column_config.LinkColumn("Job Link"),
            "status": st.column_config.SelectboxColumn("Status", options=all_status),
            "applied_date": st.column_config.DateColumn("Date Applied"),
            "score": st.column_config.NumberColumn("Score", format="%d ⭐")
        },
        width="stretch",
        hide_index=True
    )

    if st.button("💾 Save Changes to Google Sheets"):
        # The .update() method sends the data back to the sheet
        conn.update(data=updated_df)
        st.success("Changes Saved Permanently!")
        st.balloons()
else:
    st.warning("The Google Sheet is currently empty.")
