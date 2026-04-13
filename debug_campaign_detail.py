import os
from dotenv import load_dotenv
load_dotenv('.env.local')
from ad_api.api import sp
import json

credentials = dict(
    refresh_token=os.getenv('REFRESH_TOKEN'),
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    profile_id=os.getenv('PROFILE_ID')
)

print(f"Current profile_id: {os.getenv('PROFILE_ID')}")

# Get campaign 18699453817819 FULL details
print("\nFetching campaign details...")

result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

target_camp = None
for c in campaigns:
    if str(c.get('campaignId')) == "18699453817819":
        target_camp = c
        break

if target_camp:
    print(f"\nCampaign: {json.dumps(target_camp, indent=2)}")
else:
    print("Campaign not found!")

# Also try to see ALL campaigns with their exact IDs
print("\n" + "=" * 60)
print("All campaign IDs (first 50):")
for c in campaigns[:50]:
    print(f"  {c.get('campaignId')}: {c.get('name')[:50]}")