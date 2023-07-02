#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", encoding='utf8') as readme:
    long_description = readme.read()

setup(
    name="signal_parser",
    version="1.1.0",
    author="G-K7, Corey Forman (digitalsleuth)",
    license="MIT",
    url="https://github.com/digitalsleuth/signal_parser",
    description="Python 3 Signal Messenger data parser",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "Flask",
        "python-dateutil",
        "sqlcipher3-binary"
    ],
    entry_points={
        "console_scripts": [
            "signal-parser = signal_parser.signal_parser:main"
        ]
    },
    package_data={'': ['README.md']}
)
