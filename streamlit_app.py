import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Job Tracker", layout="wide")

st.title("💼 My Job Application Dashboard")
st.write("This dashboard updates automatically every 15 minutes from GitHub Actions.")

if os.path.exists("dashboard_data.json"):
    with open("dashboard_data.json", "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    # Filter Sidebar
    st.sidebar.header("Filters")
    min_score = st.sidebar.slider("Minimum Score", 0, 10, 6)
    
    # Process Data
    df = df[df['score'] >= min_score]
    df = df.sort_values(by="saved_at", ascending=False)

    # Display Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Matches", len(df))
    col2.metric("Avg Match Score", round(df['score'].mean(), 1))
    col3.metric("Latest Search", df['saved_at'].iloc[0] if not df.empty else "N/A")

    # Main Table
    st.dataframe(
        df[["saved_at", "title", "company", "score", "why_apply", "apply_url"]],
        column_config={
            "apply_url": st.column_config.LinkColumn("Apply Link")
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("No data found yet. Wait for the first GitHub Action run!")