import urllib.request
import urllib.parse
import json
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
PROFILE_ID = os.getenv("PROFILE_ID")

def get_access_token():
    url = "https://api.amazon.com/auth/o2/token"
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }).encode()
    
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())["access_token"]

access_token = get_access_token()

# Try POST with urllib
url = "https://advertising-api.amazon.com/v3/sp/campaigns/list"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": CLIENT_ID,
    "Content-Type": "application/json"
}

body = json.dumps({}).encode('utf-8')
req = urllib.request.Request(url, data=body, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode())