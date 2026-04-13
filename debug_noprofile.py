import os
from dotenv import load_dotenv
load_dotenv('.env.local')
from ad_api.api import sp

# Try WITHOUT profile_id to see all data
credentials_all = dict(
    refresh_token=os.getenv('REFRESH_TOKEN'),
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    # profile_id intentionally omitted
)

print("Fetching campaigns WITHOUT profile_id filter...")

result = sp.CampaignsV3(credentials=credentials_all).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

print(f"Total campaigns: {len(campaigns)}")

# Find 18699453817819
for c in campaigns:
    if str(c.get('campaignId')) == "18699453817819":
        print(f"\nFound campaign {c.get('campaignId')}:")
        print(f"  Name: {c.get('name')}")
        print(f"  State: {c.get('state')}")

# Also show all campaigns with "Mid Margin"
print("\nAll 'Mid Margin' campaigns:")
for c in campaigns:
    if 'margin' in c.get('name', '').lower():
        print(f"  {c.get('campaignId')}: {c.get('name')} ({c.get('state')})")