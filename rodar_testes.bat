@echo off
cd /d "%~dp0"

echo ============================================
echo  1/11 - Teste de aceitacao dos conectores
echo ============================================
python backend\teste_todas_fontes.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  2/11 - Suite completa da sessao Ingestions
echo ============================================
python scripts\teste_ingestions_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  3/11 - Suite completa da sessao Staging
echo ============================================
python scripts\teste_staging_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  4/11 - Suite completa da sessao Dimensions
echo ============================================
python scripts\teste_dimensions_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  5/11 - Suite completa da sessao Facts
echo ============================================
python scripts\teste_facts_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  6/11 - Suite completa da sessao Metrics
echo ============================================
python scripts\teste_metrics_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  7/11 - Suite completa da sessao Dashboards
echo ============================================
python scripts\teste_dashboards_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  8/11 - Suite completa da sessao Pipeline
echo ============================================
python scripts\teste_pipeline_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  9/11 - Suite completa da sessao Catalog
echo ============================================
python scripts\teste_catalog_completo.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  10/11 - Sources: validacao, segredos e protecoes
echo ============================================
python scripts\teste_sources_ux.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo ============================================
echo  11/11 - Ingestions: assistente e dry-run
echo ============================================
python scripts\teste_ingestions_wizard.py
if %ERRORLEVEL% NEQ 0 goto falha

echo.
echo TODAS AS SUITES PASSARAM!
pause
exit /b 0

:falha
echo.
echo HOUVE FALHAS - verifique o resultado acima.
pause
exit /b 1






