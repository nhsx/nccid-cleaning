import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from pydicom.dataset import Dataset
from tqdm.auto import tqdm


def select_image_files(
    base_path: Path,
    select_first: bool = True,
    select_last: bool = False,
    select_all: bool = False,
) -> List[Path]:
    """
    Selects the first, last, first & last (alphabetically), or all files
    from each image subdirectory.
    Note: `select_all=True` will override `select_first` and `select_last`.
    """
    files_to_process = []
    for dirpath, subdirlist, file_list in tqdm(
        os.walk(base_path), desc="Finding files"
    ):
        selected_files = map(
            lambda i: (select_all)
            or (select_first and (i == 0))
            or (select_last and (i == len(file_list) - 1)),
            range(len(file_list)),
        )
        files_to_process.extend(
            [
                Path(dirpath) / file
                for selected, file in zip(selected_files, sorted(file_list))
                if selected
            ]
        )

    return files_to_process


def ingest_dicom_json(file: Path) -> Dataset:
    """
    Reads in a single of json file with pydicom
    """

    with open(file, "rb") as f:
        # Read {"InlineBinary": null} as {"InlineBinary": b""}
        data = json.load(
            f,
            object_hook=lambda d: {
                k: b"" if k == "InlineBinary" and v is None else v
                for k, v in d.items()
            },
        )

    # Replace top-level nulls with empty DICOM sequences
    data = {k: {"vr": "SQ"} if v is None else v for k, v in data.items()}
    return Dataset.from_json(data)


def ingest_dicom_jsons(files: List[Path]) -> Dict[Path, Dataset]:
    """
    Reads in a list of json files with pydicom
    """

    datasets = {}
    for file in tqdm(files, desc="Reading files"):
        datasets[file] = ingest_dicom_json(file)

    return datasets


def pydicom_to_df(datasets: Dict[Path, Dataset]) -> pd.DataFrame:
    """ "
    Takes a dict of dicom dataset metadata, and turns it into a dataframe.
    """

    attributes = []
    for file, ds in datasets.items():

        # This relies on the directory structure being consistent
        pseudonym = file.parents[2].stem
        assert pseudonym.lower().startswith("covid")

        record = {"Pseudonym": pseudonym}
        record.update({attribute: ds.get(attribute) for attribute in ds.dir()})
        attributes.append(record)

    return pd.DataFrame(attributes)


def patient_jsons_to_df(files: List[Tuple]) -> pd.DataFrame:
    """
    Reads in a list of tuples containing json files and concatenates
    to a dataframe, taking the latest dated json for each.
    """

    latest_records: Dict[Path, Dict] = {}

    for dirpath, _, filelist in tqdm(files, desc="Parsing files"):
        if filelist:
            # This relies on the filename format being consistent
            file_dates = [
                datetime.strptime(
                    file.split("_")[1].split(".")[0], "%Y-%m-%d"
                ).date()
                for file in filelist
            ]

            covid_positive = any(
                [file.lower().startswith("data") for file in filelist]
            )

            file_filter = "data" if covid_positive else "status"
            filtered_file_list = [
                filename
                for filename in sorted(filelist)
                if filename.lower().startswith(file_filter)
            ]

            latest_file = Path(dirpath) / Path(filtered_file_list[-1])

            with open(latest_file, "r") as f:
                latest_record = json.load(
                    f,
                    object_hook=lambda d: dict(
                        d,
                        **d.get("OtherDataSources", {}).get(
                            "SegmentationData", {}
                        )
                    ),
                )

            latest_records[dirpath] = {
                "filename_earliest_date": min(file_dates),
                "filename_covid_status": covid_positive,
                "filename_latest_date": max(file_dates),
                **latest_record,
            }

    return pd.DataFrame(list(latest_records.values()))


def dicom_age_in_years(age_string: str):
    """Helper function to extract DICOM age into float
    Parameters
    ----------
    age_string :
        The age string as defined in the DICOM standard,see
        http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
    Returns
    -------
    float or None
        The age or None if any conversiomn went wrong.
    """
    try:
        units = age_string[-1]
        value = age_string[0:-1]
    except IndexError:
        return
    try:
        age = float(value)
    except ValueError:
        return

    if units == "Y":
        # default
        pass
    elif units == "M":
        age /= 12
    elif units == "W":
        age /= 52
    elif units == "D":
        age /= 365
    else:
        # unknown
        return
    return age


def patient_data_dicom_update(
    patients: pd.DataFrame, images: List[pd.DataFrame]
) -> pd.DataFrame:
    """Fills in missing values for Sex and Age from imaging dicom headers.
    Parameters
    ----------
    patients :
        The patient clinical DataFrame that needs filling in.
    images :
        List of image metadata Dataframes, e.g., [xrays, cts, mris].
    Returns
    -------
    pd.DataFrame
        Patient data with updated sex and age information filled in
        using the image metadata.
    """

    demo = pd.concat(
        [
            modality[["Pseudonym", "PatientSex", "PatientAge"]]
            for modality in images
        ]
    )
    demo["ParsedPatientAge"] = demo["PatientAge"].map(dicom_age_in_years)
    demo_dedup = (
        demo.sort_values("ParsedPatientAge", ascending=True)
        .drop_duplicates(subset=["Pseudonym"], keep="last")
        .sort_index()
    )

    def _fill_sex(x, df_dicom):
        sex = x["sex"]
        if sex == "Unknown":
            try:
                sex = df_dicom.loc[df_dicom["Pseudonym"] == x["Pseudonym"]][
                    "PatientSex"
                ].values[0]
            except IndexError:
                pass
        return sex

    def _fill_age(x, df_dicom):
        age = x["age"]
        if pd.isnull(age):
            try:
                age = df_dicom.loc[df_dicom["Pseudonym"] == x["Pseudonym"]][
                    "ParsedPatientAge"
                ].values[0]
            except IndexError:
                pass
        return age

    patients["age_update"] = patients.apply(
        lambda x: _fill_age(x, demo_dedup), axis=1
    )
    patients["sex_update"] = patients.apply(
        lambda x: _fill_sex(x, demo_dedup), axis=1
    )
    return patients
