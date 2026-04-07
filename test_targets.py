import os
import json
from dotenv import load_dotenv
load_dotenv(".env.local")

from ad_api.api import sp

credentials = dict(
    refresh_token=os.getenv("REFRESH_TOKEN"),
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    profile_id="2511423595502144"
)

body = {
    "startIndex": 0,
    "count": 100
}

result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
clauses = result.payload.get("targetingClauses", [])

# Find all unique expression types
types_found = set()
for clause in clauses:
    for expr in clause.get("expression", []):
        types_found.add(expr.get("type", ""))

print("Expression types found:")
for t in sorted(types_found):
    print(f"  - {t}")

# Also check states
states = set(clause.get("state", "") for clause in clauses)
print(f"\nStates: {states}")

# Find specific auto types
auto_types = {"QUERY_HIGH_REL_MATCHES": "close-match", "QUERY_BROAD_REL_MATCHES": "loose-match", 
             "ASIN_SUBSTITUTE_REL": "substitutes", "ASIN_ACCESSORY_REL": "complements"}

target_types = {}
for t, name in auto_types.items():
    count = sum(1 for c in clauses for e in c.get("expression", []) if e.get("type") == t)
    if count:
        target_types[name] = count

print(f"\nAuto target types found: {target_types}")