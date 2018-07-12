# -*- coding: utf-8 -*-

from setuptools import find_packages, setup


with open("README.rst", "rb") as fp:
    LONG_DESCRIPTION = fp.read().decode("utf-8").strip()


setup(
    name="dump2polarion",
    use_scm_version=True,
    url="https://github.com/mkoura/dump2polarion",
    description="Dump testcases results to xunit file; submit files to Polarion Importers",
    long_description=LONG_DESCRIPTION,
    author="Martin Kourim",
    author_email="mkourim@redhat.com",
    license="GPL",
    packages=find_packages(exclude=("tests",)),
    entry_points={
        "console_scripts": [
            "csv2sqlite.py = dump2polarion.csv2sqlite_cli:main",
            "polarion_dumper.py = dump2polarion.dumper_cli:main",
        ]
    },
    setup_requires=["setuptools_scm"],
    install_requires=["lxml", "pyyaml", "requests", "six"],
    keywords=["polarion", "testing"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Intended Audience :: Developers",
    ],
    include_package_data=True,
)
