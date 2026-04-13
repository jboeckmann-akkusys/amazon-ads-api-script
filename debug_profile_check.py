import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# Try get profile via advertising API
url = "https://advertising-api.amazon.com/v2/profiles"
data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}

# First get access token
token_resp = requests.post("https://api.amazon.com/auth/o2/token", data=data)
if token_resp.status_code != 200:
    print(f"Token error: {token_resp.text}")
    exit(1)

access_token = token_resp.json()["access_token"]

# Get profiles
headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": CLIENT_ID,
    "Content-Type": "application/json"
}

# Try different API endpoints
endpoints = [
    "https://advertising-api.amazon.com/v2/profiles",
    "https://advertising-api-test.amazon.com/v2/profiles", 
]

for ep in endpoints:
    resp = requests.get(ep, headers=headers)
    print(f"{ep}: {resp.status_code}")
    if resp.status_code == 200 and resp.text != "[]":
        print(f"  Response: {resp.text[:500]}")

# Also check if there's a countryCode filter that matters
# Maybe profile is in DE but we're querying US?
print("\n" + "=" * 60)
print("Checking marketplace in .env.local profile...")

# Check current profile details via ad_api
from ad_api.api import sp
credentials = dict(
    refresh_token=os.getenv('REFRESH_TOKEN'),
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    profile_id=os.getenv('PROFILE_ID')
)

# Try to get profile info
try:
    result = sp.Profiles(credentials=credentials).list_profiles()
    print(f"Profiles API: {result.payload}")
except Exception as e:
    print(f"Profiles error: {e}")