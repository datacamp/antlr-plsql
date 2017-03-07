#!/usr/bin/env python

import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('antlr_plsql/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
	name = 'antlr-plsql',
	version = version,
	packages = ['antlr_plsql'],
	install_requires = ['antlr4-python3-runtime'],
        description = 'A procedural sql parser, written in Antlr4',
        author = 'Michael Chow',
        author_email = 'michael@datacamp.com',
        url = 'https://github.com/datacamp/antlr-plsql')
