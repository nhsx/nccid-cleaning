# content of test_sysexit.py
import numpy as np
import pandas as pd

import nccid_cleaning as nc


def test_example():
    # Load our test case and reference output
    df = pd.read_csv("notebooks/data/example.csv")

    # Some type coertion for the loaded CSV fields
    date_cols = [
        "date_of_positive_covid_swab",
        "date_of_admission",
        "swabdate",
        "latest_swab_date",
    ]
    dtypes = {
        "pmh_lung_disease": "object",
        "cxr_severity_2": "object",
        "covid_code": "object",
    }
    df_target = pd.read_csv(
        "notebooks/data/example_cleaned.csv",
        parse_dates=date_cols,
        dtype=dtypes,
    )

    # Do actual cleaning
    df_cleaned = nc.clean_data_df(df, nc.patient_df_pipeline)

    # Test the equivalence
    pd.testing.assert_frame_equal(df_cleaned, df_target)


def test_coerce_numeric_columns_when_no_values():
    val = ""
    cols = (
        "Fibrinogen  if d-dimer not performed",
        "Urea on admission",
        "O2 saturation",
        "Temperature on admission",
    )

    df = pd.DataFrame([[val for _ in range(len(cols))]], columns=cols)
    df = nc.cleaning._coerce_numeric_columns(df)
    output_cols = [col for col in df.columns if col not in cols]
    assert (df[output_cols].dtypes == 'float64').all()
