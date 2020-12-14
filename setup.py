import setuptools

setuptools.setup(
    name="nccid_cleaning",
    version="0.1.0",
    description="Cleaning pipeline for the the National"
        + "COVID-19 Chest Imaging Database (NCCID) clinical data.",
    author="Faculty",
    author_email="info@faculty.ai",
    url="",
    packages=setuptools.find_packages(),
    install_requires=["pydicom", "pandas", "tqdm"],
    extras_require={
        "notebooks": [
            "jupyter",
            "cufflinks==0.17.3",
            "plotly==4.12.0",
            "matplotlib==3.3.2",
            "kaleido==0.0.3.post1",
            "pandas==1.14.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6'
)
