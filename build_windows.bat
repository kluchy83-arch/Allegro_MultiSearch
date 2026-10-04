@echo off
echo ===================================================
echo Budowanie AllegroMultiItemFinderGUI.exe dla Windows x64
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

echo Budowanie pliku wykonywalnego GUI (EXE bez okna konsoli)...
pyinstaller --noconsole --onefile --name="AllegroMultiItemFinderGUI" gui.py

if exist "dist\AllegroMultiItemFinderGUI.exe" (
    echo.
    echo ===================================================
    echo Sukces! Plik AllegroMultiItemFinderGUI.exe zostal utworzony w folderze dist\
    echo ===================================================
) else (
    echo.
    echo Wystapil blad podczas tworzenia pliku EXE.
)

pause
