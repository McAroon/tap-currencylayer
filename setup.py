#!/usr/bin/env python
from setuptools import setup

setup(
    name="tap-currencylayer",
    version="0.1.0",
    description="Singer.io tap for extracting currency exchange rates from https://currencylayer.com API",
    author="McAroon",
    url="https://github.com/McAroon/tap-currencylayer",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_currencylayer"],
    install_requires=[
        # NB: Pin these to a more specific version for tap reliability
        "singer-python==5.13.0",
        "requests==2.31.0",
        "backoff==1.8.0"
    ],
    entry_points="""
    [console_scripts]
    tap-currencylayer=tap_currencylayer:main
    """,
    packages=["tap_currencylayer"],
    package_data = {
        "schemas": ["tap_currencylayer/schemas/*.json"]
    },
    include_package_data=True,
)
