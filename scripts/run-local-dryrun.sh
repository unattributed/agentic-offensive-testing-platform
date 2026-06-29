#!/usr/bin/env sh
set -eu

PYTHONPATH=src python3 -m aotp.cli validate-config --scope config/scope.example.yaml
PYTHONPATH=src python3 -m aotp.cli dry-run --scope config/scope.example.yaml
PYTHONPATH=src python3 -m aotp.cli campaign-plan \
  --scope config/scope.example.yaml \
  --campaign campaigns/authorized-webapp-campaign.example.yaml
