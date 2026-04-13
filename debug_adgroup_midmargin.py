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

CAMPAIGN_ID = "18699453817819"  # Channable | SP | AUTO | DE | Mid Margin | New

print("=" * 60)
print(f"Fetching ad groups for campaign: {CAMPAIGN_ID}")
print("=" * 60)

# Fetch ad groups with campaign filter not available, so get all and filter
print("\nFetching ALL ad groups...")
all_ad_groups = []
start_idx = 0
count = 1000

while True:
    body = {"startIndex": start_idx, "count": count}
    result = sp.AdGroupsV3(credentials=credentials).list_ad_groups(body=body)
    ad_groups = result.payload.get('adGroups', [])
    if not ad_groups:
        break
    all_ad_groups.extend(ad_groups)
    total = result.payload.get('totalResults', 0)
    print(f"Fetched {len(all_ad_groups)} / {total} ad groups")
    if len(all_ad_groups) >= total:
        break
    start_idx += count

print(f"\nTotal ad groups: {len(all_ad_groups)}")

# Filter by campaign
matching = [ag for ag in all_ad_groups if str(ag.get('campaignId')) == CAMPAIGN_ID]

print(f"\nFound {len(matching)} ad groups in campaign {CAMPAIGN_ID}:")
for ag in matching[:50]:
    print(f"\nAdGroup ID: {ag.get('adGroupId')}")
    print(f"  Name: {ag.get('name')}")
    print(f"  Campaign: {ag.get('campaignId')}")
    print(f"  State: {ag.get('state')}")

if not matching:
    print("\nSearching for 'Mid Margin' in ad group names...")
    mid_margin = [ag for ag in all_ad_groups if 'mid margin' in ag.get('name', '').lower()]
    print(f"Found {len(mid_margin)} 'Mid Margin' ad groups:")
    for ag in mid_margin[:20]:
        print(f"  {ag.get('name')}")

print("\n" + "=" * 60)