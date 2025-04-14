# streamlit_app.py

import streamlit as st
import pandas as pd
from data_loader import get_fresh_data_if_needed


# Full Width Table
st.set_page_config(layout="wide")  # This ensures the layout is wide and takes the full screen


st.title("OpenPrescribing Oral Morphine Equivalence list")
st.markdown(
"""
In 2017 we created a [tool to show the total Oral Morphine Equivalence (OME)](https://openprescribing.net/measure/opioidome/national/england/) of prescribing in practices, and [published a paper to describe our findings](https://www.thelancet.com/journals/lanpsy/article/PIIS2215-0366%2818%2930471-1/abstract).

Originally we created a spreadsheet and manually mapped drugs at BNF presentation level to the appropriate OME value.  Since then some of the OME values have changed, and new products were not included, and so we moved to using a dictionary of medicines + devices (dm+d) based automatic calculation instead, which uses a map at [ingredient and route level](https://github.com/bennettoxford/openprescribing/blob/main/openprescribing/measures/tables/opioid_ing_form_ome.csv).  However, this means that the OME value for each product is no longer openly available.  

A full methodology on the new OME calculations are [here](https://github.com/bennettoxford/openprescribing/pull/2907).  

By using a modified version of the SQL in the method above, we can create a list of OME values at BNF presentation level. You can filter by opioid ingredient, or download the whole list by clicking on the button below the table.
"""
)


data = get_fresh_data_if_needed()

# Convert to a DataFrame
df = pd.DataFrame(data)

# Assign new column names
df.columns = ['Ingredient dm+d code', 'Ingredient name', 'Presentation Code', 'Presentation name', 'Unit strength (mg)', 'Unit volume (ml)', 'OME', 'OME per unit dose']
df = df.sort_values(by=["Ingredient name", "Presentation name"], ascending=[True, True])

# Filter by ingredient (dropdown)
selected_ing = st.selectbox("Filter by opioid ingredient", ["All"] + list(df["Ingredient name"].unique()))
# Apply Filters
filtered_df = df[
    ((df["Ingredient name"] == selected_ing) | (selected_ing == "All"))
]
# Show an interactive, filterable table
st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# Function to convert the dataframe to CSV and return it as a downloadable link
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Download button
csv = convert_df_to_csv(df)
st.download_button(
    label="Download whole table as CSV",
    data=csv,
    file_name="OpenPrescribing OME values.csv",
    mime="text/csv",
)