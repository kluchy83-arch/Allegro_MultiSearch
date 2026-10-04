@echo off
echo ===================================================
echo Budowanie AllegroMultiItemFinder.exe dla Windows x64
echo ===================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python nie jest zainstalowany lub nie zostal dodany do PATH.
    pause
    exit /b 1
)

echo Instalacja wymaganych pakietow...
pip install -r requirements.txt
pip install pyinstaller

echo Budowanie pliku wykonywalnego EXE...
pyinstaller --onefile --name="AllegroMultiItemFinder" cli.py

if exist "dist\AllegroMultiItemFinder.exe" (
    echo.
    echo ===================================================
    echo Sukces! Plik AllegroMultiItemFinder.exe zostal utworzony w folderze dist\
    echo ===================================================
) else (
    echo.
    echo Wystapil blad podczas tworzenia pliku EXE.
)

pause
