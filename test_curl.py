import subprocess
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
    import requests
    response = requests.post(url, data=data)
    return response.json()["access_token"]

access_token = get_access_token()

# Use curl to make the request
curl_cmd = [
    "curl", "-X", "POST",
    "https://advertising-api.amazon.com/v3/sp/campaigns/list",
    "-H", f"Authorization: Bearer {access_token}",
    "-H", f"Amazon-Advertising-API-Scope: {PROFILE_ID}",
    "-H", "Content-Type: application/json",
    "-H", "Accept: application/vnd.spCampaign.v3+json",
    "-d", "{}"
]

result = subprocess.run(curl_cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)