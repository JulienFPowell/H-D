import hubspot
import json
import requests
from pprint import pprint
from hubspot.crm.companies import (
    ApiException,
    BatchInputSimplePublicObjectBatchInput,
)

# Updates all company names to their imported company name
# using the list returned by get_all_companies
def batch_update_company_names(companies_to_update):

    client = hubspot.Client.create(
        access_token="pat-na1-ab8abc62-73ab-47d1-afdc-200f40377d44"
    )

    batch_input_simple_public_object_batch_input = (
        BatchInputSimplePublicObjectBatchInput(inputs=companies_to_update)
    )
    try:
        api_response = client.crm.companies.batch_api.update(
            batch_input_simple_public_object_batch_input=batch_input_simple_public_object_batch_input
        )
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling batch_api->update: %s\n" % e)


# Get the basic info required for all companies
def get_all_companies(page_mark, company_list):

    # Api request to get basic info about a company
    client = hubspot.Client.create(
        access_token="pat-na1-ab8abc62-73ab-47d1-afdc-200f40377d44"
    )

    try:
        api_response = client.crm.companies.basic_api.get_page(
            limit=100,
            after=page_mark,
            properties=[
                "hs_object_id",
                "name",
                "client_company_location_id",
                "client_parent_company_id",
                "imported_company_name",
            ],
            archived=False,
        )
        response = api_response

        # Batch updates only support 100 items at a time
        # So we reset the list we are sending to it and repopulate it
        # with the new values every call
        companies_to_update = []
        # Add each company to a dictionary, as the response limit per query is 100 items
        # it will continue to call the function until all companies have been returned
        for company in response.results:
            company_list[company.properties["hs_object_id"]] = company.properties
            # Format the list into what batch_update expects
            companies_to_update.append(
                {
                    "properties": {"name": company.properties["imported_company_name"]},
                    "id": company.properties["hs_object_id"],
                }
            )

        # Check if final company has been returned, if not calls function again
        if response.paging is None:
            # batch_update can only handle 100 items at a time
            # Sends list of all companies retrieved in this API call
            batch_update_company_names(companies_to_update)
            return company_list
        else:
            # Set record id to start at for next API query
            page_mark = response.paging.next.after
            # batch_update can only handle 100 items at a time
            # Sends list of all companies retrieved in this API call
            batch_update_company_names(companies_to_update)
            get_all_companies(page_mark, company_list)

    except ApiException as e:
        print("Exception when calling basic_api->get_page: %s\n" % e)


# Returns a dictionary with company location id : company name
# This dictionary holds all the parent companies we need to make
def get_companies_to_create():
    # Create a set containing all parent company ids that need to be created
    companies_to_create = {}
    parent_companies = []
    for companyId in company_list:
        if (  # Check if company is a child
            company_list[companyId]["client_parent_company_id"] is not None
        ):
            if (
                # If values do not match then company is a child company
                company_list[companyId]["client_parent_company_id"]
                != company_list[companyId]["client_company_location_id"]
            ):

                # Create a dictionary containing
                # all parent company ids that need to be created
                companies_to_create.update(
                    # The parent company id is used as the key to avoid duplicates
                    {
                        company_list[companyId][
                            "client_parent_company_id"
                        ]: company_list[companyId]["name"]
                    }
                )
        else:
            # If it is none that means company is already a parent
            parent_companies.append(
                company_list[companyId]["client_company_location_id"]
            )

    # Remove all companies that are already parent companies
    for parent in parent_companies:
        companies_to_create.pop(parent)

    # The final list represents all parent companies we need to create
    return companies_to_create


# Create a parent for an existing company using details from that company
# Would have done as batch but that is not available currently with new api
def create_company(companies_to_create):

    for company in companies_to_create:
        url = "https://api.hubapi.com/companies/v2/companies"

        payload = json.dumps(
            {
                "properties": [
                    {
                        "name": "name",
                        "value": companies_to_create[company] + " (Parent)",
                    },
                    {
                        "name": "client_company_location_id",
                        "value": company,
                    },
                ]
            }
        )
        headers = {
            "Content-Type": "application/json",
            "authorization": "Bearer pat-na1-ab8abc62-73ab-47d1-afdc-200f40377d44",
        }

        requests.request("POST", url, data=payload, headers=headers)


# Assigns companies as children of their parent companies
def assign_child_companies(company_list):

    for child_id in company_list:
        for parent_id in company_list:
            # Match child_id with its parent_id
            if (
                company_list[child_id]["client_parent_company_id"]
                == company_list[parent_id]["client_company_location_id"]
            ):
                url = (
                    "https://api.hubapi.com/crm/v4/objects/company/"
                    + child_id  # ID of the child
                    + "/associations/company/"
                    + parent_id  # ID of the parent
                )

                # association type id, 14 to make from_id a child
                # 13 to make from_id a parent
                payload = (
                    '[{"associationCategory":"HUBSPOT_DEFINED","associationTypeId":14}]'
                )
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "authorization": "Bearer pat-na1-ab8abc62-73ab-47d1-afdc-200f40377d44",
                }

                response = requests.request("PUT", url, data=payload, headers=headers)

                print(response.text)


company_list = {}
get_all_companies(1, company_list)

companies_to_create = get_companies_to_create()
create_company(companies_to_create)

assign_child_companies(company_list)
