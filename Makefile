.PHONY: bootstrap compile test safety check dry-run

bootstrap:
	./scripts/bootstrap.sh

compile:
	python3 -m compileall -q src tests

test:
	python3 -m pytest

safety:
	./scripts/validate-repository-safety.sh

check: compile test safety

dry-run:
	PYTHONPATH=src python3 -m aotp.cli dry-run --scope config/scope.example.yaml
