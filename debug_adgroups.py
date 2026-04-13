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

TARGET_CID = "18699453817819"

# Check ad groups in this campaign
print(f"Fetching ad groups (first 1000)...")

body = {"startIndex": 0, "count": 1000}
result = sp.AdGroupsV3(credentials=credentials).list_ad_groups(body=body)
ad_groups = result.payload.get('adGroups', [])

matches = [ag for ag in ad_groups if str(ag.get('campaignId')) == TARGET_CID]
print(f"Ad groups in campaign {TARGET_CID}: {len(matches)}")

if matches:
    for ag in matches[:10]:
        print(f"  {ag.get('adGroupId')}: {ag.get('name')}")
else:
    print("No ad groups found in this campaign")
    
    # Show unique campaignIds in ad groups
    print("\nCampaignIds in ad groups (sample):")
    cids = set(ag.get('campaignId') for ag in ad_groups[:100])
    for cid in sorted(cids)[:20]:
        count = sum(1 for ag in ad_groups if ag.get('campaignId') == cid)
        print(f"  {cid}: {count} ad groups")