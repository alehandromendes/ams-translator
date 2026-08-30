@echo off
REM Preenche as linhas de dialogo que o mod de traducao de Lord of Mysteries
REM deixou em chines. FECHE O JOGO ANTES DE RODAR.
cd /d "%~dp0"
set PY=.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo.
echo === PREVIA (nao grava nada) ===
"%PY%" -m overlay.gamefill --dry-run
echo.
echo Relatorio completo em:  gamefill\report.csv
echo.
choice /m "Aplicar no jogo agora"
if errorlevel 2 goto :fim

"%PY%" -m overlay.gamefill
echo.
echo Pronto. Para desfazer:  "%PY%" -m overlay.gamefill --restore
:fim
pause
