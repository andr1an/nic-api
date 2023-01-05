import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

long_description = open(os.path.join(here, "README.rst"), "r").read()

setup(
    name="nic_api",
    version="0.4.2",
    description="NIC.RU API wrapper library",
    long_description=long_description,
    url="https://github.com/andr1an/nic-api",
    author="Sergey Andrianov",
    author_email="info@andrian.ninja",
    license="GPLv3",
    packages=["nic_api"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Internet :: Name Service (DNS)",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=2.7, <4.0",
    install_requires=[
        "requests>=2.4",
        "requests-oauthlib>=1.1",
    ],
    project_urls={
        "Bug Reports": "https://github.com/andr1an/nic-api/issues",
        "Source": "https://github.com/andr1an/nic-api",
    },
)
