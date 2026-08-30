@echo off
REM Gera o executavel do Tradutor de Legendas em dist\Tradutor de Legendas\
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Rode primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

taskkill /IM "Tradutor de Legendas.exe" /F >nul 2>&1
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq Tradutor de Legendas.exe" 2>nul | find /I "Tradutor de Legendas.exe" >nul
if not errorlevel 1 (
    echo.
    echo  *** FECHE a janela do "Tradutor de Legendas" antes de compilar ***
    echo  Ela esta aberta e trava os arquivos da pasta dist\.
    echo  Se nao fechar pelo X, use o Gerenciador de Tarefas.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -q pyinstaller
REM sem --clean: evita PermissionError em build\overlay\localpycs
".venv\Scripts\python.exe" -m PyInstaller --noconfirm overlay.spec
if errorlevel 1 (
    echo.
    echo  ================================================================
    echo   BUILD FALHOU.
    echo   Se foi "Acesso negado" em dist\...\data ou _internal: o .exe
    echo   ainda estava aberto. Feche-o e rode de novo.
    echo  ================================================================
    pause
    exit /b 1
)

echo.
echo ================================================================
echo  Pronto: dist\Tradutor de Legendas\Tradutor de Legendas.exe
echo  Distribua a PASTA inteira "dist\Tradutor de Legendas".
echo ================================================================
pause
