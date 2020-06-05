@echo off
title Plant Reliability - Iniciando...
echo ===================================================
echo Iniciando Plant Reliability (Modo Local para Pymes)
echo ===================================================
echo.
echo Verificando entorno e instalando dependencias (puede tardar la primera vez)...
uv sync
if %errorlevel% neq 0 (
    echo.
    echo Error: Asegurate de tener 'uv' o Python instalado.
    pause
    exit /b %errorlevel%
)
echo.
echo Entorno verificado. Levantando la interfaz web...
echo Si el navegador no se abre automaticamente, entra a: http://localhost:8501
echo.
uv run plant-reliability serve
pause
