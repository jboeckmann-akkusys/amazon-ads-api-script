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

print("=" * 60)
print("List ALL campaigns with exact IDs")
print("=" * 60)

result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

print(f"Total campaigns: {len(campaigns)}")

# Print all campaigns
for c in campaigns:
    print(f"\n{c.get('campaignId')}")
    print(f"  Name: {c.get('name')}")
    print(f"  State: {c.get('state')}")

print("\n" + "=" * 60)
print("Now fetch first 20 targets, show campaignId type")
print("=" * 60)

body = {"startIndex": 0, "count": 20, "stateFilter": {"include": ["ENABLED", "PAUSED"]}}
result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])

for t in targets[:10]:
    cid = t.get('campaignId')
    print(f"\nTarget: {t.get('targetId')}")
    print(f"  campaignId: '{cid}' (type: {type(cid).__name__})")
    print(f"  campaignId == '18699453817819': {cid == '18699453817819'}")
    print(f"  campaignId == 18699453817819: {cid == 18699453817819}")