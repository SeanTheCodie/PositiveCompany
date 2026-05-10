# PositiveCompany

Streamlit application for searching UK Companies House data.

## Features

- Search by **company name**
- Search by **post code / location**
- Search by **company number**
- Search by **director name**
- Choose from all matching companies in a dropdown
- View key profile details, officers, PSC, and filing history in a concise dashboard

## Run locally

1. Set your Companies House API key:
   ```bash
   export COMPANIES_HOUSE_API_KEY="your-api-key"
   ```
2. Install dependencies:
   ```bash
   pip install streamlit requests
   ```
3. Run:
   ```bash
   streamlit run "Company Searcher.py"
   ```
