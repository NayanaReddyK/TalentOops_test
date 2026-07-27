from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

sa_path = "/Users/apple/TalentOops/token.json"
creds = service_account.Credentials.from_service_account_file(
    sa_path, scopes=["https://www.googleapis.com/auth/meetings.space.created"]
)

try:
    svc = build("meet", "v2", credentials=creds)
    space = svc.spaces().create(body={}).execute()
    print("Meet space created:", space.get("meetingUri"))
except Exception as e:
    print("Error creating Meet space:", e)
