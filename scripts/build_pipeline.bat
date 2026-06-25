@echo off
echo ========================================================
echo VaultMind 2.0 - Unified Data Pipeline
echo ========================================================
echo.
echo [1/2] Running Data Generator v2.0...
python data_generator_v2.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo [2/2] Running Data Mutator...
python -X utf8 data_mutator.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo Pipeline complete. Production files are in ../server/data/vaultmind_production/
