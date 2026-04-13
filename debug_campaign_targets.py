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

TARGET_CAMPAIGN = "18699453817819"

# Try WITHOUT stateFilter to get ALL targets
print("Fetching ALL targets (no filter)...")

body = {"startIndex": 0, "count": 1000}
result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])
total = result.payload.get('totalResults', 0)

print(f"Total targets returned: {len(targets)} (total in API: {total})")

# Filter
matches = [t for t in targets if str(t.get('campaignId')) == TARGET_CAMPAIGN]

print(f"\nFound {len(matches)} targets in campaign {TARGET_CAMPAIGN}:")
if matches:
    for t in matches[:10]:
        print(f"\n  Target: {t.get('targetId')}")
        print(f"    AdGroup: {t.get('adGroupId')}")
        print(f"    State: {t.get('state')}")
        print(f"    Bid: {t.get('bid')}")
        for e in t.get('expression', [])[:2]:
            print(f"    {e.get('type')}: {e.get('value')}")
else:
    print("  None found")
    print("\n  Unique campaignIds in first 1000 targets:")
    cids = set(t.get('campaignId') for t in targets[:1000])
    for cid in sorted(cids):
        count = sum(1 for t in targets if t.get('campaignId') == cid)
        print(f"    {cid}: {count}")