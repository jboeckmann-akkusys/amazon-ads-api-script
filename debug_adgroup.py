import os
from dotenv import load_dotenv
load_dotenv('.env.local')
from ad_api.api import sp

credentials = dict(
    refresh_token=os.getenv('REFRESH_TOKEN'),
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    profile_id=os.getenv('PROFILE_ID')
)

print("=" * 60)
print("SEARCHING FOR AD GROUP")
print("=" * 60)

# Find campaign
result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

# Find the exact campaign
for c in campaigns:
    name = c.get('name', '')
    if 'Channable | SP | AUTO | DE | Mid Margin | New' in name:
        print(f"Campaign: ID={c.get('campaignId')}, Name={name}")
        target_campaign_id = str(c.get('campaignId'))
        break

# Try AdGroupsV3
print(f"\nFetching ad groups via AdGroupsV3 for campaign {target_campaign_id}...")

try:
    result = sp.AdGroupsV3(credentials=credentials).list_ad_groups(body={'campaignId': target_campaign_id})
    ad_groups = result.payload.get('adGroups', [])
    print(f"Found {len(ad_groups)} ad groups:")
    for ag in ad_groups:
        name = ag.get('name', 'N/A')
        agid = ag.get('adGroupId')
        state = ag.get('state')
        print(f"  AdGroup ID: {agid}")
        print(f"    Name: {name}")
        print(f"    State: {state}")
        print()
except Exception as e:
    print(f"Error: {e}")

print("=" * 60)