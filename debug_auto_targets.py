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

print(f"Fetching targets with different filters for campaign {TARGET_CID}...")

# Try different state filters
filters = [
    {"include": ["ENABLED"]},
    {"include": ["PAUSED"]},
    {"include": ["ENABLED", "PAUSED"]},
    {"include": ["ENABLED", "PAUSED", "ARCHIVED"]},
    {},  # No filter
]

for state_filter in filters:
    body = {"startIndex": 0, "count": 500}
    if state_filter:
        body["stateFilter"] = state_filter
    
    result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
    targets = result.payload.get('targetingClauses', [])
    
    matches = [t for t in targets if str(t.get('campaignId')) == TARGET_CID]
    print(f"  Filter {state_filter}: {len(matches)} targets")

# Also check expression types in this campaign's targets
print("\n" + "=" * 60)
print("If targets exist, check expression types:")

# Get all targets and look for campaign
body = {"startIndex": 0, "count": 1000}
result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])

matches = [t for t in targets if str(t.get('campaignId')) == TARGET_CID]
print(f"Total targets in campaign {TARGET_CID}: {len(matches)}")

if matches:
    # Show expression types
    expr_types = {}
    for t in matches:
        for e in t.get('expression', []):
            etype = e.get('type', 'UNKNOWN')
            expr_types[etype] = expr_types.get(etype, 0) + 1
    
    print("Expression types:")
    for etype, count in sorted(expr_types.items()):
        print(f"  {etype}: {count}")
else:
    print("Still no targets found")
    print("\nLet's check what campaignId format the API returns:")
    for t in targets[:5]:
        print(f"  {t.get('campaignId')} (type: {type(t.get('campaignId'))})")