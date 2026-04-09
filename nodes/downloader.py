from comfy_api.latest import io
from ..core.downloader_utils import resolve_colmap, resolve_blender_path
from ..core.gpu_utils import get_gpu_info

GLOMAP_CONFIG = io.Custom("GLOMAP_CONFIG")


class GLOMAPSetup(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="GLOMAPSetup",
            display_name="(down)Load GLOMAP Setup",
            category="3D/GLOMAP",
            description="Downloads and configures COLMAP 4.0.2 (with integrated GLOMAP) and Blender for camera tracking",
            inputs=[
                io.Combo.Input(
                    "colmap_version",
                    options=[
                        "v4.0.2 Windows CUDA",
                        "v4.0.2 Windows cuDSS (Custom GPU Build)",
                        "v4.0.2 Windows CPU (No-CUDA)",
                        "Linux / Mac (System Install)",
                    ],
                    tooltip="cuDSS = custom build with GPU-accelerated Bundle Adjustment. Standard CUDA uses official release. Linux/Mac users install manually.",
                ),
                io.Boolean.Input(
                    "use_blender_portable",
                    default=True,
                    tooltip="If True, uses the builtin portable Blender (downloads if missing). If False, uses the custom path below.",
                ),
                io.String.Input(
                    "blender_path",
                    default="proporciona un path",
                    tooltip="Only used if use_blender_portable is False. Point to your blender.exe",
                ),
            ],
            outputs=[
                GLOMAP_CONFIG.Output(display_name="config"),
                io.String.Output(display_name="status"),
            ],
            is_output_node=False,
        )

    @classmethod
    def execute(
        cls, colmap_version, use_blender_portable, blender_path
    ) -> io.NodeOutput:
        status_msgs = []

        # 1. Resolve GPU Info
        gpu_info = get_gpu_info()
        gpu_msg = f"GPU: {gpu_info['name']} ({gpu_info['vram_gb']} GB VRAM, CUDA {gpu_info['cuda_version']})"
        if not gpu_info["is_available"]:
            gpu_msg = "GPU: Not available or CUDA not found. Expect slow performance."
        status_msgs.append(gpu_msg)
        print(f"[GLOMAP Setup] {gpu_msg}")

        # 2. Resolve COLMAP (COLMAP 4.0.2 includes GLOMAP as global_mapper)
        resolved_colmap = None
        try:
            resolved_colmap = resolve_colmap(
                colmap_version, user_path="auto", auto_download=True
            )
            colmap_msg = f"COLMAP: Ready at {resolved_colmap}"
            status_msgs.append(colmap_msg)
            print(f"[GLOMAP Setup] {colmap_msg}")

            if "cuDSS" in colmap_version:
                status_msgs.append(
                    "Mode: Custom cuDSS build — GPU-accelerated Bundle Adjustment + Global Positioning"
                )
            else:
                status_msgs.append(
                    "Mode: Official COLMAP — GPU used for Feature Extraction + Matching"
                )
        except Exception as e:
            msg = f"COLMAP ERROR: {str(e)}"
            status_msgs.append(msg)
            print(f"[GLOMAP Setup] {msg}")

        # 3. Resolve Blender
        try:
            if use_blender_portable:
                resolved_blender = resolve_blender_path(
                    user_path="auto", auto_download=True
                )
                blender_msg = f"Blender: Portable ready at {resolved_blender}"
            else:
                if not blender_path.strip():
                    blender_msg = (
                        "Blender: Custom path is empty. Exporting to FBX/ABC will fail."
                    )
                    resolved_blender = None
                else:
                    resolved_blender = resolve_blender_path(
                        user_path=blender_path, auto_download=False
                    )
                    blender_msg = f"Blender: Custom path verified at {resolved_blender}"
            status_msgs.append(blender_msg)
            print(f"[GLOMAP Setup] {blender_msg}")
        except Exception as e:
            msg = f"Blender ERROR: {str(e)}"
            status_msgs.append(msg)
            print(f"[GLOMAP Setup] {msg}")
            resolved_blender = None

        config = {
            "colmap_exe": resolved_colmap,
            "blender_exe": resolved_blender,
            "gpu_info": gpu_info,
        }

        final_status = "\n".join(status_msgs)
        return io.NodeOutput(config, final_status)
