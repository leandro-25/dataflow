@echo off
echo Restaurando dados de demonstracao do Dataflow...
cd /d "%~dp0"
python scripts\restaurar_dados_demo.py
pause
