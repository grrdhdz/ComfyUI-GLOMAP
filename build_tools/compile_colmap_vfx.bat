@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  COLMAP 4.0.2 VFX BUILD (with cuDSS GPU Acceleration)
echo  Target: RTX 5060 Ti (sm_120) ^| CUDA 13 ^| GUI: OFF
echo ========================================================
echo.

set BASE_DIR=%~dp0
set VCPKG_DIR=%BASE_DIR%vcpkg
set COLMAP_SRC=%BASE_DIR%colmap_source
set BUILD_DIR=%BASE_DIR%build_colmap
set OUTPUT_DIR=%BASE_DIR%..\bin\colmap_cudss
set OVERLAYS=%BASE_DIR%overlay_ports
set CUDSS_DIR=%BASE_DIR%cuDSS

:: -------------------------------------------------------
:: STEP 0: Detect Visual Studio 2022 and CUDA 13
:: -------------------------------------------------------
echo [Step 0/6] Detecting build environment...
echo.

set VS_PATH=
for %%E in (Community Professional Enterprise) do (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvarsall.bat" (
        set "VS_PATH=C:\Program Files\Microsoft Visual Studio\2022\%%E"
        echo [OK] Visual Studio 2022 %%E found
        goto :vs_found
    )
)

echo [ERROR] Visual Studio 2022 not found. Please install it.
pause
exit /b 1

:vs_found
:: Load VS environment
call "%VS_PATH%\VC\Auxiliary\Build\vcvarsall.bat" x64
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to load VS environment
    pause
    exit /b 1
)
echo [OK] VS 2022 environment loaded

:: Detect CUDA
if exist "%CUDA_PATH%\bin\nvcc.exe" (
    echo [OK] CUDA detected: %CUDA_PATH%
    "%CUDA_PATH%\bin\nvcc.exe" --version 2>nul | findstr "release"
) else (
    echo [ERROR] CUDA not found. Set CUDA_PATH or install CUDA Toolkit 13.
    pause
    exit /b 1
)
echo.

:: -------------------------------------------------------
:: STEP 1: Bootstrap vcpkg
:: -------------------------------------------------------
echo [Step 1/6] Setting up vcpkg...
echo.

if not exist "%VCPKG_DIR%\vcpkg.exe" (
    if not exist "%VCPKG_DIR%\.git" (
        echo [Step 1] Cloning vcpkg...
        git clone https://github.com/microsoft/vcpkg.git "%VCPKG_DIR%"
        if %ERRORLEVEL% neq 0 (
            echo [ERROR] Failed to clone vcpkg
            pause
            exit /b 1
        )
    )
    echo [Step 1] Bootstrapping vcpkg...
    call "%VCPKG_DIR%\bootstrap-vcpkg.bat" -disableMetrics
    if not exist "%VCPKG_DIR%\vcpkg.exe" (
        echo [ERROR] vcpkg bootstrap failed
        pause
        exit /b 1
    )
)
echo [OK] vcpkg ready
echo.

:: -------------------------------------------------------
:: STEP 2: Download cuDSS SDK if needed
:: -------------------------------------------------------
echo [Step 2/6] Checking cuDSS SDK...
echo.

if not exist "%CUDSS_DIR%\lib\13\cmake\cudss\cudss-config.cmake" (
    echo [Step 2] cuDSS not found. Please download it manually:
    echo.
    echo   1. Go to https://developer.nvidia.com/cudss-downloads
    echo   2. Download cuDSS for Windows x64, CUDA 13
    echo   3. Extract to: %CUDSS_DIR%
    echo   4. Verify: %CUDSS_DIR%\lib\13\cmake\cudss\cudss-config.cmake exists
    echo.
    echo After extracting, run this script again.
    pause
    exit /b 1
)
echo [OK] cuDSS SDK found
echo.

:: -------------------------------------------------------
:: STEP 3: Install vcpkg dependencies (Ceres with CUDA + cuDSS)
:: -------------------------------------------------------
echo [Step 3/6] Installing dependencies (Ceres CUDA, Boost, Eigen, etc.)...
echo This may take 15-30 minutes on first run.
echo.

"%VCPKG_DIR%\vcpkg.exe" install ^
    ceres[core,cuda,lapack,schur,suitesparse]:x64-windows ^
    boost-algorithm:x64-windows ^
    boost-filesystem:x64-windows ^
    boost-graph:x64-windows ^
    boost-heap:x64-windows ^
    boost-program-options:x64-windows ^
    boost-property-map:x64-windows ^
    boost-property-tree:x64-windows ^
    eigen3:x64-windows ^
    gflags:x64-windows ^
    glog:x64-windows ^
    flann:x64-windows ^
    freeimage:x64-windows ^
    metis:x64-windows ^
    sqlite3:x64-windows ^
    poselib:x64-windows ^
    suitesparse:x64-windows ^
    glew:x64-windows ^
    --overlay-ports="%OVERLAYS%" --recurse

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Dependency installation failed
    pause
    exit /b 1
)
echo.
echo [OK] All dependencies installed
echo.

:: -------------------------------------------------------
:: STEP 4: Clone COLMAP 4.0.2 source
:: -------------------------------------------------------
echo [Step 4/6] Getting COLMAP 4.0.2 source code...
echo.

if not exist "%COLMAP_SRC%\CMakeLists.txt" (
    echo [Step 4] Cloning COLMAP 4.0.2...
    git clone --branch 4.0.2 --depth 1 https://github.com/colmap/colmap.git "%COLMAP_SRC%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to clone COLMAP
        pause
        exit /b 1
    )
)
echo [OK] COLMAP 4.0.2 source ready
echo.

:: Apply MSVC/NVCC compatibility patch
echo [Step 4b] Patching COLMAP for MSVC + NVCC compatibility...
python "%BASE_DIR%patch_colmap_msvc.py" "%COLMAP_SRC%"
echo.

:: -------------------------------------------------------
:: STEP 5: Configure and Build with CMake + Ninja
:: -------------------------------------------------------
echo [Step 5/6] Configuring CMake (Ninja + CUDA 13 + cuDSS)...
echo.

:: Find Ninja from vcpkg downloads or PATH
set NINJA_EXE=
for /f "delims=" %%i in ('where ninja 2^>nul') do set "NINJA_EXE=%%i"
if not defined NINJA_EXE (
    for /r "%VCPKG_DIR%\downloads\tools" %%f in (ninja.exe) do (
        set "NINJA_EXE=%%f"
    )
)
if not defined NINJA_EXE (
    echo [WARN] Ninja not found. Installing via vcpkg...
    "%VCPKG_DIR%\vcpkg.exe" install vcpkg-tool-ninja:x64-windows
    for /r "%VCPKG_DIR%\downloads\tools" %%f in (ninja.exe) do (
        set "NINJA_EXE=%%f"
    )
)

:: Find CMake from vcpkg downloads or PATH
set CMAKE_EXE=
for /f "delims=" %%i in ('where cmake 2^>nul') do set "CMAKE_EXE=%%i"
if not defined CMAKE_EXE (
    for /r "%VCPKG_DIR%\downloads\tools" %%f in (cmake.exe) do (
        if /i "%%~nxf"=="cmake.exe" set "CMAKE_EXE=%%f"
    )
)
if not defined CMAKE_EXE (
    echo [ERROR] CMake not found
    pause
    exit /b 1
)

echo [OK] Using CMake: %CMAKE_EXE%
echo [OK] Using Ninja: %NINJA_EXE%

:: Clean previous build if it exists
if exist "%BUILD_DIR%" (
    echo [Step 5] Cleaning previous build...
    rmdir /s /q "%BUILD_DIR%"
)

:: Set NVCC flags for unsupported compiler
set CUDAFLAGS=-allow-unsupported-compiler
set NVCC_APPEND_FLAGS=-allow-unsupported-compiler
set NVCC_PREPEND_FLAGS=-allow-unsupported-compiler

:: Configure
"%CMAKE_EXE%" -G "Ninja" -S "%COLMAP_SRC%" -B "%BUILD_DIR%" ^
    -DCMAKE_MAKE_PROGRAM="%NINJA_EXE%" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_TOOLCHAIN_FILE="%VCPKG_DIR%\scripts\buildsystems\vcpkg.cmake" ^
    -DCUDAToolkit_ROOT="%CUDA_PATH%" ^
    -Dcudss_DIR="%CUDSS_DIR%\lib\13\cmake\cudss" ^
    -DCMAKE_CUDA_ARCHITECTURES="120" ^
    -DCMAKE_CUDA_FLAGS="--allow-unsupported-compiler" ^
    -DCMAKE_CXX_STANDARD=17 ^
    -DCMAKE_CUDA_STANDARD=17 ^
    -DCUDA_ENABLED=ON ^
    -DGUI_ENABLED=OFF ^
    -DCGAL_ENABLED=OFF ^
    -DLSD_ENABLED=OFF ^
    -DONNX_ENABLED=OFF ^
    -DOPENGL_ENABLED=OFF ^
    -DDOWNLOAD_ENABLED=OFF ^
    -DTESTS_ENABLED=OFF ^
    -DFETCH_POSELIB=ON ^
    -DFETCH_FAISS=ON ^
    -DMSVC_USE_STATIC_CRT=OFF

if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake configuration failed
    pause
    exit /b 1
)

echo.
echo [Step 5b] Building COLMAP (this may take 30-60 minutes)...
echo.

"%CMAKE_EXE%" --build "%BUILD_DIR%" --config Release --parallel %NUMBER_OF_PROCESSORS%

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo [OK] Build successful!
echo.

:: -------------------------------------------------------
:: STEP 6: Package binaries
:: -------------------------------------------------------
echo [Step 6/6] Packaging binaries...
echo.

if not exist "%OUTPUT_DIR%\bin" mkdir "%OUTPUT_DIR%\bin"

:: Copy COLMAP executable
for /r "%BUILD_DIR%" %%f in (colmap.exe) do (
    if exist "%%f" (
        echo Copying %%f...
        xcopy /Y "%%f" "%OUTPUT_DIR%\bin\"
    )
)

:: Copy vcpkg DLLs (CRITICAL: Copy from the build manifest directory)
set VCPKG_BIN=%BUILD_DIR%\vcpkg_installed\x64-windows\bin
if exist "%VCPKG_BIN%" (
    echo Copying vcpkg runtime DLLs from build manifest...
    xcopy /Y "%VCPKG_BIN%\*.dll" "%OUTPUT_DIR%\bin\"
) else (
    :: Fallback to the prep-vcpkg if manifest mode wasn't used correctly
    set VCPKG_BIN=%VCPKG_DIR%\installed\x64-windows\bin
    if exist "!VCPKG_BIN!" (
        echo Copying vcpkg runtime DLLs from base...
        xcopy /Y "!VCPKG_BIN!\*.dll" "%OUTPUT_DIR%\bin\"
    )
)

:: Copy cuDSS DLLs (CRITICAL for GPU solver)
echo Copying cuDSS DLLs (required for GPU Bundle Adjustment)...
if exist "%CUDSS_DIR%\bin\13\cudss64_0.dll" (
    xcopy /Y "%CUDSS_DIR%\bin\13\cudss64_0.dll" "%OUTPUT_DIR%\bin\"
    echo [OK] cudss64_0.dll copied
) else (
    echo [WARN] cudss64_0.dll not found!
)
if exist "%CUDSS_DIR%\bin\13\cudss_mtlayer_vcomp140_13_0.dll" (
    xcopy /Y "%CUDSS_DIR%\bin\13\cudss_mtlayer_vcomp140_13_0.dll" "%OUTPUT_DIR%\bin\"
)

:: Create COLMAP.bat wrapper
echo @echo off > "%OUTPUT_DIR%\COLMAP.bat"
echo "%%~dp0bin\colmap.exe" %%* >> "%OUTPUT_DIR%\COLMAP.bat"

:: -------------------------------------------------------
:: VERIFICATION
:: -------------------------------------------------------
echo.
echo ========================================================
echo  VERIFICATION
echo ========================================================
echo.

if exist "%OUTPUT_DIR%\bin\colmap.exe" (
    echo [OK] colmap.exe found
    "%OUTPUT_DIR%\bin\colmap.exe" help 2>&1 | findstr /C:"with CUDA" >nul
    if !ERRORLEVEL! equ 0 (
        echo [OK] CUDA support confirmed
    ) else (
        echo [WARN] CUDA support NOT detected in binary
    )
    "%OUTPUT_DIR%\bin\colmap.exe" help 2>&1 | findstr /C:"global_mapper" >nul
    if !ERRORLEVEL! equ 0 (
        echo [OK] global_mapper (GLOMAP) command available
    ) else (
        echo [WARN] global_mapper NOT found
    )
    "%OUTPUT_DIR%\bin\colmap.exe" help 2>&1 | findstr /C:"view_graph_calibrator" >nul
    if !ERRORLEVEL! equ 0 (
        echo [OK] view_graph_calibrator command available
    ) else (
        echo [WARN] view_graph_calibrator NOT found
    )
) else (
    echo [ERROR] colmap.exe NOT found in output directory!
)

if exist "%OUTPUT_DIR%\bin\cudss64_0.dll" (
    echo [OK] cuDSS GPU solver DLL present
) else (
    echo [WARN] cuDSS DLL missing - GPU solver will NOT work!
)

if exist "%OUTPUT_DIR%\bin\ceres.dll" (
    echo [OK] Ceres solver DLL present
) else (
    echo [WARN] Ceres DLL missing
)

echo.
echo ========================================================
echo  BUILD COMPLETE
echo  Output: %OUTPUT_DIR%
echo.
echo  GPU Pipeline:
echo    Feature Extraction: SiftGPU (CUDA)
echo    Feature Matching:   SiftGPU (CUDA)
echo    Bundle Adjustment:  Ceres + cuDSS (GPU)
echo    Global Positioning: Ceres + cuDSS (GPU)
echo ========================================================
echo.
pause
