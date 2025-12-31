import requests
import json
from pprint import pprint

API_KEY = "be340484-da4d-4717-b064-faa44c3fffee"
BASE_URL = "https://api.company-information.service.gov.uk"

def get(endpoint):
    """Helper function to call Companies House API."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, auth=(API_KEY, ""))
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None
    return response.json()


def print_section(title, data):
    """Pretty-print a section of data."""
    print("\n" + "=" * 80)
    print(title.upper())
    print("=" * 80)
    pprint(data, sort_dicts=False)


def search_by_postcode_prefix(prefix):
    """
    Use the Companies House ADVANCED SEARCH endpoint to return ALL companies
    whose registered office location includes with the given value.
    Then allow the user to select one for a full lookup.
    """
    print(f"\nSearching for companies with adress matching : {prefix}")

    # Advanced search endpoint
    endpoint = (
        "/advanced-search/companies"
        f"?location={prefix}"
        "&size=5000"   # maximum allowed by API
    )

    results = get(endpoint)

    if not results or "items" not in results:
        print("No results found.")
        return

    companies = results["items"]

    if not companies:
        print("\nNo companies matched the postcode prefix.")
        return

    print("\n" + "=" * 80)
    print(f"COMPANIES WITH POSTCODE PREFIX '{prefix}'")
    print("=" * 80)

    for i, c in enumerate(companies, start=1):
        print(f"{i}. {c['company_name']} — {c['company_number']} ({c['registered_office_address'].get('postal_code', '')})")

    print("\nEnter the number of the company you want to look up:")
    choice = input("> ")

    try:
        choice = int(choice)
        if choice < 1 or choice > len(companies):
            print("Invalid selection.")
            return
    except ValueError:
        print("Please enter a valid number.")
        return

    selected = companies[choice - 1]
    print(f"\n✅ You selected: {selected['company_name']} ({selected['company_number']})")

    lookup_company(selected["company_number"])
    
def lookup_company(company_number):
    print(f"\nFetching Companies House data for: {company_number}")

    # 1. Company Profile
    profile = get(f"/company/{company_number}")
    print_section("Company Profile", profile)

    if not profile:
        return

    # 2. Officers
    officers = get(f"/company/{company_number}/officers")
    print_section("Officers", officers)

    # 3. Filing History
    filing_history = get(f"/company/{company_number}/filing-history")
    print_section("Filing History", filing_history)

    # 4. Persons with Significant Control (PSC)
    psc = get(f"/company/{company_number}/persons-with-significant-control")
    print_section("Persons With Significant Control", psc)

    # 5. Charges
    charges = get(f"/company/{company_number}/charges")
    print_section("Charges", charges)

    # 6. Registers
    registers = get(f"/company/{company_number}/registers")
    print_section("Registers", registers)

    # 7. Insolvency
    insolvency = get(f"/company/{company_number}/insolvency")
    print_section("Insolvency", insolvency)

    print("\n✅ Done.\n")


if __name__ == "__main__":
    
    while True:

        mainmenu = ["Search by Company Number", "Search by Post Code"]

        print("Company Finder\n")
        for i, option in enumerate(mainmenu, start=1):
            print(f"{i}. {option}")
        choice = input("\nChose your action : ")
        
        match choice:
            case "1":
                search_company_number = input("Enter Company Number : ")
                lookup_company(search_company_number)
            case "2":
                search_postcode = input("Enter part of address : ")
                search_by_postcode_prefix(search_postcode)
            case _:
                break
