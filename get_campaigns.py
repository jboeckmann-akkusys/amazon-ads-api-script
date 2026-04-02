import requests
import os
from dotenv import load_dotenv
import json

load_dotenv(".env.local")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

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

def list_campaigns():
    access_token = get_access_token()
    print(f"Access token: {access_token[:50]}...")

    url = "https://advertising-api.amazon.com/v3/sp/campaigns"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2)[:2000])

list_campaigns()