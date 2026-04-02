import requests
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
PROFILE_ID = os.getenv("PROFILE_ID")

def get_access_token():
    url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(url, data=data)
    return response.json()["access_token"]

access_token = get_access_token()

# Test: POST campaigns with ClientId + Scope
url = "https://advertising-api.amazon.com/v3/sp/campaigns/list"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": CLIENT_ID,
    "Amazon-Advertising-API-Scope": PROFILE_ID,
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, json={})
print(f"POST /v3/sp/campaigns/list (ClientId+Scope): {response.status_code}")
print(f"Response: {response.text[:500]}")

# Now test with just ClientId
headers2 = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": CLIENT_ID,
    "Content-Type": "application/json"
}

response2 = requests.post(url, headers=headers2, json={})
print(f"\nPOST /v3/sp/campaigns/list (ClientId only): {response2.status_code}")
print(f"Response: {response2.text[:500]}")