from comfy_api.latest import io
from pathlib import Path
import os
import subprocess
import json
import folder_paths
from ..core.camera_converter import export_ply as do_export_ply, export_colmap_native as do_export_colmap_native, export_nuke_nk

GLOMAP_RECONSTRUCTION = io.Custom("GLOMAP_RECONSTRUCTION")
GLOMAP_CONFIG = io.Custom("GLOMAP_CONFIG")

class GLOMAPExportCamera(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="GLOMAPExportCamera",
            display_name="GLOMAP Export Camera",
            category="3D/GLOMAP",
            description="Export tracked camera to FBX, Nuke, Alembic, etc.",
            inputs=[
                GLOMAP_RECONSTRUCTION.Input("reconstruction"),
                GLOMAP_CONFIG.Input("config", optional=True,
                    tooltip="Required for FBX/Alembic export (needs Blender)"),
                io.String.Input("output_directory", default="",
                    tooltip="Leave empty to use ComfyUI output dir"),
                io.String.Input("filename_prefix", default="glomap_camera"),
                
                io.Boolean.Input("export_fbx", default=True, tooltip="Export FBX for Blender/Maya"),
                io.Boolean.Input("export_alembic", default=False, tooltip="Export Alembic (.abc)"),
                io.Boolean.Input("export_nuke", default=False, tooltip="Export Nuke Camera3 script (.nk)"),
                io.Boolean.Input("export_ply", default=True, tooltip="Export sparse pointcloud (.ply)"),
                io.Boolean.Input("export_colmap_native", default=False, tooltip="Export raw COLMAP files"),
                
                io.Float.Input("scene_scale", default=1.0, min=0.001, max=1000.0,
                    tooltip="Scale factor for the exported scene"),
                io.Combo.Input("up_axis", options=["Y_UP", "Z_UP"],
                    tooltip="Y_UP for Maya/Nuke/Resolve, Z_UP for Blender"),
                io.Int.Input("original_fps", default=30, min=1, max=120,
                    tooltip="FPS of original footage for animation timing")
            ],
            outputs=[
                io.String.Output(display_name="export_dir"),
                io.String.Output(display_name="export_log"),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, reconstruction, config, output_directory, filename_prefix,
                export_fbx, export_alembic, export_nuke, export_ply, export_colmap_native, 
                scene_scale, up_axis, original_fps) -> io.NodeOutput:
        
        if not output_directory:
            base_out_dir = Path(reconstruction["workspace_dir"]) / "export"
        else:
            base_out_dir = Path(output_directory)
            
        base_out_dir.mkdir(parents=True, exist_ok=True)
        
        logs = []
        blender_formats = []
        if export_fbx: blender_formats.append("fbx")
        if export_alembic: blender_formats.append("alembic")
        
        # Clean prefix just in case user left an extension
        clean_prefix = filename_prefix.replace(".fbx", "").replace(".nk", "").replace(".abc", "").replace(".ply", "")
        
        if export_colmap_native:
            fmt_dir = base_out_dir / "colmap_native"
            fmt_dir.mkdir(parents=True, exist_ok=True)
            out_path = do_export_colmap_native(reconstruction, fmt_dir / clean_prefix)
            logs.append(f"Exported COLMAP native to {out_path}")
            
        if export_nuke:
            fmt_dir = base_out_dir / "nuke"
            fmt_dir.mkdir(parents=True, exist_ok=True)
            out_file = fmt_dir / f"{clean_prefix}.nk"
            out_path = export_nuke_nk(reconstruction, out_file, scene_scale, original_fps)
            logs.append(f"Exported Nuke script to {out_path}")
            
        if export_ply:
            fmt_dir = base_out_dir / "ply"
            fmt_dir.mkdir(parents=True, exist_ok=True)
            out_file = fmt_dir / f"{clean_prefix}.ply"
            out_path = do_export_ply(reconstruction, out_file, scene_scale)
            logs.append(f"Exported PLY to {out_path}")
            
        if export_fbx or export_alembic:
            blender_exe = config.get("blender_exe") if config else None
            if not blender_exe or not os.path.exists(blender_exe):
                raise RuntimeError("Blender executable not found in config. Please connect GLOMAP Setup node and enable Blender download.")
                
            for fmt in blender_formats:
                fmt_dir = base_out_dir / fmt
                fmt_dir.mkdir(parents=True, exist_ok=True)
                ext = ".fbx" if fmt == "fbx" else ".abc"
                out_file = fmt_dir / f"{clean_prefix}{ext}"
                
                # Prepare config for blender script
                blender_cfg = {
                    'images_txt': str(Path(reconstruction['text_model_path']) / "images.txt"),
                    'points_txt': str(Path(reconstruction['text_model_path']) / "points3D.txt"),
                    'out_path': str(out_file),
                    'format': fmt,
                    'scene_scale': scene_scale,
                    'up_axis': up_axis,
                    'export_pointcloud': export_ply
                }
                cfg_path = fmt_dir / f"{clean_prefix}_blender_cfg.json"
                with open(cfg_path, 'w') as f:
                    json.dump(blender_cfg, f)
                    
                script_path = Path(__file__).parent.parent / "scripts" / "blender_export.py"
                
                cmd = [
                    blender_exe, "--background", "--python", str(script_path),
                    "--", "--config", str(cfg_path)
                ]
                
                print(f"[GLOMAP Export] Running blender for {fmt}: {' '.join(cmd)}")
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                
                if result.returncode != 0:
                    raise RuntimeError(f"Blender export failed for {fmt}:\n{result.stdout}")
                    
                logs.append(f"Exported {fmt.upper()} to {out_file}")
            
        return io.NodeOutput(str(base_out_dir), "\n".join(logs))
