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

# Use campaignIdFilter to get targets for campaign
print(f"Fetching targets for campaign {TARGET_CID}...")

body = {
    "startIndex": 0,
    "count": 500,
    "campaignIdFilter": {"include": [TARGET_CID]}
}

result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])
total = result.payload.get('totalResults', 0)

print(f"Total targets: {len(targets)} (total in API: {total})")

if targets:
    print(f"\nFound {len(targets)} targets:")
    for t in targets:
        print(f"\n  Target: {t.get('targetId')}")
        print(f"    AdGroup: {t.get('adGroupId')}")
        print(f"    State: {t.get('state')}")
        print(f"    Bid: {t.get('bid')}")
        for e in t.get('expression', []):
            print(f"    {e.get('type')}: {e.get('value')}")
else:
    print("No targets found for this campaign via API")