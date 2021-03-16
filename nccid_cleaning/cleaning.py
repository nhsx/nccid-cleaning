import re
from typing import Callable, Collection, Optional

import numpy as np
import pandas as pd
import json

# Mapping can be found in the submission spreadsheet
# https://medphys.royalsurrey.nhs.uk/nccid/guidance/COVID-19_NCCID_covid_positive_data_template_v1_5.xlsx

# Category maps
with open("../data/category_maps.json", "r") as f:
    category_maps = json.load(f)

_ETHNICITY_MAPPING = category_maps["ethnicity"]
_ETHNICITY_MAPPING = {k.lower(): v for k, v in _ETHNICITY_MAPPING.items()}
_ETHNICITY_MAPPING.update({v.lower(): v for v in set(_ETHNICITY_MAPPING.values())})
_ETHNICITY_MAPPING.update({np.nan: "Unknown"})

_SEX_MAPPING = category_maps["sex"]
_SEX_MAPPING = {k.lower(): v for k, v in _SEX_MAPPING.items()}
_SEX_MAPPING.update({v.lower(): v for v in set(_SEX_MAPPING.values())})
_SEX_MAPPING.update({np.nan: "Unknown"})

_TEST_RESULT_MAPPING = category_maps["test_results"]
_TEST_RESULT_MAPPING.update({0: "Negative", 1: "Positive"})

_US_DATE_COLS = [
    "Date of Positive Covid Swab",
    "Date of acquisition of 1st RT-PCR",
    "Date of acquisition of 2nd RT-PCR",
    "Date of result of 1st RT-PCR",
    "Date of result of 2nd RT-PCR",
    "Date of admission",
    "Date of ITU admission",
    "Date of intubation",
    "Date of 1st CXR",
    "Date of 2nd CXR",
    "Date last known alive",
    "Date of death",
]

def _clean_name(name: str) -> str:
    """
    Returns name of new cleaned column. Cleaned columns names are fully
    lowercase, whitespace is replaced with underscores, and commas are removed. 
    """
    return name.lower().replace(" ", "_").replace(",", "")

def _remap_ethnicity(patients_df: pd.DataFrame) -> pd.DataFrame:
    """
    Remap ethnicities to standardised groupings.
    """
    _ETHNICITY_MAPPING.update(
        {
            e.lower(): "Multiple"
            for e in patients_df["Ethnicity"].unique()
            if "mixed" in str(e).lower() or "multiple" in str(e).lower()
        }
    )
    _ETHNICITY_MAPPING.update(
        {
            e.lower(): "White"
            for e in patients_df["Ethnicity"].unique()
            if "white" in str(e).lower()
        }
    )
    _ETHNICITY_MAPPING.update(
        {
            str(e).lower(): "Unknown"
            for e in patients_df["Ethnicity"].unique()
            if str(e).lower() not in _ETHNICITY_MAPPING
        }
    )

    try:
        patients_df["ethnicity"] = (
            patients_df["Ethnicity"].str.lower().replace(_ETHNICITY_MAPPING)
        )
    except AttributeError:
        # If the column is all empty, the .str call would break as non-string is inferred
        pass

    return patients_df


def _remap_sex(patients_df: pd.DataFrame) -> pd.DataFrame:
    """
    Remap sex to F/M/Unknown
    """
    try:
        patients_df["sex"] = (
            patients_df["Sex"]
            .str
            .lower()
            .map(_SEX_MAPPING)
            .replace({np.nan:"Unknown"})
            )
    except AttributeError:
        # If the column is all empty, the .str call would break as non-string is inferred
        pass

    return patients_df


def _coerce_numeric_columns(patients_df: pd.DataFrame) -> pd.DataFrame:
    """
    Force fields to be numeric
    """

    def _extract_clinical_values(x, kind="single") -> float:
        """
        Extracts data from known errors in BP entries
        """

        if x.replace(".", "", 1).isnumeric():
            return float(x)

        elif kind == "single":
            # check for known error pattern "[#value] - 2020-03-04"
            match_error = re.search(r"\[(\d+\.?\d+)\]", x)
            if match_error:
                return float(match_error.group(1))
        else:
            # Or "[170/70] - 2020-03-04" for blood pressure values
            match_error = re.search(
                r"\[(?P<systolic>\d{2,3})/(?P<diastolic>\d{2,3})\]", x
            )
            if match_error and kind == "systolic":
                return float(match_error.group("systolic"))
            elif match_error and kind == "diastolic":
                return float(match_error.group("diastolic"))

    # standard clinical columns to be cleaned
    clinical_columns = (
        "Duration of symptoms",
        "Respiratory rate on admission",
        "Heart rate on admission",
        "NEWS2 score on arrival",
        "APACHE score on ITU arrival",
        "PaO2",
        "Creatinine on admission",
        "D-dimer on admission",  # units vary between sites
        "Fibrinogen  if d-dimer not performed",
        "WCC on admission",
        "Lymphocyte count on admission",
        "Platelet count on admission",
        "CRP on admission",  # mg/L large variance expected
        "Urea on admission",  # units vary ng/ml vs mmol/L
        "O2 saturation",
        "Temperature on admission",
        "Ferritin",  # most sites use ug/L
        "Troponin I",  # sites vary between ng/L and ng/ml
        "Troponin T",  # not widely used by sites
    )
    for col in [col for col in clinical_columns if col in patients_df]:
        patients_df[_clean_name(col)] = patients_df[col].map(
            lambda x: _extract_clinical_values(str(x), kind="single")
        )
    # blood pressure columns
    if "Systolic BP" in patients_df:
        patients_df["systolic_bp"] = patients_df["Systolic BP"].map(
            lambda x: _extract_clinical_values(str(x), kind="systolic")
        )
    if "Diastolic BP" in patients_df:
        patients_df["diastolic_bp"] = patients_df["Diastolic BP"].map(
            lambda x: _extract_clinical_values(str(x), kind="diastolic")
        )

    # age (round to nearest year)
    if "Age" in patients_df:
        patients_df["age"] = pd.to_numeric(patients_df["Age"], errors="coerce").apply(
            np.floor
        )

    return patients_df


def _clip_numeric_values(patients_df: pd.DataFrame) -> pd.DataFrame:
    """Removed values outside of expected limits.
    Can only be called after _coerce_numeric_columns.
    """
    # remove values outside reasonable range where range is known
    if "temperature_on_admission" in patients_df:
        # expected in celcius so clipped to 25- 45
        patients_df["temperature_on_admission"] = patients_df[
            "temperature_on_admission"
        ].apply(lambda x: x if 25 <= x <= 45 else np.nan)

    # expected in the 0-100 range
    cols100range = [
        "fibrinogen__if_d-dimer_not_performed",
        "urea_on_admission",
        "o2_saturation",
    ]
    for col in [col for col in cols100range if col in patients_df]:
        patients_df[col] = patients_df[col].map(
            lambda x: x if 0 <= x <= 100 else np.nan
        )

    return patients_df


def _parse_date_columns(patients_df: pd.DataFrame) -> pd.DataFrame:
    def _clean_us_dates(x: str) -> pd.datetime:
        """Converts fields expected in US date format MM/DD/YY
        into pd.datetime dates. Dates are pulled out from entries with
        known errors of the form '[Text] - YYYY-MM-DD'.
        Other known errors e.g., '.', ' ',
        and unknown errors are parsed as pd.NaT"""

        _x = pd.NaT
        if isinstance(x, str):
            # Look for expected date patterns MM/DD/YY or MM/DD/YYYY to datetime
            match_standard = re.search(
                r"\d{1,2}/\d{1,2}/\d{2,4}",
                x,
            )
            if match_standard:
                # Coerce into US date format
                _x = pd.to_datetime(
                    match_standard.group(), dayfirst=False, errors="coerce"
                )
            else:
                # Look for known error date patterns
                match_error = re.search(r"\d{4}-\d{2}-\d{2}", x)
                if match_error:
                    _x = pd.to_datetime(match_error.group(), errors="coerce")

        return _x

    # Cleaning and preprocessing for columns expected in US style dates -
    # https://nhsx.github.io/covid-chest-imaging-database/faq.html
    for col in [col for col in _US_DATE_COLS if col in patients_df]:
        patients_df[_clean_name(col)] = patients_df[col].map(
            lambda x: _clean_us_dates(x)
        )

    # Parsing of columns expected in UK style dates
    if "SwabDate" in patients_df:
        patients_df["swabdate"] = pd.to_datetime(
            patients_df["SwabDate"], dayfirst=True, errors="coerce"
        )
    
        # Calculate the latest swab date
        if "swabdate" and "date_of_positive_covid_swab" in patients_df:
            patients_df["latest_swab_date"] = pd.concat(
                [
                    patients_df["date_of_positive_covid_swab"],
                    patients_df["swabdate"],
                ],
                axis=1,
            ).max(axis=1)
    
        return patients_df


def _parse_binary_columns(patients_df: pd.DataFrame) -> pd.DataFrame:

    # 'Unknown' mapped to NaN
    binary_columns = (
        "PMH hypertension",
        "PMH CKD",
        "Current ACEi use",
        "Current Angiotension receptor blocker use",
        "Current NSAID used",
        "ITU admission",
        "Intubation",
        "Death",
    )

    for col in [col for col in binary_columns if col in patients_df]:
        patients_df[_clean_name(col)] = patients_df[col].map(
            {0: False, "0": False, "0.0": False, 1: True, "1": True, "1.0": True}
        )

    # map and merge 'PMH h1pertension column'
    if "PMH h1pertension" in patients_df:
        patients_df["pmh_hypertension"] = patients_df["pmh_hypertension"].fillna(
            patients_df["PMH h1pertension"].map({"1": True, "1es": True})
        )

    # merge old column and map to binary
    # not merging 'PMH diabetes mellitus TYPE I'
    # because only 12 entries and accuracy uncertain
    if "PMH diabetes mellitus type II" in patients_df:
        patients_df["pmh_diabetes_mellitus_type_2"] = patients_df[
            "PMH diabetes mellitus type II"
        ].copy()
        if "PMH diabetes mellitus TYPE II" in patients_df:
            # Fill in from capitalised original field, see "TYPE" instead of "type"
            patients_df["pmh_diabetes_mellitus_type_2"] = patients_df[
                "pmh_diabetes_mellitus_type_2"
            ].fillna(patients_df["PMH diabetes mellitus TYPE II"])
        # finish up remapping
        patients_df["pmh_diabetes_mellitus_type_2"] = patients_df[
            "pmh_diabetes_mellitus_type_2"
        ].map({0: False, "0": False, "0.0": False, 1: True, "1": True, "1.0": True})

    return patients_df


def _parse_cat_columns(patients_df: pd.DataFrame) -> pd.DataFrame:

    if "Pack year history" in patients_df:
        # Remove known errors such as ' '
        patients_df["pack_year_history"] = patients_df["Pack year history"].str.extract(
            r"(\d+)"
        )

    # strip digits from strings and exclude values outside of schema
    # "Unknown" categories mapped to nan if they exist
    schema_values = {
        "Smoking status": ["0", "1", "2"],
        "If CKD, stage": ["2", "3", "4", "5"],
        "PMH CVS disease": ["0", "1", "2", "3", "4"],
        "PMH Lung disease": ["0", "1", "2", "3", "4", "5"],
        "CXR severity": ["1", "2", "3"],
        "CXR severity 3": ["1", "2", "3"],
        "COVID CODE": ["0", "1", "2", "3"],
        "COVID CODE 2": ["0", "1", "2", "3"],
    }
    for col in [col for col in schema_values.keys() if col in patients_df]:
        new_col = _clean_name(col)
        patients_df[new_col] = patients_df[col].astype(str).str.extract(r"(\d+)")
        patients_df[new_col] = patients_df[new_col].loc[
            patients_df[new_col].isin(schema_values[col])
        ]

    return patients_df


def _remap_test_result_columns(patients_df: pd.DataFrame) -> pd.DataFrame:

    # maps entries of 'RNA DETECTED (SARS-CoV-2)' to positive
    result_columns = ("1st RT-PCR result", "2nd RT-PCR result", "Final COVID Status")

    for col in [col for col in result_columns if col in patients_df]:
        patients_df[_clean_name(col)] = patients_df[col].map(
            _TEST_RESULT_MAPPING
        )
    return patients_df


def _rescale_fio2(patients_df: pd.DataFrame) -> pd.DataFrame:
    """Remaps FiO2 entries to the % scale."""

    def _fiO2_mapping(x: str) -> Optional[int]:
        values_to_percentage = {
            "1": "25",
            "2": "29",
            "3": "33",
            "4": "37",
            "5": "41",
            "6": "45",
            "7": "41",
            "8": "47",
            "9": "53",
            "10": "60",
            "11": "80",
            "12": "85",
            "13": "90",
            "14": "95",
            "15": "100",
            "blue": "24",
            "white": "28",
            "orange": "31",
            "yellow": "35",
            "red": "40",
            "green": "60",
        }
        _x = x
        if "." in x:
            # decimal entries are converted to percentages
            # put inside 'try' to catch edge cases such as "."
            try:
                _x = str(round(float(x) * 100))
            except ValueError:
                _x = None
        elif "l" in x.lower():
            try:
                _x = values_to_percentage[x.lower().rstrip("l")]
            except KeyError:
                _x = None
        elif x in values_to_percentage.keys():
            _x = values_to_percentage[str(x)]

        # makes sure new value is in % value range
        if _x.isdigit() and 0 <= int(_x) <= 100:
            return int(_x)
        else:
            return None

    if "FiO2" in patients_df:
        patients_df["fio2"] = patients_df["FiO2"].map(lambda x: _fiO2_mapping(str(x)))
    return patients_df


def _fix_headers(patients_df: pd.DataFrame) -> pd.DataFrame:
    """Fixes known mistakes in column headers.
    Should always be run last as it acts on the cleaned columns.
    """
    if "cxr_severity_3" in patients_df:
        patients_df.rename(
            columns={"cxr_severity_3": "cxr_severity_2"},
            inplace=True,
        )

    return patients_df


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
    _fix_headers,
)


def clean_data_df(
    data_df: pd.DataFrame,
    cleaning_pipeline: Collection[Callable],
) -> pd.DataFrame:
    """
    Run the data through a list of cleaning functions with signature
    f(pd.DataFrame) -> pd.DataFrame
    """

    for cleaning_function in cleaning_pipeline:
        data_df = data_df.pipe(cleaning_function)

    return data_df
