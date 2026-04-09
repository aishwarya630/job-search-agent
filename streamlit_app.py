import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Job Search CRM", layout="wide")

def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PIN"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input("Enter PIN to access Job Tracker", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Enter PIN to access Job Tracker", type="password", on_change=password_entered, key="password")
        st.error("😕 PIN incorrect")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()  # Stop execution here until PIN is correct
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    # Define exact columns we expect
    expected_cols = [
        "title", "company", "location", "apply_url", "score", 
        "what_fits", "whats_missing", "why_apply", "visa_note", 
        "saved_at", "status", "applied_date", "notes"
    ]
    for col in expected_cols:
        if col not in data.columns:
            data[col] = ""
    
    # Cleaning types
    data['applied_date'] = pd.to_datetime(data['applied_date'], errors='coerce')
    data['score'] = pd.to_numeric(data['score'], errors='coerce').fillna(0)
    data['status'] = data['status'].fillna("Not Applied").replace("", "Not Applied")
    data['notes'] = data['notes'].fillna("")
    data['visa_note'] = data['visa_note'].fillna("")
    
    return data

df = load_data()

# --- 1. SMART ARCHIVE LOGIC ---
# Define dealbreakers (matches your request for US/Work Ex)
dealbreakers = ["us citizen", "citizenship", "security clearance", "years", "10+", "8+", "senior"]

# Tag rows that match dealbreakers
df['is_dealbreaker'] = (
    df['notes'].str.lower().str.contains('|'.join(dealbreakers), na=False) | 
    df['visa_note'].str.lower().str.contains('|'.join(dealbreakers), na=False) |
    df['title'].str.lower().str.contains('senior|lead|principal', na=False)
)

st.title("💼 Master Job Tracker")

# --- 2. PIPELINE TABS ---
tab1, tab2, tab3 = st.tabs(["🔥 Active Leads", "✅ Applied", "📂 Archive (Dealbreakers)"])

with tab1:
    # Only show jobs that are NOT dealbreakers and NOT applied
    active_df = df[~df['is_dealbreaker'] & (df['status'] == "Not Applied")]
    st.subheader(f"Recommended for You ({len(active_df)})")
    
with tab2:
    applied_df = df[df['status'] == "Applied"]
    st.subheader(f"Tracking Applications ({len(applied_df)})")

with tab3:
    archive_df = df[df['is_dealbreaker'] | (df['status'] == "Archived")]
    st.subheader("Auto-Filtered Roles")

# --- 3. THE INTERACTIVE EDITOR ---
# (Apply to whichever tab is active)
current_view = active_df if tab1 else (applied_df if tab2 else archive_df)

updated_df = st.data_editor(
    current_view,
    column_config={
        "apply_url": st.column_config.LinkColumn("Link"),
        "score": st.column_config.ProgressColumn("Match", min_value=0, max_value=10),
        "status": st.column_config.SelectboxColumn("Status", options=["Not Applied", "Applied", "Interviewing", "Archived", "Rejected"]),
        "what_fits": st.column_config.TextColumn("Why Me?", width="medium"),
        "whats_missing": st.column_config.TextColumn("Gaps", width="medium"),
        "is_dealbreaker": None # Hide this column
    },
    use_container_width=True,
    hide_index=True,
    key="editor"
)

# --- 4. GLOBAL SAVE ---
if st.button("💾 Push All Changes to Google Sheets"):
    # Merge the edited view back into the main dataframe
    df.update(updated_df)
    save_df = df.drop(columns=['is_dealbreaker']) # Don't save our helper column
    save_df['applied_date'] = save_df['applied_date'].dt.strftime('%Y-%m-%d').fillna("")
    conn.update(data=save_df)
    st.success("Synchronized! Archive updated.")
    st.balloons()
