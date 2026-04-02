import requests
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

print(f"CLIENT_ID: {CLIENT_ID[:20]}..." if CLIENT_ID else "CLIENT_ID: None")
print(f"REFRESH_TOKEN: {'set' if REFRESH_TOKEN else 'None'}")

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

def get_profiles():
    access_token = get_access_token()
    print(f"Access token: {access_token[:50]}...")

    url = "https://advertising-api.amazon.com/v2/profiles"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

get_profiles()