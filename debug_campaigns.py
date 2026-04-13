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
print("CAMPAIGN AND AD GROUP DEBUG")
print("=" * 60)

# Fetch campaigns with details
result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

print("\n=== CAMPAIGNS ===")
for c in campaigns:
    cid = c.get('campaignId')
    name = c.get('name', 'N/A')
    state = c.get('state', 'UNKNOWN')
    print(f"ID: {cid}")
    print(f"  Name: {name}")
    print(f"  State: {state}")
    print()

# Get active campaign IDs
active_ids = {str(c.get('campaignId')) for c in campaigns if c.get('state') == 'ENABLED'}
paused_ids = {str(c.get('campaignId')) for c in campaigns if c.get('state') == 'PAUSED'}
archived_ids = {str(c.get('campaignId')) for c in campaigns if c.get('state') == 'ARCHIVED'}

print("\n=== CAMPAIGN STATE SUMMARY ===")
print(f"Active: {len(active_ids)} campaigns")
print(f"Paused: {len(paused_ids)} campaigns")
print(f"Archived: {len(archived_ids)} campaigns")

# Now fetch targets for active campaigns
print("\n=== TARGETS IN ACTIVE CAMPAIGNS ===")

result = sp.TargetsV3(credentials=credentials).list_product_targets(body={'startIndex': 0, 'count': 5000})
targets = result.payload.get('targetingClauses', [])

for t in targets:
    cid = t.get('campaignId')
    if cid in active_ids:
        tid = t.get('targetId')
        adgid = t.get('adGroupId')
        state = t.get('state')
        bid = t.get('bid', 0)
        expr_types = [e.get('type') for e in t.get('expression', [])]
        
        print(f"Target: {tid}")
        print(f"  Campaign ID: {cid}")
        print(f"  AdGroup ID: {adgid}")
        print(f"  State: {state}")
        print(f"  Bid: {bid}")
        print(f"  Expression Types: {expr_types}")
        print()

print("=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)