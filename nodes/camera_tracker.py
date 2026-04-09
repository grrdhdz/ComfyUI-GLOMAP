import os
import time
from pathlib import Path
from comfy_api.latest import io
from ..core.colmap_runner import (
    feature_extract,
    run_matcher,
    run_view_graph_calibrator,
    run_mapper,
    convert_model_to_text,
)
from ..core.colmap_parser import read_model
import folder_paths

GLOMAP_CONFIG = io.Custom("GLOMAP_CONFIG")
GLOMAP_RECONSTRUCTION = io.Custom("GLOMAP_RECONSTRUCTION")
GLOMAP_TRACKING_DATA = io.Custom("GLOMAP_TRACKING_DATA")


class GLOMAPVfxTracker(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="GLOMAPVfxTracker",
            display_name="GLOMAP VFX Tracker (Zero RAM)",
            category="3D/GLOMAP",
            description="3D camera tracking loaded directly from disk (Video or Image Sequence) to save RAM",
            inputs=[
                GLOMAP_CONFIG.Input("config", tooltip="Config from GLOMAP Setup node"),
                io.Combo.Input(
                    "media_type", options=["video_path", "image_sequence_dir"]
                ),
                io.String.Input(
                    "media_path",
                    default="",
                    tooltip="Absolute path to the MP4 file or directory",
                ),
                io.Combo.Input(
                    "mapper_type", options=["glomap (global)", "colmap (incremental)"]
                ),
                io.Combo.Input(
                    "matching_type", options=["sequential", "exhaustive", "vocab_tree"]
                ),
                io.Combo.Input(
                    "camera_model",
                    options=["SIMPLE_RADIAL", "RADIAL", "OPENCV", "PINHOLE"],
                ),
                io.Int.Input("max_image_size", default=4096, min=512, max=8192),
                io.Int.Input("max_num_features", default=16384, min=1024, max=65536),
                io.Boolean.Input("single_camera", default=True),
                io.Boolean.Input("use_gpu", default=True),
                io.Float.Input("fps_override", default=0.0, min=0.0, max=120.0),
                io.Float.Input(
                    "source_fps",
                    default=0.0,
                    min=0.0,
                    max=240.0,
                    tooltip="0 = auto-detect from video metadata. Overrides output FPS for animation.",
                ),
            ],
            outputs=[
                GLOMAP_RECONSTRUCTION.Output(display_name="reconstruction"),
                GLOMAP_TRACKING_DATA.Output(display_name="tracking_data"),
                io.Image.Output(display_name="images"),
                io.String.Output(display_name="log"),
            ],
        )

    @classmethod
    def execute(
        cls,
        config,
        media_type,
        media_path,
        mapper_type,
        matching_type,
        camera_model,
        max_image_size,
        max_num_features,
        single_camera,
        use_gpu,
        fps_override,
        source_fps,
    ) -> io.NodeOutput:

        colmap_exe = config.get("colmap_exe")
        if not colmap_exe or not os.path.exists(colmap_exe):
            raise RuntimeError(
                "COLMAP executable not found in config. Please check GLOMAP Setup node."
            )

        output_dir = Path(folder_paths.get_output_directory())
        workspace_dir = output_dir / "GLOMAP" / f"track_{int(time.time())}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        db_path = workspace_dir / "database.db"
        sparse_dir = workspace_dir / "sparse"

        log_msgs = []
        log_msgs.append(f"VFX Workspace created: {workspace_dir}")
        print(f"[GLOMAP] VFX Workspace created: {workspace_dir}")

        try:
            active_fps = source_fps
            if media_type == "video_path":
                from ..core.frame_utils import extract_frames_from_video

                images_dir, saved_paths = extract_frames_from_video(
                    media_path,
                    workspace_dir,
                    fps_override=fps_override,
                    source_fps=source_fps,
                )
                log_msgs.append(
                    f"Extracted {len(saved_paths)} images from video to {images_dir}"
                )
                if active_fps <= 0:
                    import cv2

                    # Attempt to read the actual video fps to store it in Tracking Data
                    cap = cv2.VideoCapture(str(media_path))
                    if cap.isOpened():
                        active_fps = cap.get(cv2.CAP_PROP_FPS)
                        cap.release()
            else:
                images_dir = str(Path(media_path).resolve())
                if not os.path.exists(images_dir) or not os.path.isdir(images_dir):
                    raise RuntimeError(f"Directory not found: {images_dir}")
                valid_exts = {".jpg", ".jpeg", ".png"}
                saved_paths = [
                    str(p)
                    for p in Path(images_dir).iterdir()
                    if p.suffix.lower() in valid_exts
                ]
                if not saved_paths:
                    raise RuntimeError(f"No valid images found in {images_dir}")
                log_msgs.append(
                    f"Using {len(saved_paths)} images from custom directory: {images_dir}"
                )

            if active_fps <= 0:
                active_fps = 30.0  # Standard fallback

            # === STEP 1: Feature Extraction (GPU via SiftGPU) ===
            log_msgs.append("Starting Feature Extraction (GPU)...")
            feature_extract(
                colmap_exe,
                db_path,
                images_dir,
                max_image_size=max_image_size,
                max_num_features=max_num_features,
                single_camera=single_camera,
                use_gpu=use_gpu,
                camera_model=camera_model,
            )

            # === STEP 2: Feature Matching (GPU via SiftGPU) ===
            log_msgs.append(f"Starting Feature Matching ({matching_type}, GPU)...")
            run_matcher(
                colmap_exe, db_path, matching_type=matching_type, use_gpu=use_gpu
            )

            # === STEP 3: View Graph Calibration (COLMAP 4.0+) ===
            if "glomap" in mapper_type.lower():
                log_msgs.append(
                    "Running View Graph Calibrator (focal length estimation)..."
                )
                run_view_graph_calibrator(colmap_exe, db_path)

            # === STEP 4: Reconstruction (GPU via cuDSS for Bundle Adjustment) ===
            log_msgs.append(f"Starting Reconstruction ({mapper_type}, GPU)...")
            model_path = run_mapper(
                colmap_exe,
                db_path,
                images_dir,
                sparse_dir,
                mapper_type=mapper_type,
                use_gpu=use_gpu,
            )
            log_msgs.append(f"Reconstruction saved to {model_path}")

            # === STEP 5: Parse Results ===
            log_msgs.append("Parsing reconstruction data...")
            text_model_path = workspace_dir / "sparse_txt"
            convert_model_to_text(colmap_exe, model_path, text_model_path)

            cameras, images_data, points3D = read_model(text_model_path)
            log_msgs.append(
                f"Parsed {len(cameras)} cameras, {len(images_data)} images, {len(points3D)} 3D points."
            )
            print(log_msgs[-1])

            reconstruction_data = {
                "workspace_dir": str(workspace_dir),
                "model_path": str(model_path),
                "text_model_path": str(text_model_path),
                "cameras": cameras,
                "images": images_data,
                "points3D": points3D,
                "images_dir": images_dir,
                "saved_paths": saved_paths,
                "fps": active_fps,
            }

            tracking_data = {
                "cameras": cameras,
                "images": images_data,
                "points3D": points3D,
                "images_dir": images_dir,
                "saved_paths": saved_paths,
                "fps": active_fps,
            }
            # Sort saved paths to preserve sequence order
            saved_paths = sorted(saved_paths)

            log_msgs.append("Loading images into tensor for ComfyUI preview...")
            import cv2
            import numpy as np
            import torch

            img_list = []
            for p in saved_paths:
                img = cv2.imread(p)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img_list.append(img.astype(np.float32) / 255.0)

            if img_list:
                images_tensor = torch.from_numpy(np.stack(img_list))
            else:
                images_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)

            return io.NodeOutput(
                reconstruction_data, tracking_data, images_tensor, "\n".join(log_msgs)
            )

        except Exception as e:
            log_msgs.append(f"ERROR: {str(e)}")
            print(f"[GLOMAP ERROR] {str(e)}")
            raise RuntimeError("\n".join(log_msgs))
