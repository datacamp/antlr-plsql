#!/usr/bin/env python

from setuptools import setup

setup(
	name='sqlwhat',
	version='0.0.6',
	packages=['sqlwhat', 'sqlwhat.grammar.plsql'],
	install_requires=['pythonwhat', 'antlr4-python3-runtime'])
