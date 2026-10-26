.PHONY: data run test
data:
	python scripts/bootstrap.py
run:
	python run.py --data data --out reports
test:
	python -m pytest -q
