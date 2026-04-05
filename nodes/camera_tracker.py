import os
import time
from pathlib import Path
from comfy_api.latest import io
from ..core.frame_utils import save_tensor_images
from ..core.colmap_runner import feature_extract, run_matcher, run_view_graph_calibrator, run_mapper, convert_model_to_text
from ..core.colmap_parser import read_model
import folder_paths

GLOMAP_CONFIG = io.Custom("GLOMAP_CONFIG")
GLOMAP_RECONSTRUCTION = io.Custom("GLOMAP_RECONSTRUCTION")
GLOMAP_TRACKING_DATA = io.Custom("GLOMAP_TRACKING_DATA")

class GLOMAPCameraTracker(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="GLOMAPCameraTracker",
            display_name="GLOMAP Camera Tracker",
            category="3D/GLOMAP",
            description="3D camera tracking using GLOMAP/COLMAP",
            inputs=[
                GLOMAP_CONFIG.Input("config",
                    tooltip="Config from GLOMAP Setup node"),
                io.Image.Input("images",
                    tooltip="Image batch from VHS Load Video or image loader"),
                io.Combo.Input("mapper_type", 
                    options=["glomap (global)", "colmap (incremental)"],
                    tooltip="GLOMAP is faster, COLMAP is more robust"),
                io.Combo.Input("matching_type",
                    options=["sequential", "exhaustive", "vocab_tree"],
                    tooltip="Sequential is best for video footage"),
                io.Combo.Input("camera_model",
                    options=["SIMPLE_RADIAL", "RADIAL", "OPENCV", "PINHOLE"],
                    tooltip="Camera lens model. SIMPLE_RADIAL works for most cases"),
                io.Int.Input("max_image_size", default=4096, min=512, max=8192,
                    tooltip="Max dimension for feature extraction. 4096 for 4K"),
                io.Int.Input("max_num_features", default=16384, 
                    min=1024, max=65536,
                    tooltip="More features = better tracking but slower"),
                io.Boolean.Input("single_camera", default=True,
                    tooltip="All frames from same camera (true for video)"),
                io.Boolean.Input("use_gpu", default=True,
                    tooltip="Use CUDA GPU for feature extraction"),
                io.Float.Input("fps_override", default=0.0, min=0.0, max=120.0,
                    tooltip="0 = use all frames. Set value to subsample"),
            ],
            outputs=[
                GLOMAP_RECONSTRUCTION.Output(display_name="reconstruction"),
                GLOMAP_TRACKING_DATA.Output(display_name="tracking_data"),
                io.String.Output(display_name="log"),
            ],
        )

    @classmethod
    def execute(cls, config, images, mapper_type, matching_type,
                camera_model, max_image_size, max_num_features,
                single_camera, use_gpu, fps_override) -> io.NodeOutput:
        
        colmap_exe = config.get("colmap_exe")
        if not colmap_exe or not os.path.exists(colmap_exe):
            raise RuntimeError("COLMAP executable not found in config. Please check GLOMAP Setup node.")
            
        output_dir = Path(folder_paths.get_output_directory())
        workspace_dir = output_dir / "GLOMAP" / f"track_{int(time.time())}"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        db_path = workspace_dir / "database.db"
        sparse_dir = workspace_dir / "sparse"
        
        log_msgs = []
        log_msgs.append(f"Workspace created: {workspace_dir}")
        print(f"[GLOMAP] Workspace created: {workspace_dir}")
        
        try:
            images_dir, saved_paths = save_tensor_images(
                images, workspace_dir, fps_override=fps_override, original_fps=30.0
            ) 
            log_msgs.append(f"Saved {len(saved_paths)} images to {images_dir}")
            
            log_msgs.append("Starting Feature Extraction...")
            feature_extract(
                colmap_exe, db_path, images_dir, 
                max_image_size=max_image_size, 
                max_num_features=max_num_features, 
                single_camera=single_camera, 
                use_gpu=use_gpu, 
                camera_model=camera_model
            )
            
            log_msgs.append(f"Starting Feature Matching ({matching_type})...")
            run_matcher(
                colmap_exe, db_path, 
                matching_type=matching_type, 
                use_gpu=use_gpu
            )
            
            # Pre-calibrate focal lengths for video frames without EXIF data
            if "glomap" in mapper_type.lower():
                log_msgs.append("Running View Graph Calibrator (focal length estimation)...")
                run_view_graph_calibrator(colmap_exe, db_path)
            
            log_msgs.append(f"Starting Reconstruction ({mapper_type})...")
            model_path = run_mapper(
                colmap_exe, db_path, images_dir, sparse_dir, mapper_type=mapper_type
            )
            log_msgs.append(f"Reconstruction saved to {model_path}")
            
            log_msgs.append("Parsing reconstruction data...")
            text_model_path = workspace_dir / "sparse_txt"
            convert_model_to_text(colmap_exe, model_path, text_model_path)
            
            cameras, images_data, points3D = read_model(text_model_path)
            log_msgs.append(f"Parsed {len(cameras)} cameras, {len(images_data)} images, {len(points3D)} 3D points.")
            print(log_msgs[-1])
            
            reconstruction_data = {
                "workspace_dir": str(workspace_dir),
                "model_path": str(model_path),
                "text_model_path": str(text_model_path),
                "cameras": cameras,
                "images": images_data,
                "points3D": points3D,
                "images_dir": images_dir,
                "saved_paths": saved_paths
            }
            
            tracking_data = {
                "cameras": cameras,
                "images": images_data,
                "points3D": points3D,
                "images_dir": images_dir,
                "saved_paths": saved_paths
            }
            
            return io.NodeOutput(reconstruction_data, tracking_data, "\n".join(log_msgs))
            
        except Exception as e:
            log_msgs.append(f"ERROR: {str(e)}")
            print(f"[GLOMAP ERROR] {str(e)}")
            raise RuntimeError("\n".join(log_msgs))
