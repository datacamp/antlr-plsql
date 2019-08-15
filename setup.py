#!/usr/bin/env python

import re
import ast
from os import path
from setuptools import setup

PACKAGE_NAME = "antlr_plsql"
REQUIREMENT_NAMES = ["antlr-ast", "antlr4-python3-runtime", "pyyaml"]

HERE = path.abspath(path.dirname(__file__))
VERSION_FILE = path.join(HERE, PACKAGE_NAME, "__init__.py")
REQUIREMENTS_FILE = path.join(HERE, "requirements.txt")
README_FILE = path.join(HERE, "README.md")

with open(VERSION_FILE, encoding="utf-8") as fp:
    _version_re = re.compile(r"__version__\s+=\s+(.*)")
    VERSION = str(ast.literal_eval(_version_re.search(fp.read()).group(1)))
with open(REQUIREMENTS_FILE, encoding="utf-8") as fp:
    req_txt = fp.read()
    _requirements_re_template = r"^({}(?:\s*[~<>=]+\s*\S*)?)\s*(?:#.*)?$"
    REQUIREMENTS = [
        re.search(_requirements_re_template.format(requirement), req_txt, re.M).group(0)
        for requirement in REQUIREMENT_NAMES
    ]
with open(README_FILE, encoding="utf-8") as fp:
    README = fp.read()

setup(
    name=PACKAGE_NAME.replace("_", "-"),
    version=VERSION,
    packages=[PACKAGE_NAME],
    install_requires=REQUIREMENTS,
    description="A procedural sql parser, written in Antlr4",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Michael Chow",
    author_email="michael@datacamp.com",
    maintainer="Jeroen Hermans",
    maintainer_email="content-engineering@datacamp.com",
    url="https://github.com/datacamp/antlr-plsql",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
)
