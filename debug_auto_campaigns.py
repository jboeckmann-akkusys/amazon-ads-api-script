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

# Auto-targeting campaigns should show targets in the API using list_product_targets
# but in a special format - let's see if there's a different call

# Try with campaignId filter
print("Trying list_product_targets with campaignId filter...")

body = {
    "startIndex": 0,
    "count": 100,
    "campaignIdFilter": {"include": [TARGET_CID]}
}

try:
    result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
    targets = result.payload.get('targetingClauses', [])
    print(f"Targets with campaignIdFilter: {len(targets)}")
    for t in targets[:5]:
        print(f"  {t.get('targetId')}: {t.get('expression', [])[:2]}")
except Exception as e:
    print(f"Error: {e}")

# Also check if there are targets in ANY auto-targeting campaign
print("\n" + "=" * 60)
print("Finding all AUTO campaigns with ANY targets...")

result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

auto_campaigns = [c for c in campaigns if c.get('targetingType') == 'AUTO']
print(f"Found {len(auto_campaigns)} AUTO campaigns")

# Check which have targets
result = sp.TargetsV3(credentials=credentials).list_product_targets(body={"startIndex": 0, "count": 500})
targets = result.payload.get('targetingClauses', [])

for ac in auto_campaigns:
    cid = str(ac.get('campaignId'))
    count = sum(1 for t in targets if str(t.get('campaignId')) == cid)
    if count > 0:
        print(f"  {cid}: {count} targets")