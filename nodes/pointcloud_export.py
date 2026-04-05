from comfy_api.latest import io
from pathlib import Path
from ..core.camera_converter import export_ply
import folder_paths

GLOMAP_RECONSTRUCTION = io.Custom("GLOMAP_RECONSTRUCTION")

class GLOMAPPointCloudExport(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="GLOMAPPointCloudExport",
            display_name="GLOMAP Point Cloud Export",
            category="3D/GLOMAP",
            description="Export point cloud as PLY file",
            inputs=[
                GLOMAP_RECONSTRUCTION.Input("reconstruction"),
                io.String.Input("output_path", default="", tooltip="Leave empty to use output dir"),
                io.String.Input("filename", default="pointcloud.ply"),
                io.Float.Input("scene_scale", default=1.0, min=0.001, max=1000.0)
            ],
            outputs=[
                io.String.Output(display_name="file_path"),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, reconstruction, output_path, filename, scene_scale) -> io.NodeOutput:
        if not output_path:
            out_dir = Path(reconstruction["workspace_dir"])
        else:
            out_dir = Path(output_path)
            
        out_file = out_dir / filename
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        path = export_ply(reconstruction, out_file, scene_scale)
        return io.NodeOutput(path)
