.PHONY: bootstrap compile test safety check dry-run

PYTHON ?= python3

bootstrap:
	./scripts/bootstrap.sh

compile:
	$(PYTHON) -m compileall -q src tests

test:
	$(PYTHON) -m pytest

safety:
	./scripts/validate-repository-safety.sh

check: compile test safety

dry-run:
	PYTHONPATH=src $(PYTHON) -m aotp.cli dry-run --scope config/scope.example.yaml
