import requests
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
PROFILE_ID = os.getenv("PROFILE_ID")

# Get access token
url = "https://api.amazon.com/auth/o2/token"
data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}
response = requests.post(url, data=data)
access_token = response.json()["access_token"]

# Test profiles without Scope header (this worked earlier)
url1 = "https://advertising-api.amazon.com/v2/profiles"
headers1 = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
response1 = requests.get(url1, headers=headers1)
print(f"GET /v2/profiles (no scope): {response1.status_code}")
print(f"Response: {response1.text}")

# Test campaigns endpoint - POST with scope
url2 = "https://advertising-api.amazon.com/v3/sp/campaigns/list"
headers2 = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-Scope": PROFILE_ID,
    "Content-Type": "application/json"
}
response2 = requests.post(url2, headers=headers2, json={})
print(f"\nPOST /v3/sp/campaigns/list: {response2.status_code}")
print(f"Response: {response2.text[:500]}")