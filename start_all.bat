@echo off
echo Iniciando Dataflow - Sistema Completo de Pipeline de Dados
echo.
echo Este script ira iniciar ambos os servidores (backend e frontend)
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Pressione qualquer tecla para iniciar...
pause > nul

echo.
echo [1/2] Iniciando Backend...
start "Dataflow Backend" cmd /k "cd /d d:\FATEC\projetos\date\dataflow\backend && pip install -r requirements.txt && python main.py"

echo Aguardando 5 segundos para o backend iniciar...
timeout /t 5 /nobreak > nul

echo.
echo [2/2] Iniciando Frontend...
start "Dataflow Frontend" cmd /k "cd /d d:\FATEC\projetos\date\dataflow\frontend && npm install && npm run dev"

echo.
echo Sistema iniciado! Aguarde a inicializacao completa.
echo.
echo Acesse:
echo - Frontend: http://localhost:5173
echo - Backend API: http://localhost:8000
echo - Documentacao API: http://localhost:8000/docs
echo.
pause
