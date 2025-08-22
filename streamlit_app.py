# streamlit_app.py

import streamlit as st
import pandas as pd
from data_loader import get_fresh_data_if_needed


# Full Width Table
st.set_page_config(layout="wide")  # This ensures the layout is wide and takes the full screen


st.title("Mapping BNF codes to dm+d")
st.markdown(
"""
We have had a request from NHS England:

>Our initial need is to have a reference file that can be used to map data in BNF code form (from NHS BSA) to drug information in dm+d (SNOMED) form (at VMP/AMP level but also with VTM information).

We hold this information in the BQ database, and should be able to create a query to deliver this need.
"""
)


data = get_fresh_data_if_needed()

# Convert to a DataFrame
df = pd.DataFrame(data)


# Assign new column types

df['id'] = df['id'].astype('Int64')  # ensure csv is integer
df['vtm'] = df['vtm'].astype('Int64') # ensure csv is integer
df['vmp_previous'] = df['vmp_previous'].astype('Int64') # ensure csv is integer

# Show an interactive, filterable table
st.dataframe(df, use_container_width=True, hide_index=True)

# Function to convert the dataframe to CSV and return it as a downloadable link
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Download button
csv = convert_df_to_csv(df)
st.download_button(
    label="Download BNF code to dm+d as CSV",
    data=csv,
    file_name="bnf_code_to_dmd_map.csv",
    mime="text/csv",
)


# --- direct feed ---
query_params = st.query_params
if query_params.get("format") == "csv":
    # Output CSV text only, no Streamlit UI, no index
    st.text(df.to_csv(index=False))
    st.stop()
