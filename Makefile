.PHONY: clean

build:
	antlr4 -Dlanguage=Python3 -visitor sqlwhat/grammar/plsql/plsql.g4

clean:
	find . \( -name \*.pyc -o -name \*.pyo -o -name __pycache__ \) -prune -exec rm -rf {} +

test:
	pytest -m "not backend"

deploy:
	travis/deploy-builds.sh
