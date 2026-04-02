import os

os.environ["AD_API_CLIENT_ID"] = "amzn1.application-oa2-client.8500b6baaa5e41f0bc41c1fc9d37a7db"
os.environ["AD_API_CLIENT_SECRET"] = "amzn1.oa2-cs.v1.bf5b0b4fb1c670c183350eb818bf87cdb717102b3d505d962a24cec1d266208b"
os.environ["AD_API_REFRESH_TOKEN"] = "Atzr|IwEBIPwoaMJCfCE4TjJRmVLym8xF3Ng8OvgYyyUt3LwMdw-2mYPywcCZBI-gXbzCu_jLfCslzi8jHxWFeFhb1wIlsNvlgZ-IHVVmkShgyFaNypjK2WklLwY2swtkBGoNB662hWUPuA430CrtEvL_1gUTAJYQfUSO3DcyDLEH2EXHO4ojPDr2vvC_ocUYWdze_FL_FBL2Kj8cx_D781TQ_k_VMngwaobQAFN3Wx9_9VR7mlKNOx_WTakoVdD4IQ7vg_zA-oBU4DWgLbJx92uiVMBlXRZp0R_l6oP1g6smCLY9oocTz4XOyBB9LBKC02AktGR1qFOPqJN_r47qQzuuaDoGRJYGpAgR3FfQ2x5GMZEG75J5XdK_FD3FwKhpk9cOAI6dQ1bdpugxf9sUbFXIwSWc3crF6wjiKqo2Hmeze6eRJlVA4yMzbm7o4Km8kPl4aVM0w4uPV0QrHemCJCZIRLDr7Har"

# Don't set AD_API_PROFILE_ID - pass it as credentials instead

from ad_api.api import sp
from ad_api.base import Marketplaces

credentials = {
    "client_id": "amzn1.application-oa2-client.8500b6baaa5e41f0bc41c1fc9d37a7db",
    "client_secret": "amzn1.oa2-cs.v1.bf5b0b4fb1c670c183350eb818bf87cdb717102b3d505d962a24cec1d266208b",
    "refresh_token": "Atzr|IwEBIPwoaMJCfCE4TjJRmVLym8xF3Ng8OvgYyyUt3LwMdw-2mYPywcCZBI-gXbzCu_jLfCslzi8jHxWFeFhb1wIlsNvlgZ-IHVVmkShgyFaNypjK2WklLwY2swtkBGoNB662hWUPuA430CrtEvL_1gUTAJYQfUSO3DcyDLEH2EXHO4ojPDr2vvC_ocUYWdze_FL_FBL2Kj8cx_D781TQ_k_VMngwaobQAFN3Wx9_9VR7mlKNOx_WTakoVdD4IQ7vg_zA-oBU4DWgLbJx92uiVMBlXRZp0R_l6oP1g6smCLY9oocTz4XOyBB9LBKC02AktGR1qFOPqJN_r47qQzuuaDoGRJYGpAgR3FfQ2x5GMZEG75J5XdK_FD3FwKhpk9cOAI6dQ1bdpugxf9sUbFXIwSWc3crF6wjiKqo2Hmeze6eRJlVA4yMzbm7o4Km8kPl4aVM0w4uPV0QrHemCJCZIRLDr7Har",
    "profile_id": "ENTITYP6KKDRTLO1AG"
}

result = sp.CampaignsV3(
    account="default",
    marketplace=Marketplaces.EU,
    credentials=credentials,
    verify_additional_credentials=False
).list_campaigns(body={})

print("Success!")
print(result)