# NCCID Cleaning

This package contains the cleaning pipeline for the National COVID Chest Imaging Database (NCCID) clinical data. 

For an overview of the NCCID and available data please visit the [NCCID website](https://nhsx.github.io/covid-chest-imaging-database/#). Further technical details on the database, including full documentation of the clinical data, its known issues, and the recommended preprocessing steps implemented in the cleaning pipeline, are provided via the [HDRUK portal](https://web.www.healthdatagateway.org/dataset/31f0148b-f965-4136-ab39-6c5bbbf8c2d9).

### Installation

```python
git clone https://github.com/nhsx/nccid-cleaning.git
cd nccid-cleaning
pip install .
```

### Running 
To run the cleaning pipeline execute the following code:
```python
from nccid_cleaning import clean_data_df, patient_df_pipeline
df = clean_data_df(df, patient_df_pipeline)
```
The function `clean_data_df` is designed to act on a Pandas DataFrame, containing some or all of the clinical data fields as columns, and 1 or more patients as rows.

The full cleaning pipeline can be called using the imported Collection `patient_df_pipeline` which includes the following functions:
```python
patient_df_pipeline = (
    _remap_ethnicity,
    _remap_sex,
    _coerce_numeric_columns,
    _clip_numeric_values,
    _parse_date_columns,
    _parse_binary_columns,
    _parse_cat_columns,
    _remap_test_result_columns,
    _rescale_fio2,
    _fix_headers
)
```
Alternatively, pass the subset of functions that meet your specific needs. For example, if you wish to use a custom ethnicity mapping, `_remap_ethnicity` can be removed.

Rather than replacing the original data the pipeline creates new columns with lowercase and underscored names. Thus, the clean version of `Date of admission` becomes `date_of_admission`, and `Age` becomes `age`

An example, including further details of the cleaning steps is provided in `notebooks/example_cleaning_pipeline.ipynb`.
