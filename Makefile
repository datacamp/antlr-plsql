.PHONY: clean

clean:
	find . \( -name \*.pyc -o -name \*.pyo -o -name __pycache__ \) -prune -exec rm -rf {} +

test:
	pytest -m "not backend"
