@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /EHsc /O2 /MT /LD /W3 ^
   /D "IMGUI_DISABLE_OBSOLETE_FUNCTIONS" ^
   /I "deps\EDF6Plugins" /I "deps\imgui" ^
   src\loadouts.cpp src\ui_kit.cpp ^
   deps\imgui\imgui.cpp deps\imgui\imgui_draw.cpp deps\imgui\imgui_tables.cpp deps\imgui\imgui_widgets.cpp ^
   /Fo:build\ /Fe:build\EDF6Loadouts.dll ^
   /link user32.lib /IMPLIB:build\EDF6Loadouts.lib
