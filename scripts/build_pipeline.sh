#!/bin/bash
set -e

echo "========================================================"
echo "VaultMind 2.0 - Unified Data Pipeline"
echo "========================================================"
echo ""

echo "[1/2] Running Data Generator v2.0..."
python data_generator_v2.py

echo ""
echo "[2/2] Running Data Mutator..."
PYTHONIOENCODING=utf-8 python data_mutator.py

echo ""
echo "Pipeline complete. Production files are in ../server/data/vaultmind_production/"
