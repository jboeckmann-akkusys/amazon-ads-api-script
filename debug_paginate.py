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

active_campaign_ids = {"18699453817819"}  # Test with just one

all_targets = []
start_index = 0
count = 500

print(f"Fetching targets for {len(active_campaign_ids)} campaigns...")

while True:
    body = {
        "startIndex": start_index,
        "count": count,
        "stateFilter": {"include": ["ENABLED", "PAUSED"]},
        "campaignIdFilter": {"include": list(active_campaign_ids)}
    }
    
    result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
    targets = result.payload.get('targetingClauses', [])
    total = result.payload.get('totalResults', 0)
    
    if not targets:
        break
    
    all_targets.extend(targets)
    print(f"Fetched {len(targets)} (total so far: {len(all_targets)}, API total: {total})")
    
    if len(all_targets) >= total:
        break
    
    start_index += count

print(f"\nFinal: {len(all_targets)} targets fetched (API reported total: {total})")

# Filter
types_to_reduce = ["QUERY_BROAD_REL_MATCHES", "ASIN_SUBSTITUTE_RELATED", "ASIN_ACCESSORY_RELATED"]
to_reduce = []
for t in all_targets:
    for e in t.get('expression', []):
        if e.get('type') in types_to_reduce:
            to_reduce.append(t)
            break

print(f"Targets to reduce bid: {len(to_reduce)}")