# streamlit_app.py
import streamlit as st
import pandas as pd
from data_loader import get_fresh_data_if_needed

def create_dataframe():
    """Function to create the dataframe - used by both normal and CSV modes"""
    data = get_fresh_data_if_needed()
    # Convert to a DataFrame
    df = pd.DataFrame(data)
    # Assign new column types
    df['id'] = df['id'].astype('Int64')  # ensure csv is integer
    df['vtm'] = df['vtm'].astype('Int64') # ensure csv is integer
    df['vmp_previous'] = df['vmp_previous'].astype('Int64') # ensure csv is integer
    return df

# Check for CSV mode FIRST, before any other content is rendered
params = st.query_params
format_param = params.get("format")

if format_param:
    if isinstance(format_param, list):
        format_param = format_param[0]
    
    if format_param.lower() == "csv":
        # CSV mode - output only CSV data
        df = create_dataframe()
        
        # Set headers for better compatibility
        st.markdown("""
        <style>
        .stApp > header {display: none !important;}
        .stApp > .main {padding: 0 !important;}
        .stDeployButton {display: none !important;}
        .stDecoration {display: none !important;}
        footer {display: none !important;}
        .stToolbar {display: none !important;}
        </style>
        """, unsafe_allow_html=True)
        
        csv_content = df.to_csv(index=False)
        st.text(csv_content)
        st.stop()  # This prevents the rest of the app from running

# Normal app mode continues here
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

# Create the dataframe
df = create_dataframe()

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
