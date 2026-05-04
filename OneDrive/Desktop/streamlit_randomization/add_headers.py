import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Read credentials from environment or .streamlit/secrets.toml
# Make sure your credentials.json is in the project root or set GOOGLE_CREDENTIALS_JSON env var
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not credentials_json:
    print("Error: GOOGLE_CREDENTIALS_JSON not set")
    print("Set it via: export GOOGLE_CREDENTIALS_JSON='<your-json-content>'")
    exit(1)

# Read spreadsheet ID from environment or .streamlit/secrets.toml
spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

if not spreadsheet_id:
    print("Error: GOOGLE_SHEETS_ID not set")
    print("Set it via: export GOOGLE_SHEETS_ID='your-spreadsheet-id'")
    exit(1)

# Parse credentials
try:
    credentials_dict = json.loads(credentials_json)
except json.JSONDecodeError:
    print("Error: Invalid JSON in GOOGLE_CREDENTIALS_JSON")
    exit(1)

# Authenticate
credentials = Credentials.from_service_account_info(
    credentials_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

service = build("sheets", "v4", credentials=credentials)

# Headers
headers = [
    "Date", "School ID", "Grade Range",
    "Grade 1 Sections", "Grade 2 Sections", "Grade 3 Sections",
    "Grade 4 Sections", "Grade 5 Sections", "Grade 6 Sections",
    "Selected Section 1", "Section 1 Total Students", "Section 1 Selected Students",
    "Selected Section 2", "Section 2 Total Students", "Section 2 Selected Students",
    "Selected Section 3", "Section 3 Total Students", "Section 3 Selected Students",
]

# Add headers to first row
service.spreadsheets().values().update(
    spreadsheetId=spreadsheet_id,
    range="Sheet1!A1",
    valueInputOption="USER_ENTERED",
    body={"values": [headers]}
).execute()

print("[SUCCESS] Headers added successfully!")
print("Total columns: " + str(len(headers)))
