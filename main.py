import hubspot
from pprint import pprint
from hubspot.crm.companies import ApiException


# Api request to get basic info about a company
client = hubspot.Client.create(
    access_token="pat-na1-ab8abc62-73ab-47d1-afdc-200f40377d44"
)

try:
    api_response = client.crm.companies.basic_api.get_page(
        limit=1,
        properties=[
            "hs_object_id",
            "name",
            "client_company_location_id",
            "client_parent_location_id",
            "imported_company_name",
        ],
        archived=False,
    )
    pprint(api_response)
except ApiException as e:
    print("Exception when calling basic_api->get_page: %s\n" % e)
