from typing import Any, Dict, List

import requests
import streamlit as st
from pathlib import Path

COMPANIES_HOUSE_API_KEY = "be340484-da4d-4717-b064-faa44c3fffee"
BASE_URL = "https://api.company-information.service.gov.uk"
DEFAULT_PAGE_SIZE = 20
MAX_OFFICERS = 35
MAX_FILINGS = 20
MAX_PSC = 20

PRIMARY_COLOR = "#1B4D3E"  # Positive at Work green
SECONDARY_COLOR = "#F4B400"  # Positive accent
BACKGROUND_COLOR = "#F3FAF6"
LOGO_PATH = Path(__file__).with_name("PAWLogo.png")


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


def _build_financial_table(profile: Dict[str, Any]) -> List[Dict[str, str]]:
    accounts = profile.get("accounts", {})
    next_due = accounts.get("next_due")
    last_accounts = accounts.get("last_accounts", {})
    confirmation = profile.get("confirmation_statement", {})

    return [
        {"Financial detail": "Accounts due", "Value": next_due or "N/A"},
        {"Financial detail": "Last accounts made up to", "Value": last_accounts.get("made_up_to", "N/A")},
        {"Financial detail": "Last accounts type", "Value": last_accounts.get("type", "N/A")},
        {
            "Financial detail": "Overdue accounts",
            "Value": "Yes" if accounts.get("overdue") else "No",
        },
        {
            "Financial detail": "Next confirmation statement due",
            "Value": confirmation.get("next_due", "N/A"),
        },
        {
            "Financial detail": "Has insolvency history",
            "Value": "Yes" if profile.get("has_insolvency_history") else "No",
        },
    ]


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


def _apply_branding() -> None:
    st.markdown(
        f"""
        <style>
            .stApp {{ background: linear-gradient(180deg, {BACKGROUND_COLOR} 0%, #ffffff 45%); }}
            .brand-banner {{
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 12px 16px;
                border-left: 6px solid {SECONDARY_COLOR};
                background: #ffffff;
                border-radius: 10px;
                margin-bottom: 8px;
            }}
            .brand-logo {{
                width: 42px;
                height: 42px;
                border-radius: 50%;
                background: {PRIMARY_COLOR};
                color: white;
                font-weight: 700;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .brand-title {{ color: {PRIMARY_COLOR}; font-size: 1.2rem; font-weight: 700; }}
            .stButton > button {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_logo, col_text = st.columns([1, 8])
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=56)
        else:
            st.markdown('<div class="brand-logo">PAW</div>', unsafe_allow_html=True)

    with col_text:
        st.markdown(
            """
            <div class="brand-banner">
                <div>
                    <div class="brand-title">Positive at Work</div>
                    <div>Company Intelligence Dashboard</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(page_title="Positive at Work | Company Explorer", page_icon="📈", layout="wide")
    _apply_branding()

    st.title("UK Company Explorer")
    st.caption("Search UK company data and review leadership, filing, and financial details.")

    api_key = COMPANIES_HOUSE_API_KEY

    with st.sidebar:
        st.header("Search Companies")
        search_type = st.selectbox(
            "Search by",
            ["Company name", "Post code", "Company number", "Director name"],
        )
        query = st.text_input("Enter search value")

        if st.button("Run search", type="primary", use_container_width=True):
            with st.spinner("Searching Companies House..."):
                try:
                    st.session_state["search_results"] = search_companies(search_type, query, api_key)
                    st.session_state["selected_company"] = None
                except Exception as exc:
                    st.error(str(exc))
                    st.session_state["search_results"] = []

        results = st.session_state.get("search_results", [])
        if results:
            st.success(f"Found {len(results)} match(es)")
            st.session_state["selected_company"] = st.selectbox(
                "Pick a company from search results",
                options=results,
                format_func=_company_option_label,
                key="company_picker",
            )
        elif "search_results" in st.session_state:
            st.warning("No companies found for this search.")

    selected_company = st.session_state.get("selected_company")

    if selected_company:
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

            st.markdown("### Financial Details")
            st.table(_build_financial_table(profile))

            st.markdown("### Key Information")
            st.write(
                {
                    "Incorporation date": profile.get("date_of_creation"),
                    "Registered office": _format_address(profile.get("registered_office_address", {})),
                    "SIC codes": ", ".join(profile.get("sic_codes", [])),
                    "Jurisdiction": profile.get("jurisdiction"),
                    "Can file": profile.get("can_file"),
                }
            )

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


if __name__ == "__main__":
    main()
