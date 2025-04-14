import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from google.cloud import bigquery
import os

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Load SQL from file
def load_sql(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQL file '{path}' not found!")
    with open(path, "r") as file:
        return file.read()
    
# Load your specific query
ome_sql = load_sql("sql/ome.sql")
date_sql = load_sql("sql/max_month.sql")

# Generic cached query runner
@st.cache_data
def run_query(query):
    query_job = client.query(query)
    rows = query_job.result()
    return [dict(row) for row in rows]

# Cache the latest known max(month) from last fetch
@st.cache_data
def get_cached_max_month():
    result = run_query(date_sql)
    return result[0]["max_month"]

# Main data loader that refreshes cache only when max(month) changes
def get_fresh_data_if_needed():
    # Get cached max month
    cached_max = get_cached_max_month()

    # Get current max month directly from DB (not cached)
    current_max = run_query(date_sql)[0]["max_month"]

    if current_max != cached_max:
        st.cache_data.clear()  # Invalidate all cached data
        # Re-run to re-cache everything
        data = run_query(ome_sql)
        get_cached_max_month()  # Update cached max_month
    else:
        data = run_query(ome_sql)  # Cached version used

    return data
