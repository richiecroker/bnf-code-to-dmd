# streamlit_app.py

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid
from google.oauth2 import service_account
from google.cloud import bigquery

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

# Full Width Table
st.set_page_config(layout="wide")  # This ensures the layout is wide and takes the full screen
client = bigquery.Client(credentials=credentials)
st.title("OpenPrescribing Oral Morphine Equivalence list")
st.markdown("""
In 2017 we created a [tool to show the total Oral Morphine Equivalence (OME)](https://openprescribing.net/measure/opioidome/national/england/) of prescribing in practices, and [published a paper to describe our findings](https://www.thelancet.com/journals/lanpsy/article/PIIS2215-0366%2818%2930471-1/abstract).

Originally we create a spreadsheet and manually mapped drugs at BNF presentation level to the appropriate OME value.  Since then some of the OME values have changed, and new products were not included, and so we moved a dictionary of medicines + devices (dm+d) based automatic calculation instead, which uses a map at [ingredient and route level](https://github.com/bennettoxford/openprescribing/blob/main/openprescribing/measures/tables/opioid_ing_form_ome.csv).  However, this means that the OME value for each product is no longer openly available.  

A full methodology on the new OME calculations are [here](https://github.com/bennettoxford/openprescribing/pull/2907).  

By using a modified version of the SQL in the method above, we can create a list of OME values at BNF presentation level.  Please note that this is a snapshot, and won't include any preparations first prescribed after January 2025.
""")

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=7 * 24 * 60 * 60)  # TTL set to 1 week
def run_query(query):
    query_job = client.query(query)
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows

sql = """
WITH simp_form AS (
  SELECT DISTINCT
    vmp, #vmp code
    CASE WHEN descr LIKE '%injection%' THEN 'injection' #creates "injection" as route, regardless of whether injection or infusion. this also removes injection routes, e.g.
    WHEN descr LIKE '%infusion%' THEN 'injection' #s/c, i/v etc, AS often injections have many licensed routes, e.g "solutioninjection.subcutaneous" AND solutioninjection.intramuscular"which would multiply the row
    WHEN descr LIKE 'filmbuccal.buccal' THEN 'film' # buccal films have a different OME and so should be indentified here
    ELSE SUBSTR(
      form.descr,
      STRPOS(form.descr, ".")+ 1) #takes the dosage form out of the string (e.g. tablet.oral) TO leave route.
    END AS simple_form
  FROM
    dmd.ont AS ont #the coded route for dosage form, includes vmp code
    INNER JOIN dmd.ontformroute AS form ON form.cd = ont.form #text description of route
    )

#subquery to normalise strength to mg
,norm_vpi AS (
    SELECT
    vpi.vmp as vmp, #vmp code
    vpi.ing as ing, #ing code
    ing.nm as nm, #ing name
    vpi.basis_strnt as basis_strnt, # strength based on ingredient (1) or base (2) substance
    vpi.bs_subid as bs_subid, # VPI code for base substance where it exists
    strnt_nmrtr_val,#numerator strength value
    strnt_nmrtr_uom,#numerator unit of measurement
    unit_num.descr as num_unit, #numerator unit
    unit_den.descr as den_unit, #denominator unit
    CASE WHEN unit_num.descr = 'microgram' THEN vpi.strnt_nmrtr_val / 1000 #creates miligram value from mcg value
    WHEN unit_num.descr = 'gram' THEN vpi.strnt_nmrtr_val * 1000 #creates miligram value from gram value
    WHEN unit_num.descr = 'mg' THEN vpi.strnt_nmrtr_val #no change if mg value
    ELSE NULL # will give a null value if a non-stanard dosage unit - this can then be checked if neccesary
    END AS strnt_nmrtr_val_mg, #all listed drugs now in miligram rather than g or mcg
    CASE WHEN unit_den.descr = 'litre' THEN vpi.strnt_dnmtr_val * 1000 #some denominators listed as litre, so create mililitre value
    WHEN unit_den.descr = 'ml' THEN vpi.strnt_dnmtr_val #no change if mililitre value
    ELSE NULL # will give a null value if a non-stanard dosage unit - this can then be checked if neccesary
    END AS strnt_dnmtr_val_ml #denominator now in ml
    FROM
    dmd.vpi AS vpi
    INNER JOIN dmd.ing AS ing ON vpi.ing = ing.id
    LEFT JOIN dmd.unitofmeasure AS unit_num ON vpi.strnt_nmrtr_uom = unit_num.cd #join to create text value for numerator unit
    LEFT JOIN dmd.unitofmeasure AS unit_den ON vpi.strnt_dnmtr_uom = unit_den.cd #join to create text value for denominator unit
)

#main query to calculate the OME
SELECT
  vpi.ing AS ing_dmd_code, #ingredient DM+D code. Combination products will have more than one ing code per VMP, e.g. co-codamol will have ing for paracetamoland codeine
  vpi.nm AS ing_name, #ingredient name
  bnf.presentation_code AS bnf_code, #BNF code to link to prescribing data
  bnf.presentation AS bnf_name, #BNF name from prescribing data
  vpi.strnt_nmrtr_val_mg, #strength numerator in mg
  vpi.strnt_dnmtr_val_ml, #strength denominator in ml 
  opioid.ome AS ome,
  SUM(
    ( CASE WHEN COALESCE(vpi.bs_subid, vpi.ing) = 373492002
      AND form.simple_form = 'transdermal' THEN (ome * vpi.strnt_nmrtr_val_mg * 72)/ coalesce(vpi.strnt_dnmtr_val_ml, 1) # creates 72 hour dose for fentanyl transdermal patches, as doses are per hour on DM+D)
      WHEN COALESCE(vpi.bs_subid, vpi.ing) = 387173000
      AND form.simple_form = 'transdermal'
      AND vpi.strnt_nmrtr_val IN (5, 10, 15, 20) THEN (ome * vpi.strnt_nmrtr_val_mg * 168)/ coalesce(vpi.strnt_dnmtr_val_ml, 1) # creates 168 hour (7 day) dose for low-dose buprenorphine patch
      WHEN COALESCE(vpi.bs_subid, vpi.ing) = 387173000
      AND form.simple_form = 'transdermal'
      AND vpi.strnt_nmrtr_val IN (35, 52.5, 70) THEN (ome * vpi.strnt_nmrtr_val_mg * 96)/ coalesce(vpi.strnt_dnmtr_val_ml, 1) # creates 96 hour dose for higher-dose buprenorphine patch
      WHEN form.simple_form = 'injection' THEN (ome * vpi.strnt_nmrtr_val_mg * vmp.udfs)/ coalesce(vpi.strnt_dnmtr_val_ml, 1) # injections need to be weighted by pack size
      ELSE (ome * strnt_nmrtr_val_mg) / coalesce(vpi.strnt_dnmtr_val_ml, 1) #all other products have usual dose - coalesce as solid dose forms do not have a denominator
      END
    )
  ) AS ome_dose
FROM
  norm_vpi AS vpi #VPI has both ING and VMP codes in the table
  INNER JOIN dmd.vmp AS vmp ON vpi.vmp = vmp.id #join to get BNF codes for both VMPs and AMPs joined indirectly TO ING.
  INNER JOIN simp_form AS form ON vmp.id = form.vmp #join to subquery for simplified administration route
  INNER JOIN measures.opioid_ing_form_ome AS opioid ON opioid.vpi = COALESCE(vpi.bs_subid, vpi.ing) AND opioid.form = form.simple_form #join to OME table, which has OME value for ING/route pairs
  INNER JOIN hscic.bnf AS bnf ON CONCAT(
    SUBSTR(bnf.presentation_code, 0, 9),
    'AA',
    SUBSTR(bnf.presentation_code,-2, 2)
  ) = CONCAT(
    SUBSTR(vmp.bnf_code, 0, 11),
    SUBSTR(vmp.bnf_code,-2, 2)
  ) #uses bnf code structure to join both branded and generic prescribing data to generic VMP codes - which stops chance of duplication of VMP/AMP names
WHERE
bnf.presentation_code NOT LIKE '0410%' #remove drugs used in opiate dependence
GROUP BY
  vpi.ing,
  vpi.nm,
  bnf.presentation_code,
  bnf.presentation,
  vpi.strnt_nmrtr_val,
  strnt_nmrtr_val_mg,
  vpi.strnt_dnmtr_val_ml,
  opioid.ome
  """

rows = run_query(sql)

# Convert to a DataFrame if not already
df = pd.DataFrame(rows)

# Assign new column names
df.columns = ['Ingredient dm+d code', 'Ingredient name', 'Presentation Code', 'Presentation name', 'Unit strength (mg)', 'Unit volume (ml)', 'OME', 'OME per unit dose']

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