import os
import requests
import zipfile
import shutil
from pathlib import Path
from tqdm import tqdm
import platform

BIN_DIR = Path(__file__).parent.parent / "bin"
COLMAP_VERSION = "4.0.2"
BLENDER_VERSION = "4.4.0"

BLENDER_URL = f"https://download.blender.org/release/Blender4.4/blender-{BLENDER_VERSION}-windows-x64.zip"


def download_file(url, dest_path):
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # We shouldn't redownload if it's already there
    if dest_path.exists():
        print(f"File {dest_path.name} already exists. Skipping download.")
        return dest_path

    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get("content-length", 0))

    with (
        open(dest_path, "wb") as file,
        tqdm(
            desc=dest_path.name,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar,
    ):
        for data in response.iter_content(chunk_size=8192):
            size = file.write(data)
            bar.update(size)

    return dest_path


def extract_zip(zip_path, extract_dir):
    zip_path = Path(zip_path)
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {zip_path.name} to {extract_dir}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)


def _find_exe_in_dir(search_dir, *exe_names):
    for name in exe_names:
        found = list(search_dir.rglob(name))
        if found:
            return str(found[0])
    return None


def resolve_colmap(version_selection, user_path="auto", auto_download=True):
    """
    Resolve the COLMAP executable path.
    COLMAP 4.0.2 integrates GLOMAP (global_mapper), so no separate glomap.exe needed.

    Returns: path to colmap executable (COLMAP.bat or colmap.exe)
    """
    return _resolve_colmap_exe(version_selection, user_path, auto_download)


# Keep backwards compatibility
def resolve_colmap_and_glomap(version_selection, user_path="auto", auto_download=True):
    """Legacy function — returns (colmap_exe, None) since GLOMAP is integrated."""
    colmap_exe = _resolve_colmap_exe(version_selection, user_path, auto_download)
    return colmap_exe, None


def _resolve_colmap_exe(version_selection, user_path="auto", auto_download=True):
    colmap_dir = BIN_DIR / "colmap"
    exe_name = "COLMAP.bat" if platform.system() == "Windows" else "colmap"

    if "Linux" in version_selection or "Mac" in version_selection:
        colmap_sys = shutil.which("colmap")
        if colmap_sys:
            return colmap_sys
        raise FileNotFoundError(
            "COLMAP not found in system PATH. For Linux/Mac, please install COLMAP manually (e.g. brew install colmap / apt install colmap) and add it to your PATH."
        )

    if user_path and user_path.lower() != "auto":
        path = Path(user_path)
        if path.is_file():
            return str(path)
        if path.is_dir():
            exe_path = path / exe_name
            if exe_path.exists():
                return str(exe_path)
            exe_path2 = path / "colmap.exe"
            if exe_path2.exists():
                return str(exe_path2)
        raise ValueError(
            f"COLMAP executable not found at user provided path: {user_path}"
        )

    # Custom cuDSS build (compiled locally with full GPU support)
    if "cuDSS" in version_selection:
        target_dir = BIN_DIR / "colmap_cudss"
        if target_dir.exists():
            found = _find_exe_in_dir(target_dir, exe_name, "colmap.exe")
            if found:
                return found
        raise FileNotFoundError(
            "cuDSS build selected but 'bin/colmap_cudss' not found. "
            "Please compile it first using build_tools/compile_colmap_vfx.bat"
        )

    # Pre-downloaded official COLMAP
    if colmap_dir.exists():
        found = _find_exe_in_dir(colmap_dir, exe_name, "colmap.exe")
        if found:
            return found

    if auto_download:
        base_url = (
            f"https://github.com/colmap/colmap/releases/download/{COLMAP_VERSION}"
        )
        if "Windows CUDA" in version_selection:
            colmap_url = f"{base_url}/colmap-x64-windows-cuda.zip"
        elif "Windows CPU" in version_selection:
            colmap_url = f"{base_url}/colmap-x64-windows-no-cuda.zip"
        else:
            raise ValueError(
                f"No auto-download available for selection: {version_selection}"
            )

        zip_path = BIN_DIR / "colmap.zip"
        download_file(colmap_url, zip_path)
        extract_zip(zip_path, colmap_dir)

        if zip_path.exists():
            zip_path.unlink()
            print(f"Deleted archive: {zip_path.name}")

        found = _find_exe_in_dir(colmap_dir, exe_name, "colmap.exe")
        if found:
            return found
        raise RuntimeError("Downloaded COLMAP but executable not found in zip.")

    raise FileNotFoundError("COLMAP not found and auto-download is disabled.")


def resolve_colmap_path(version_selection, user_path="auto", auto_download=True):
    return _resolve_colmap_exe(version_selection, user_path, auto_download)


def resolve_blender_path(user_path="auto", auto_download=False):
    blender_dir = BIN_DIR / "blender"
    exe_name = "blender.exe" if platform.system() == "Windows" else "blender"

    if user_path and user_path.lower() != "auto":
        path = Path(user_path)
        if path.is_file():
            return str(path)
        if path.is_dir():
            exe_path = path / exe_name
            if exe_path.exists():
                return str(exe_path)
        raise ValueError(
            f"Blender executable not found at user provided path: {user_path}"
        )

    # Auto resolution
    if blender_dir.exists():
        found = list(blender_dir.rglob(exe_name))
        if found:
            return str(found[0])

    if auto_download:
        zip_path = BIN_DIR / "blender.zip"
        download_file(BLENDER_URL, zip_path)
        extract_zip(zip_path, blender_dir)

        if zip_path.exists():
            zip_path.unlink()
            print(f"Deleted archive: {zip_path.name}")

        found = list(blender_dir.rglob(exe_name))
        if found:
            # Make it portable by creating empty config directory alongside blender.exe
            config_dir = found[0].parent / "config"
            config_dir.mkdir(exist_ok=True)
            return str(found[0])
        raise RuntimeError("Downloaded Blender but executable not found in zip.")

    raise FileNotFoundError("Blender not found and auto-download is disabled.")
