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

print(f"Searching ALL targets for campaign {TARGET_CID}...")
print("This may take a while...")

# Paginate through ALL targets
all_targets = []
start_idx = 0
count = 1000

while start_idx < 40000:  # Safety limit
    body = {"startIndex": start_idx, "count": count}
    result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
    targets = result.payload.get('targetingClauses', [])
    total = result.payload.get('totalResults', 0)
    
    if not targets:
        break
    
    for t in targets:
        if str(t.get('campaignId')) == TARGET_CID:
            all_targets.append(t)
    
    if start_idx % 5000 == 0:
        print(f"  Searched {start_idx}, found {len(all_targets)} matches...")
    
    if len(all_targets) >= total:
        break
    
    start_idx += count

print(f"\nTotal found: {len(all_targets)} targets in campaign {TARGET_CID}")

if all_targets:
    # Show ad groups
    ad_groups = set(t.get('adGroupId') for t in all_targets)
    print(f"Unique ad groups: {len(ad_groups)}")
    
    # Search for Growatt
    print("\nSearching for 'Growatt'...")
    for t in all_targets:
        for e in t.get('expression', []):
            if 'growatt' in str(e.get('value', '')).lower():
                print(f"\nTarget {t.get('targetId')}:")
                print(f"  AdGroup: {t.get('adGroupId')}")
                for e in t.get('expression', []):
                    print(f"  {e.get('type')}: {e.get('value')}")