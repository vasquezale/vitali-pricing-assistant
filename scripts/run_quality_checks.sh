#!/bin/bash
set -e

echo "=== Ruff ==="
ruff check src/ tests/

echo "=== Pylint ==="
pylint src/vitali/ --fail-under=9.5

echo "=== Pytest ==="
pytest tests/ -v --tb=short

echo ""
echo "=== All quality checks passed ==="
