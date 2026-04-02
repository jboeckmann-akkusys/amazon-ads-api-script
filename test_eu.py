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

# Test with EU endpoint and ClientId header (not Scope)
url = "https://advertising-api-eu.amazon.com/v3/sp/targets/list"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": CLIENT_ID,
    "Content-Type": "application/json"
}

body = {
    "startIndex": 0,
    "count": 10
}

response = requests.post(url, headers=headers, json=body)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")