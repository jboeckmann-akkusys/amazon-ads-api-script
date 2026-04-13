from dotenv import load_dotenv
load_dotenv('.env.local')
from ad_api.api import sp
import os

creds = dict(
    refresh_token=os.getenv('REFRESH_TOKEN'),
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    profile_id=os.getenv('PROFILE_ID')
)

target_ids = ['45946528472049', '242930031082056', '202674693629576']
total = 0
found = []

while total < 41000:
    body = {'startIndex': total, 'count': 1000, 'stateFilter': {'include': ['ENABLED', 'PAUSED']}}
    r = sp.TargetsV3(credentials=creds).list_product_targets(body=body)
    targets = r.payload.get('targetingClauses', [])
    
    for t in targets:
        if t['targetId'] in target_ids:
            found.append(t)
    
    total += 1000
    print(f'Total checked: {total}')

print(f'\nFound {len(found)} targets:')
for f in found:
    print(f"TargetId: {f['targetId']}")
    print(f"  CampaignId: {f.get('campaignId')}")
    print(f"  AdGroupId: {f.get('adGroupId')}")
    print(f"  State: {f['state']}")
    print(f"  Bid: {f.get('bid')}")
    print(f"  Expression: {[e['type'] for e in f.get('expression', [])]}")
    print()