@echo off
:: Modification from original script. Do not switch to script's directory.
setlocal enabledelayedexpansion
set "node_name=SageAttention-Multi"
Title '%node_name%' based on 'ComfyUI Easy Install' by ivo
:: PHAROS Edition ::
:: This script is based on https://github.com/Tavris1/ComfyUI-Easy-Install
:: Helper-CEI.zip/ComfyUI-Easy-Install/Add-Ons/SageAttention-Multi (v2.2.0 and v3).bat
:: Follow the repo's releases to keep this script up to date

set "DIR_LVL=.\"
for %%I in ("%DIR_LVL%") do set "ABS_DIR_LVL=%%~fI"
echo Execution Root: %ABS_DIR_LVL%

call :SET_COLORS
call :CHECK_FOLDER "%~dp0"
call :CHECK_EXISTS "main.py"
call :GET_VERSIONS "3.12" "2.7 2.8 2.9 2.10 2.11 2.12 2.13 2.14" "12.8 13.0"

set "PIP_NC=--no-cache-dir"&if exist "%DIR_LVL%Add-Ons\Tools\Helper-CEI\keep_cache.flag" set "PIP_NC="
set "PIPargs=%PIP_NC% --no-warn-script-location --timeout=1000 --retries 10 --use-pep517"

echo %green%:::::::::::::: Installing %yellow%SageAttention v2.2.0%green% and %yellow%SageAttention v3%reset%
echo.

:: Erasing ~* folders ::
if exist "%DIR_LVL%.venv\Lib\site-packages\~*" (powershell -NoProfile -ExecutionPolicy Bypass -command "Get-ChildItem '%DIR_LVL%.venv\Lib\site-packages\' -Directory | Where-Object {$_.Name -like '~*'} | Remove-Item -Recurse -Force")

:: Installing Triton ::
echo %green%:::::::::::::: Installing%yellow% Triton%reset%
echo.
%PYTHON_EXE% -I -m pip uninstall triton-windows -y >nul 2>&1
if "%TORCH_VERSION%"=="2.7" %PYTHON_EXE% -I -m pip install "triton-windows<3.4" %PIPargs%
if "%TORCH_VERSION%"=="2.8" %PYTHON_EXE% -I -m pip install "triton-windows<3.5" %PIPargs%
if "%TORCH_VERSION%"=="2.9" %PYTHON_EXE% -I -m pip install "triton-windows<3.6" %PIPargs%
if "%TORCH_VERSION%"=="2.10" %PYTHON_EXE% -I -m pip install "triton-windows<3.7" %PIPargs%
if "%TORCH_VERSION%"=="2.11" %PYTHON_EXE% -I -m pip install "triton-windows<3.7" %PIPargs%
if "%TORCH_VERSION%"=="2.12" %PYTHON_EXE% -I -m pip install "triton-windows<3.8" %PIPargs%
if "%TORCH_VERSION%"=="2.13" %PYTHON_EXE% -I -m pip install "triton-windows<3.8" %PIPargs%
if "%TORCH_VERSION%"=="2.14" %PYTHON_EXE% -I -m pip install "triton-windows<3.9" %PIPargs%
echo.

:: Installing SageAttention 2.2.0 ::
echo %green%:::::::::::::: Installing%yellow% SageAttention 2.2.0%reset%
echo.
if "%TORCH_VERSION%"=="2.7" if "%CUDA_VERSION%"=="12.8" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post3/sageattention-2.2.0+cu128torch2.7.1.post3-cp39-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.8" if "%CUDA_VERSION%"=="12.8" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post3/sageattention-2.2.0+cu128torch2.8.0.post3-cp39-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.9" if "%CUDA_VERSION%"=="13.0" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post5/sageattention-2.2.0+cu130torch2.9.1.post5-cp310-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.10" if "%CUDA_VERSION%"=="13.0" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.11" if "%CUDA_VERSION%"=="13.0" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.12" if "%CUDA_VERSION%"=="13.0" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.13" if "%CUDA_VERSION%"=="13.0" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl")
if "%TORCH_VERSION%"=="2.14" if "%CUDA_VERSION%"=="13.0" (set "SAGE2_WHL=https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl")

%PYTHON_EXE% -I -m pip uninstall sageattention -y >nul 2>&1
%PYTHON_EXE% -I -m pip install %SAGE2_WHL% %PIPargs%
echo.

:: Installing SageAttention 3 ::
if "%TORCH_VERSION%"=="2.7" if "%CUDA_VERSION%"=="12.8" (set "SAGE3_WHL=https://github.com/mengqin/SageAttention/releases/download/20251229/sageattn3-1.0.0+cu128torch271-cp312-cp312-win_amd64.whl")
if "%TORCH_VERSION%"=="2.8" if "%CUDA_VERSION%"=="12.8" (set "SAGE3_WHL=https://github.com/mengqin/SageAttention/releases/download/20251229/sageattn3-1.0.0+cu128torch280-cp312-cp312-win_amd64.whl")
if "%TORCH_VERSION%"=="2.9" if "%CUDA_VERSION%"=="13.0" (set "SAGE3_WHL=https://github.com/mengqin/SageAttention/releases/download/20251229/sageattn3-1.0.0+cu130torch291-cp312-cp312-win_amd64.whl")
if "%TORCH_VERSION%"=="2.10" if "%CUDA_VERSION%"=="13.0" (set "SAGE3_WHL=https://huggingface.co/ussoewwin/Sage-Attention-for-Windows/resolve/main/sageattn3-1.0.0+cu130torch2.10.0-cp312-cp312-win_amd64.whl")
if "%TORCH_VERSION%"=="2.11" if "%CUDA_VERSION%"=="13.0" (set "SAGE3_WHL=https://github.com/Comfy-Org/wheels/releases/download/sageattn3-latest/sageattn3-1.0.0+cu130torch2.11-cp312-cp312-win_amd64.whl")

%PYTHON_EXE% -I -m pip uninstall sageattn3 -y >nul 2>&1

if "%TORCH_VERSION%"=="2.12" goto :SkipSage3
if "%TORCH_VERSION%"=="2.13" goto :SkipSage3
if "%TORCH_VERSION%"=="2.14" goto :SkipSage3

echo %green%:::::::::::::: Installing%yellow% SageAttention 3%reset%
echo.
%PYTHON_EXE% -I -m pip install %SAGE3_WHL% %PIPargs%
echo.
goto :ResumeScript

:SkipSage3
echo %warning%Warning: PyTorch 2.12 and 2.13 do not support SageAttention 3.%reset%

:ResumeScript

:: Final Messages ::
echo.
echo %green%::::::::::::::%yellow% %node_name% %green%Installation Complete%reset%
echo.
if "%~1"=="" (
    echo %green%:::::::::::::: %yellow%Press any key to exit%reset%&Pause>nul
    exit
)

exit /b

:: ---------------------------------------- END ---------------------------------------- ::

:SET_COLORS
set warning=[33m
set    gray=[90m
set     red=[91m
set   green=[92m
set  yellow=[93m
set    blue=[94m
set magenta=[95m
set    cyan=[96m
set   white=[97m
set   reset=[0m
GOTO :EOF

:CHECK_EXISTS
set "CheckFile=%DIR_LVL%%~1"
if not exist %CheckFile% (
    echo.
    echo    %white%Required file %red%%CheckFile%%white% not found.%reset%
    echo.
    echo    %gray%Press any key to exit...%reset%&&pause>nul&&exit
)
GOTO :EOF

:CHECK_FOLDER
set "PYTHON_EXE="
set "PREF_FOLDER=%~1"

if exist "%DIR_LVL%.venv\Scripts\python.exe" (set "PYTHON_EXE=%DIR_LVL%.venv\Scripts\python.exe")

if "%PYTHON_EXE%"=="" (
	echo.
    echo    %green%Please run this file from the %yellow%%~1%green% folder.%reset%
    echo    %green%Currently running from: %red%%ABS_DIR_LVL%%reset%
	echo.
    echo    %gray%Press any key to exit...%reset%&Pause>nul
    exit
)
GOTO :EOF

:GET_VERSIONS
set "ALLOWED_PYTHON=%~1"
set "ALLOWED_TORCH=%~2"
set "ALLOWED_CUDA=%~3"

echo %green%:::::::::::::: Checking %yellow%Python, Torch, CUDA %green%versions%reset%
echo.
for /f "tokens=2" %%i in ('%PYTHON_EXE% --version 2^>^&1') do (
    for /f "tokens=1,2 delims=." %%a in ("%%i") do set "PYTHON_VERSION=%%a.%%b"
)
set "TORCH_VERSION=Not found"
set "CUDA_VERSION=Not available"
for /f "tokens=1,2 delims=|" %%a in ('%PYTHON_EXE% -c "import torch; v=torch.__version__.split(chr(43))[0]; cv=torch.version.cuda or chr(78); print(v.rsplit(chr(46),1)[0],cv,sep=chr(124))" 2^>nul') do (
    set "TORCH_VERSION=%%a"
    set "CUDA_VERSION=%%b"
)

echo %green%   Python    :%yellow% %PYTHON_VERSION%%reset%
echo %green%   PyTorch   :%yellow% %TORCH_VERSION%%reset%
echo %green%   CUDA Core :%yellow% %CUDA_VERSION%%reset%
echo.

set WARNINGS=0
call :CHECK_VERSION "%PYTHON_VERSION%" "%ALLOWED_PYTHON%" "Python"
call :CHECK_VERSION "%TORCH_VERSION%"  "%ALLOWED_TORCH%"  "Torch"
call :CHECK_VERSION "%CUDA_VERSION%"   "%ALLOWED_CUDA%"   "CUDA"

if !WARNINGS!==0 (
    echo %green%:::::::::::::: All versions are supported!%reset%
    echo.
) else (
    echo.
    echo %red%:::::::::::::: Press any key to exit%reset%&Pause>nul
    exit
)
GOTO :EOF

:CHECK_VERSION
set "CURRENT=%~1"
set "ALLOWED=%~2"
set "DISPLAY=%~3"
set "FOUND=0"

if "!CURRENT!"=="Not available" (
    echo %warning%WARNING: %red%%DISPLAY% is not available.%reset%
    set "WARNINGS=1"
    GOTO :EOF
)
if "!CURRENT!"=="Not found" (
    echo %warning%WARNING: %red%%DISPLAY% is not found.%reset%
    set "WARNINGS=1"
    GOTO :EOF
)

for %%v in (%ALLOWED%) do (
    if "!CURRENT!"=="%%v" set "FOUND=1"
)

if "!FOUND!"=="0" (
    echo %warning%WARNING: %red%%DISPLAY% !CURRENT! is not supported. %green%Supported: %ALLOWED%%reset%
    set "WARNINGS=1"
)
GOTO :EOF