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

# Get active campaign IDs
result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
active_ids = {str(x.get('campaignId')) for x in result.payload.get('campaigns', []) if x.get('state') == 'ENABLED'}
print('Active campaign IDs:', active_ids)

# Get targets
result = sp.TargetsV3(credentials=credentials).list_product_targets(body={'startIndex': 0, 'count': 10000})
targets = result.payload.get('targetingClauses', [])

# Analyze targets in active campaigns with high bid (> 0.02)
print('\n==ENABLED targets in active campaigns with bid > 0.02==')
for t in targets:
    cid = t.get('campaignId')
    state = t.get('state')
    bid = t.get('bid', 0)
    if cid in active_ids and state == 'ENABLED' and bid > 0.02:
        expr_types = [e.get('type') for e in t.get('expression', [])]
        print(f'Target {t.get("targetId")}: bid={bid}, expr={expr_types}')