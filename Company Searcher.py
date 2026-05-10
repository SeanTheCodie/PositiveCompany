import os
from typing import Any, Dict, List

import requests
import streamlit as st

COMPANIES_HOUSE_API_KEY = "be340484-da4d-4717-b064-faa44c3fffee"
api_key = "be340484-da4d-4717-b064-faa44c3fffee"
BASE_URL = "https://api.company-information.service.gov.uk"
DEFAULT_PAGE_SIZE = 20
MAX_OFFICERS = 35
MAX_FILINGS = 20
MAX_PSC = 20


@st.cache_data(show_spinner=False)
def companies_house_get(endpoint: str, api_key: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Call Companies House API and return JSON response."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params, auth=(api_key, ""), timeout=25)

    if response.status_code == 404:
        return {"items": []}

    if response.status_code != 200:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")

    return response.json()


def search_companies(search_type: str, query: str, api_key: str) -> List[Dict[str, Any]]:
    """Search companies by chosen method and return candidate company records."""
    query = query.strip()
    if not query:
        return []

    if search_type == "Company name":
        data = companies_house_get(
            "/search/companies",
            api_key,
            {"q": query, "items_per_page": DEFAULT_PAGE_SIZE},
        )
        return data.get("items", [])

    if search_type == "Company number":
        data = companies_house_get("/company/" + query.upper(), api_key)
        if data and data.get("company_number"):
            return [
                {
                    "company_name": data.get("company_name"),
                    "company_number": data.get("company_number"),
                    "address_snippet": _format_address(data.get("registered_office_address", {})),
                }
            ]
        return []

    if search_type == "Post code":
        data = companies_house_get(
            "/advanced-search/companies",
            api_key,
            {
                "location": query,
                "size": DEFAULT_PAGE_SIZE,
            },
        )
        return data.get("items", [])

    if search_type == "Director name":
        data = companies_house_get(
            "/search/officers",
            api_key,
            {"q": query, "items_per_page": DEFAULT_PAGE_SIZE},
        )
        officer_items = data.get("items", [])
        companies: Dict[str, Dict[str, Any]] = {}

        for officer in officer_items:
            for appointment in officer.get("items", []):
                appointed_to = appointment.get("appointed_to", {})
                company_number = appointed_to.get("company_number")
                if not company_number:
                    continue
                companies[company_number] = {
                    "company_name": appointed_to.get("company_name", "Unknown"),
                    "company_number": company_number,
                    "address_snippet": "",
                }

        return list(companies.values())

    return []


def _format_address(address: Dict[str, Any]) -> str:
    if not address:
        return ""

    parts = [
        address.get("address_line_1"),
        address.get("address_line_2"),
        address.get("locality"),
        address.get("region"),
        address.get("postal_code"),
        address.get("country"),
    ]
    return ", ".join([p for p in parts if p])


def _company_option_label(item: Dict[str, Any]) -> str:
    name = item.get("company_name", "Unknown company")
    number = item.get("company_number", "N/A")
    address = item.get("address_snippet") or _format_address(item.get("registered_office_address", {}))
    return f"{name} ({number}) — {address}" if address else f"{name} ({number})"


def company_details(company_number: str, api_key: str) -> Dict[str, Any]:
    """Fetch full details for selected company."""
    profile = companies_house_get(f"/company/{company_number}", api_key)
    officers = companies_house_get(
        f"/company/{company_number}/officers",
        api_key,
        {"items_per_page": MAX_OFFICERS},
    )
    filings = companies_house_get(
        f"/company/{company_number}/filing-history",
        api_key,
        {"items_per_page": MAX_FILINGS},
    )
    psc = companies_house_get(
        f"/company/{company_number}/persons-with-significant-control",
        api_key,
        {"items_per_page": MAX_PSC},
    )

    return {
        "profile": profile,
        "officers": officers.get("items", []),
        "filings": filings.get("items", []),
        "psc": psc.get("items", []),
    }


def main() -> None:
    st.set_page_config(page_title="Companies House Explorer", page_icon="🏢", layout="wide")

    st.title("🏢 Companies House Explorer")
    st.caption("Search UK company data by company name, post code, company number, or director name.")

    api_key = st.secrets.get("COMPANIES_HOUSE_API_KEY") or os.getenv("COMPANIES_HOUSE_API_KEY", "")

    if not api_key:
        st.error(
            "Missing API key. Add COMPANIES_HOUSE_API_KEY to Streamlit secrets or environment variables."
        )
        st.stop()

    search_type = st.selectbox(
        "Search by",
        ["Company name", "Post code", "Company number", "Director name"],
    )
    query = st.text_input("Enter search value")

    if st.button("Search", type="primary"):
        with st.spinner("Searching Companies House..."):
            try:
                st.session_state["search_results"] = search_companies(search_type, query, api_key)
            except Exception as exc:
                st.error(str(exc))
                st.session_state["search_results"] = []

    results = st.session_state.get("search_results", [])

    if results:
        st.success(f"Found {len(results)} possible match(es).")
        selected_company = st.selectbox(
            "Choose a company",
            options=results,
            format_func=_company_option_label,
        )

        if selected_company and st.button("Show details"):
            number = selected_company.get("company_number")
            if number:
                with st.spinner("Loading full company details..."):
                    try:
                        details = company_details(number, api_key)
                    except Exception as exc:
                        st.error(str(exc))
                        return

                profile = details["profile"]
                st.subheader(profile.get("company_name", "Company"))

                col1, col2, col3 = st.columns(3)
                col1.metric("Company Number", profile.get("company_number", "N/A"))
                col2.metric("Status", profile.get("company_status", "N/A").replace("-", " ").title())
                col3.metric("Type", profile.get("type", "N/A").replace("-", " ").title())

                st.markdown("### Key Information")
                st.write({
                    "Incorporation date": profile.get("date_of_creation"),
                    "Registered office": _format_address(profile.get("registered_office_address", {})),
                    "SIC codes": ", ".join(profile.get("sic_codes", [])),
                    "Jurisdiction": profile.get("jurisdiction"),
                    "Can file": profile.get("can_file"),
                })

                st.markdown("### Officers")
                if details["officers"]:
                    st.dataframe(
                        [
                            {
                                "Name": o.get("name"),
                                "Role": o.get("officer_role"),
                                "Appointed": o.get("appointed_on"),
                                "Country": o.get("country_of_residence"),
                            }
                            for o in details["officers"]
                        ],
                        use_container_width=True,
                    )
                else:
                    st.info("No officers returned.")

                st.markdown("### Persons with Significant Control")
                if details["psc"]:
                    st.dataframe(
                        [
                            {
                                "Name": p.get("name"),
                                "Kind": p.get("kind"),
                                "Notified": p.get("notified_on"),
                                "Nature of control": ", ".join(p.get("natures_of_control", [])),
                            }
                            for p in details["psc"]
                        ],
                        use_container_width=True,
                    )
                else:
                    st.info("No PSC records returned.")

                st.markdown("### Recent Filing History")
                if details["filings"]:
                    st.dataframe(
                        [
                            {
                                "Date": f.get("date"),
                                "Type": f.get("type"),
                                "Description": f.get("description"),
                            }
                            for f in details["filings"]
                        ],
                        use_container_width=True,
                    )
                else:
                    st.info("No filing history returned.")

    elif "search_results" in st.session_state:
        st.warning("No companies found for this search.")


if __name__ == "__main__":
    main()
