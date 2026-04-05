import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.gpu_utils import get_gpu_info
from core.downloader_utils import resolve_colmap_path, resolve_blender_path

if __name__ == "__main__":
    print("GPU INFO:")
    print(get_gpu_info())
    print("\nResolving COLMAP...")
    print(resolve_colmap_path(auto_download=True))
    print("\nResolving Blender (No download)...")
    try:
        print(resolve_blender_path(auto_download=False))
    except Exception as e:
        print(f"Expected failure for blender without download: {e}")
