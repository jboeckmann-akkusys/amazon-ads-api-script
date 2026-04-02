from ad_api.api import sp
from ad_api.base import Marketplaces
from dotenv import load_dotenv
import os

load_dotenv(".env.local")

credentials = {
    "client_id": os.getenv("CLIENT_ID"),
    "client_secret": os.getenv("CLIENT_SECRET"),
    "refresh_token": os.getenv("REFRESH_TOKEN"),
}

# Try with account=None or empty string
try:
    response = sp.CampaignsV3(
        account="default",
        marketplace=Marketplaces.EU,
        credentials=credentials
    ).list_campaigns()
    print("API Response:", response)
except Exception as e:
    print(f"Error: {e}")