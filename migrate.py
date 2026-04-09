import pandas as pd
import json
import os

# 1. Load your local JSON data
JSON_FILE = "dashboard_data.json"

if not os.path.exists(JSON_FILE):
    print(f"❌ Error: {JSON_FILE} not found in this folder!")
    exit()

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

df_json = pd.DataFrame(data)

# 2. Add CRM columns if they are missing
for col in ["status", "applied_date", "notes"]:
    if col not in df_json.columns:
        df_json[col] = "Interested" if col == "status" else ""

print(f"📋 Loaded {len(df_json)} jobs from JSON.")

# 3. Instructions for Manual Migration (The "No-Console" Way)
# Since we aren't using the Google Cloud Console, the easiest way to 
# migrate locally is to export the JSON to a CSV and paste it into Sheets.

df_json.to_csv("migration_data.csv", index=False)

print("✅ Step 1: Created 'migration_data.csv'.")
print("✅ Step 2: Open this CSV file in Excel or Notepad.")
print("✅ Step 3: Copy all rows (except the header if you already have headers).")
print("✅ Step 4: Paste them directly into your Google Sheet.")
print("🚀 Migration ready!")