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

# Get campaigns with Mid Margin
result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

mid_margin = [c for c in campaigns if 'margin' in c.get('name', '').lower()]
print("Mid Margin campaigns:")
for c in mid_margin:
    print(f"  {c.get('campaignId')}: {c.get('name')} ({c.get('state')})")

print("\n" + "=" * 60)

# Get campaign IDs that have targets
print("Fetching targets to see which campaigns have targets...")

body = {"startIndex": 0, "count": 1000}
result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])

campaign_ids_with_targets = set(t.get('campaignId') for t in targets)
print(f"\nCampaigns with targets (first 1000): {len(campaign_ids_with_targets)}")

# Check which mid-margin campaigns have targets
print("\nMid Margin campaigns WITH targets:")
for c in mid_margin:
    cid = str(c.get('campaignId'))
    if cid in campaign_ids_with_targets:
        count = sum(1 for t in targets if t.get('campaignId') == cid)
        print(f"  {cid}: {count} targets")
    else:
        print(f"  {cid}: NO targets in first 1000")

# Check for campaignId 514600692899907 (another Mid Margin)
print("\n" + "=" * 60)
cid2 = "514600692899907"
m2 = [t for t in targets if t.get('campaignId') == cid2]
print(f"Campaign {cid2} (Channable - SP - AUTO - DE - Mid Margin): {len(m2)} targets")