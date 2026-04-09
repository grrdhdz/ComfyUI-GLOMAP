"""
Patches COLMAP CMakeLists.txt to fix MSVC flags for NVCC compatibility.

COLMAP uses raw MSVC flags like /MP, /wd4244, /EHsc in set(CMAKE_CXX_FLAGS ...) 
which get passed to NVCC and cause errors. This script wraps them with 
generator expressions so only the C/CXX compilers receive them.

This patch is idempotent — safe to run multiple times.
"""

import os
import sys
import glob


def find_colmap_cmakelists(build_dir):
    """Find the COLMAP CMakeLists.txt in the build directory."""
    # Direct COLMAP source (when compiling COLMAP directly)
    direct = os.path.join(build_dir, "CMakeLists.txt")
    if os.path.exists(direct):
        # Verify it's actually COLMAP
        with open(direct, 'r', encoding='utf-8') as f:
            content = f.read(500)
            if 'COLMAP' in content:
                return direct
    
    # FetchContent location
    fetch_paths = glob.glob(os.path.join(build_dir, "_deps", "colmap-src", "CMakeLists.txt"))
    if fetch_paths:
        return fetch_paths[0]
    
    return None


def patch_colmap_cmake(cmake_path):
    """Patch COLMAP CMakeLists.txt for MSVC+NVCC compatibility."""
    with open(cmake_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already patched
    if '# PATCHED FOR NVCC' in content:
        print(f"[PATCH] Already patched: {cmake_path}")
        return True
    
    original = content
    
    # Pattern 1: set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /EHsc")
    content = content.replace(
        'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /EHsc")',
        '# PATCHED FOR NVCC: Use add_compile_options with generator expressions\n'
        '    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/EHsc>)'
    )
    
    # Pattern 2: set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /wd4244 /wd4267 /wd4305")
    content = content.replace(
        'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /wd4244 /wd4267 /wd4305")',
        'add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/wd4244> $<$<COMPILE_LANGUAGE:CXX>:/wd4267> $<$<COMPILE_LANGUAGE:CXX>:/wd4305>)'
    )
    
    # Pattern 3: set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /MP") and CXX
    content = content.replace(
        'set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /MP")',
        'add_compile_options($<$<COMPILE_LANGUAGE:C>:/MP>)'
    )
    content = content.replace(
        'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /MP")',
        'add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/MP>)'
    )
    
    # Pattern 4: /bigobj flags
    content = content.replace(
        'set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /bigobj")',
        'add_compile_options($<$<COMPILE_LANGUAGE:C>:/bigobj>)'
    )
    content = content.replace(
        'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /bigobj")',
        'add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/bigobj>)'
    )
    
    if content != original:
        with open(cmake_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[PATCH] Successfully patched: {cmake_path}")
        return True
    else:
        print(f"[PATCH] No changes needed: {cmake_path}")
        return True


if __name__ == "__main__":
    # Accept build dir or source dir as argument
    if len(sys.argv) > 1:
        search_dir = sys.argv[1]
    else:
        # Default: look in build directory relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_dir = os.path.join(script_dir, "colmap_source")
    
    cmake_path = find_colmap_cmakelists(search_dir)
    if cmake_path:
        patch_colmap_cmake(cmake_path)
    else:
        print(f"[PATCH] COLMAP CMakeLists.txt not found in {search_dir}")
        print("[PATCH] This is expected on first CMake configure before source is fetched.")
        sys.exit(0)  # Don't fail — this runs before FetchContent downloads
