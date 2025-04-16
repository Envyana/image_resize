@echo off
echo Building Image Resizer executable...
pyinstaller --name="ImageResizer" --windowed --onefile --icon=NONE --add-data="README.md;." main.py
echo Build complete. Check the "dist" folder for ImageResizer.exe
pause