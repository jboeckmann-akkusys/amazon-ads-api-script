import requests
import os

from dotenv import load_dotenv
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

def get_profiles():
    access_token = get_access_token()

    url = "https://advertising-api.amazon.com/v2/profiles"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID
    }

    response = requests.get(url, headers=headers)
    print(response.json())

get_profiles()