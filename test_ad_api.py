import os
import json
from dotenv import load_dotenv
load_dotenv(".env.local")

from ad_api.api import sponsored_products

credentials = dict(
    refresh_token=os.getenv("REFRESH_TOKEN"),
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    profile_id="2511423595502144"
)

body = {}

try:
    result = sponsored_products.CampaignsV3(credentials=credentials).list_campaigns(body=body)
    print(f"Status: {result}")
    print(f"Payload: {json.dumps(result.payload, indent=2)[:1000]}")
except Exception as e:
    print(f"Error: {e}")