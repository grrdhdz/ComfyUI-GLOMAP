# ComfyUI GLOMAP Camera Tracker

A powerful ComfyUI custom node pack for automated 3D camera tracking and photogrammetry using the GLOMAP/COLMAP pipeline. Specifically designed for VFX workflows, it allows you to process video sequences directly in ComfyUI, track the 3D camera, and export it for use in Blender, Nuke, Resolve, and more.

## Features
- **GPU Accelerated**: Utilizes CUDA-enabled SIFT extraction and matching for optimal performance on NVIDIA GPUs (like RTX 5060 Ti).
- **Auto-Downloader**: Automatically fetches the required COLMAP 4.0+ and Blender binaries. No complicated manual setup!
- **Video Optimized**: Uses sequential matching and loop detection to process video footage much faster than exhaustive photogrammetry.
- **Preview Output**: See the tracking points reprojection overlaid directly on your video within ComfyUI.
- **Multiple Export Formats**:
  - `FBX` (via Blender CLI background process)
  - `Alembic / .abc` (via Blender CLI)
  - `Nuke / .nk` (animated Camera3 node generated in Python)
  - `PLY Pointcloud`
  - `COLMAP native` format (text)

## Installation

1. Clone this repository into your `custom_nodes` folder:
```bash
cd custom_nodes
git clone https://github.com/gerhh/ComfyUI-GLOMAP.git
```
2. Install Python requirements:
```bash
cd ComfyUI-GLOMAP
pip install -r requirements.txt
```
*(Since you use ComfyDesktop with a `uv` virtual environment, the dependencies are installed automatically into your active venv).*

## The Nodes

### 1. (down)Load GLOMAP Setup
Downloads the COLMAP binaries (v4.0.2) and configures the environment.
- **colmap_version**: Choose between Windows CUDA (NVIDIA), Windows CPU, or Linux/Mac (System Install).
- **use_blender_portable**: Toggle to use the built-in portable Blender 4.4 (auto-downloaded) or a custom path.
- **blender_path**: Path to your `blender.exe` if not using the portable version.

### 2. GLOMAP Camera Tracker
The core engine that converts 2D images into 3D camera data.
- **mapper_type**: 
  - `glomap (global)`: (Recommended) Modern, fast, and stable for long video sequences.
  - `colmap (incremental)`: Classic method, accurate but slower and more prone to failure on complex motion.
- **matching_type**:
  - `sequential`: (Ideal for Video) Compares adjacent frames. Fast and logical for video tracks.
  - `exhaustive`: Compares every frame with every other frame. Very slow, use only for unordered photos.
  - `vocab_tree`: Uses a visual database for large image sets.
- **camera_model**:
  - `SIMPLE_RADIAL`: Standard for most DSLR/Mirrorless lenses with basic distortion.
  - `PINHOLE`: No distortion (ideal for CG renders or pre-distorted footage).
  - `OPENCV`: More complex calculation for specific specialty lenses.
- **max_image_size**: Resolution limit for internal processing (e.g., 4096 for 4K). Lower this to 2048 if you run out of VRAM.
- **max_num_features**: Max "interest points" per image. Higher (e.g., 16384) is more precise but heavier.
- **single_camera**: Set to `true` if the whole sequence was shot with the same lens/camera for much better stability.
- **use_gpu**: Uses your NVIDIA GPU for SIFT extraction (highly recommended).
- **fps_override**: 0.0 uses the original video FPS. Set to a specific number (e.g., 24.0) to force a specific project frame rate.

### 3. GLOMAP Tracking Preview
Overlays the 3D tracked points onto your original 2D frames. 
- Color coding: Green points have low reprojection error (good), Red points have high error (bad).
- Connect to VHS `Video Combine` to render a diagnostic preview.

### 4. GLOMAP Export Camera
Export the reconstructed camera animation and point cloud.
- **format**: `fbx`, `alembic_abc`, `nuke_nk`, `ply_pointcloud`, or `colmap_native`.
- **filename_prefix**: The name of the output file. The extension updates automatically in the UI.
- **scene_scale**: Global scale factor for the 3D scene.
- **up_axis**: Choose between `Y_UP` (Maya/Nuke) or `Z_UP` (Blender/3ds Max).

## Recommended Workflow for 4K VFX
1. **Subsamping**: Tracking 30-60 fps is often overkill and hides parallax. Use `fps_override = 5.0` or `10.0` for a much faster and more robust solve.
2. **Setup**: Run the `(down)Load GLOMAP Setup` node first to ensure dependencies are ready.
3. **Tracking**: Use `glomap (global)` and `sequential` matching for almost all video tasks.
4. **Export**: Leave `output_directory` blank to save everything neatly inside `ComfyUI/output/GLOMAP/track_[ID]/`.
