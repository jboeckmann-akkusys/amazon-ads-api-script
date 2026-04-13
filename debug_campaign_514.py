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

# Check campaign 514600692899907
CID = "514600692899907"

print(f"Checking campaign {CID}...")

body = {"startIndex": 0, "count": 1000}
result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
targets = result.payload.get('targetingClauses', [])

matches = [t for t in targets if str(t.get('campaignId')) == CID]
print(f"Found {len(matches)} targets")

# Show unique ad groups
ad_groups = set(t.get('adGroupId') for t in matches)
print(f"Unique ad groups: {len(ad_groups)}")

# Search for Growatt or 9887998 in these targets
print("\nSearching for 'Growatt' or '9887998' in this campaign...")
for t in matches:
    expr = t.get('expression', [])
    for e in expr:
        val = str(e.get('value', ''))
        if 'growatt' in val.lower() or '9887998' in val:
            print(f"\nTarget {t.get('targetId')}:")
            print(f"  AdGroup: {t.get('adGroupId')}")
            print(f"  State: {t.get('state')}")
            for e in expr:
                print(f"  {e.get('type')}: {e.get('value')}")