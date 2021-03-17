import setuptools

setuptools.setup(
    name="nccid_cleaning",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="Cleaning pipeline for the the National"
    + "COVID-19 Chest Imaging Database (NCCID) clinical data.",
    author="NHSX",
    url="https://github.com/nhsx/nccid-cleaning",
    packages=setuptools.find_packages(),
    install_requires=["pandas", "pydicom", "tqdm"],
    extras_require={
        "notebooks": [
            "jupyter",
            "pandas==1.14.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
