import os
import json
from dotenv import load_dotenv
load_dotenv(".env.local")

from ad_api.api import sp

credentials = dict(
    refresh_token=os.getenv("REFRESH_TOKEN"),
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    profile_id=os.getenv("PROFILE_ID")
)

# Get an ENABLED target
result = sp.TargetsV3(credentials=credentials).list_product_targets(body={
    "startIndex": 0, 
    "count": 1,
    "stateFilter": {"include": ["ENABLED"]}
})

target = result.payload["targetingClauses"][0]
target_id = target["targetId"]
current_state = target["state"]

print(f"Target ID: {target_id}")
print(f"Current state: {current_state}")

# Try updating to PAUSED
payload = {
    "targetingClauses": [
        {"targetId": target_id, "state": "PAUSED"}
    ]
}

print(f"Payload: {json.dumps(payload)}")

try:
    result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=payload)
    print(f"SUCCESS! Response: {json.dumps(result.payload, indent=2)}")
except Exception as e:
    print(f"FAILED: {e}")