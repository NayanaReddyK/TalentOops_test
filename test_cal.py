from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

sa_path = "/Users/apple/TalentOops/token.json"
if os.path.exists(sa_path):
    try:
        # Try as service account first
        creds = service_account.Credentials.from_service_account_file(
            sa_path, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        print("Loaded as Service Account")
    except ValueError:
        # If ValueError, it's likely an OAuth token.json
        creds = Credentials.from_authorized_user_file(
            sa_path, ["https://www.googleapis.com/auth/calendar"]
        )
        print("Loaded as OAuth User Token")
        
    svc = build("calendar", "v3", credentials=creds)
    try:
        event = {
            "summary": "Test Event",
            "start": {"dateTime": "2026-07-28T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-07-28T11:00:00Z", "timeZone": "UTC"},
            "conferenceData": {
                "createRequest": {
                    "requestId": "talentops-test-12345",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        }
        res = svc.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()
        print("Event created:", res.get("htmlLink"))
        print("Meet link:", res.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri"))
    except Exception as e:
        print("Error creating event:", e)
