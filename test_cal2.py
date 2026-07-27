from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

sa_path = "/Users/apple/TalentOops/token.json"
creds = service_account.Credentials.from_service_account_file(
    sa_path, scopes=["https://www.googleapis.com/auth/calendar"]
)
svc = build("calendar", "v3", credentials=creds)
try:
    event = {
        "summary": "Test Event without Meet",
        "start": {"dateTime": "2026-07-28T10:00:00Z", "timeZone": "UTC"},
        "end": {"dateTime": "2026-07-28T11:00:00Z", "timeZone": "UTC"},
    }
    res = svc.events().insert(calendarId="primary", body=event).execute()
    print("Event created:", res.get("htmlLink"))
    print("Event ID:", res.get("id"))
except Exception as e:
    print("Error creating event:", e)
