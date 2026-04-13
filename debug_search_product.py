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

SEARCH_TERM = "Growatt MIC 2000TL-X"

print("=" * 60)
print(f"SEARCHING FOR: {SEARCH_TERM}")
print("=" * 60)

# Fetch all targets
all_targets = []
start_idx = 0
count = 1000

while True:
    body = {
        "startIndex": start_idx,
        "count": count,
        "stateFilter": {"include": ["ENABLED", "PAUSED"]}
    }
    result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
    targets = result.payload.get('targetingClauses', [])
    if not targets:
        break
    all_targets.extend(targets)
    total = result.payload.get('totalResults', 0)
    print(f"Fetched {len(all_targets)} / {total} targets")
    if len(all_targets) >= total:
        break
    start_idx += count

print(f"\nTotal targets: {len(all_targets)}")

# Search in expressions
matches = []
for t in all_targets:
    expr = t.get('expression', [])
    for e in expr:
        value = str(e.get('value', ''))
        if SEARCH_TERM.lower() in value.lower():
            matches.append(t)

print(f"\nFound {len(matches)} targets containing '{SEARCH_TERM}':")
for m in matches:
    print(f"\nTarget ID: {m.get('targetId')}")
    print(f"  Campaign: {m.get('campaignId')}")
    print(f"  AdGroup: {m.get('adGroupId')}")
    print(f"  State: {m.get('state')}")
    print(f"  Bid: {m.get('bid')}")
    for e in m.get('expression', []):
        print(f"  Expression: {e.get('type')} = {e.get('value')}")

print("\nSearching in ad groups instead...")

# Get ALL ad groups
print("\nFetching ALL ad groups...")
all_ad_groups = []
start_idx = 0
count = 1000

while True:
    body = {"startIndex": start_idx, "count": count}
    result = sp.AdGroupsV3(credentials=credentials).list_ad_groups(body=body)
    ad_groups = result.payload.get('adGroups', [])
    if not ad_groups:
        break
    all_ad_groups.extend(ad_groups)
    total = result.payload.get('totalResults', 0)
    print(f"Fetched {len(all_ad_groups)} / {total} ad groups")
    if len(all_ad_groups) >= total:
        break
    start_idx += count

ad_groups = all_ad_groups
print(f"\nTotal ad groups: {len(ad_groups)}")

# Search ad groups for Growatt or 9887998 or Mid Margin
search_terms = ['mid margin', 'growatt', '9887998', '9887998']
ag_matches = []
seen_names = set()
for ag in ad_groups:
    name = str(ag.get('name', ''))
    name_lower = name.lower()
    if any(term in name_lower for term in search_terms):
        if name not in seen_names:
            seen_names.add(name)
            ag_matches.append(ag)

print(f"\nFound {len(ag_matches)} unique ad groups containing search terms:")
for ag in ag_matches[:20]:
    print(f"\nAdGroup ID: {ag.get('adGroupId')}")
    print(f"  Name: {ag.get('name')}")
    print(f"  Campaign: {ag.get('campaignId')}")
    print(f"  State: {ag.get('state')}")

# Also search campaign names for Mid Margin
print("\nSearching campaigns for 'Mid Margin'...")

result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={'startIndex': 0, 'count': 5000})
campaigns = result.payload.get('campaigns', [])

c_matches = []
for c in campaigns:
    name = str(c.get('name', '')).lower()
    if 'mid margin' in name:
        c_matches.append(c)

print(f"\nFound {len(c_matches)} campaigns with 'Mid Margin':")
for c in c_matches:
    print(f"\nCampaign ID: {c.get('campaignId')}")
    print(f"  Name: {c.get('name')}")
    print(f"  State: {c.get('state')}")

print("\n" + "=" * 60)