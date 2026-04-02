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

# Try without any body at all
url = "https://advertising-api.amazon.com/v3/sp/campaigns/list"

# Send empty body as string
headers = {
    "Authorization": "Bearer " + access_token,
    "Content-Type": "application/json"
}

# Try with no body parameter at all
response = requests.post(url, headers=headers)
print(f"No body: {response.status_code}")
print(f"Response: {response.text[:500]}")

# Try with explicit empty JSON string
response2 = requests.post(url, headers=headers, data="{}")
print(f"\nWith {{}}: {response2.status_code}")
print(f"Response: {response2.text[:500]}")