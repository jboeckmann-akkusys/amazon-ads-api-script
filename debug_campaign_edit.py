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

# Check what campaign fields we can edit for SP (not SB)
TARGET_CID = "18699453817819"

print(f"Getting campaign {TARGET_CID} full details...")

result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
campaigns = result.payload.get('campaigns', [])

target = None
for c in campaigns:
    if str(c.get('campaignId')) == TARGET_CID:
        target = c
        break

if target:
    print("\nCampaign properties available:")
    for key, value in target.items():
        print(f"  {key}: {value}")
    
    # Try to update - which fields can we change?
    print("\n" + "=" * 60)
    print("Checking if we can edit this campaign...")
    
    # Try edit budget
    edit_body = {
        "campaigns": [{
            "campaignId": TARGET_CID,
            "budget": {"budget": 60.0, "budgetType": "DAILY"}
        }]
    }
    
    try:
        result = sp.CampaignsV3(credentials=credentials).edit_campaigns(body=edit_body)
        print(f"Edit budget result: {result.payload}")
        
        # Set back
        edit_body["campaigns"][0]["budget"] = {"budget": 50.0, "budgetType": "DAILY"}
        result = sp.CampaignsV3(credentials=credentials).edit_campaigns(body=edit_body)
        print(f"Reset budget: {result.payload}")
    except Exception as e:
        print(f"Budget edit error: {e}")

# Try dynamicBidding
    print("\n" + "=" * 60)
    print("Trying to edit dynamicBidding...")
    
    edit_body = {
        "campaigns": [{
            "campaignId": TARGET_CID,
            "dynamicBidding": {"strategy": "LEGACY_FOR_SALES"}
        }]
    }
    
    try:
        result = sp.CampaignsV3(credentials=credentials).edit_campaigns(body=edit_body)
        print(f"Edit dynamicBidding result: {result.payload}")
    except Exception as e:
        print(f"dynamicBidding error: {e}")