@echo off
REM Abre o tradutor de legendas ao vivo. Duplo-clique para rodar.
REM Se o atalho global nao pegar sobre o jogo: clique com o botao direito > Executar como administrador.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m overlay
) else (
    echo Ambiente virtual nao encontrado. Rode primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate ^&^& pip install -r requirements-overlay.txt
    pause
)
