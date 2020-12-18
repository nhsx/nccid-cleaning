# content of test_sysexit.py
import pandas as pd
import pytest

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
        "notebooks/data/example_cleaned.csv", parse_dates=date_cols, dtype=dtypes
    )

    # Do actual cleaning
    df_cleaned = nc.clean_data_df(df, nc.patient_df_pipeline)

    # Test the equivalence
    pd.testing.assert_frame_equal(df_cleaned, df_target)
