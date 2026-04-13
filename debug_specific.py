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

# Get campaign states
r = sp.CampaignsV3(credentials=creds).list_campaigns(body={})
campaigns = r.payload.get('campaigns', [])

# Check if campaign 18699453817819 is in the active list
active_campaigns = {str(c['campaignId']) for c in campaigns if c['state'] in ['ENABLED', 'PAUSED']}
print(f"Campaign 18699453817819 in active: {'18699453817819' in active_campaigns}")

# Now check targets in that campaign
body = {'startIndex': 0, 'count': 100, 'campaignIdFilter': {'include': ['18699453817819']}}
r = sp.TargetsV3(credentials=creds).list_product_targets(body=body)
targets = r.payload.get('targetingClauses', [])
print(f"Total targets in campaign 18699453817819: {len(targets)}")

# Find targets in ad group 385532260271984
ad_group_targets = [t for t in targets if t.get('adGroupId') == '385532260271984']
print(f"Targets in ad group 385532260271984: {len(ad_group_targets)}")

for t in ad_group_targets:
    print(f"\nTargetId: {t['targetId']}")
    print(f"  State: {t['state']}")
    print(f"  Bid: {t.get('bid')}")
    print(f"  Expression: {[e['type'] for e in t.get('expression', [])]}")
    
    # Check if it would be processed
    for expr in t.get('expression', []):
        expr_type = expr.get('type', '')
        if expr_type == 'QUERY_BROAD_REL_MATCHES':
            print(f"  -> loose-match, state={t['state']}, would PAUSE")
        elif expr_type == 'ASIN_ACCESSORY_RELATED':
            print(f"  -> complements, bid={t.get('bid')}, would SET_LOW_BID")
        elif expr_type == 'ASIN_SUBSTITUTE_RELATED':
            print(f"  -> substitutes, bid={t.get('bid')}, would REDUCE_BID")
        elif expr_type == 'QUERY_HIGH_REL_MATCHES':
            print(f"  -> close-match, would SKIP")