.PHONY: clean

all: clean test

build:
	antlr4 -Dlanguage=Python3 -visitor sqlwhat/grammar/plsql/plsql.g4

clean:
	find . \( -name \*.pyc -o -name \*.pyo -o -name __pycache__ \) -prune -exec rm -rf {} +
	rm -rf sqlwhat.egg-info

test: clean
	pytest -m "not backend"

deploy: build
	travis/setup-git.sh
	travis/deploy-builds.sh
