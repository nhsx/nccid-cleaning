import setuptools

setuptools.setup(
    name="nccid_cleaning",
    version="0.1.0",
    description="Cleaning pipeline for the the National"
        + "COVID-19 Chest Imaging Database (NCCID) clinical data.",
    author="NHSX",,
    url="git@github.com:nhsx/nccid-cleaning.git",
    packages=setuptools.find_packages(),
    install_requires=["pandas"],
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
    python_requires='>=3.6'
)
