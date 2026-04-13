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
LOW_BID = 0.02

# Get targets with campaignIdFilter
print(f"Fetching targets for campaign {TARGET_CID}...")

body = {
    "startIndex": 0,
    "count": 500,
    "campaignIdFilter": {"include": [TARGET_CID]}
}

result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])

# Filter for targets to reduce
types_to_reduce = {
    "QUERY_BROAD_REL_MATCHES": "loose-match",
    "ASIN_SUBSTITUTE_RELATED": "substitutes", 
    "ASIN_ACCESSORY_RELATED": "complements"
}

targets_to_reduce = []
for t in targets:
    state = t.get('state')
    if state not in ["ENABLED", "PAUSED"]:
        continue
    
    for expr in t.get('expression', []):
        if expr.get('type') in types_to_reduce:
            targets_to_reduce.append(t)
            break

print(f"Found {len(targets_to_reduce)} targets to reduce bid")

if targets_to_reduce:
    # Get unique expression types
    expr_counts = {}
    for t in targets_to_reduce:
        for e in t.get('expression', []):
            t = e.get('type')
            expr_counts[t] = expr_counts.get(t, 0) + 1
    
    print("\nExpression types:")
    for t, c in expr_counts.items():
        print(f"  {t}: {c}")
    
    # Try to update first target (test)
    test_target = targets_to_reduce[0]
    print(f"\nTest update on target {test_target.get('targetId')}:")
    print(f"  AdGroup: {test_target.get('adGroupId')}")
    print(f"  Expression: {test_target.get('expression')}")
    
    # Build update payload
    updates = [{
        "targetId": test_target.get('targetId'),
        "adGroupId": test_target.get('adGroupId'),
        "campaignId": test_target.get('campaignId'),
        "bid": LOW_BID
    }]
    
    print(f"\nUpdating bid to {LOW_BID}...")
    update_body = {"targetingClauses": updates}
    
    try:
        result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=update_body)
        print(f"Result: {result.payload}")
    except Exception as e:
        print(f"Error: {e}")