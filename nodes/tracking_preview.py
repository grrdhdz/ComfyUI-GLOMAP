import torch
import numpy as np
from comfy_api.latest import io
from ..core.reprojection import draw_tracking_points_on_frame

GLOMAP_TRACKING_DATA = io.Custom("GLOMAP_TRACKING_DATA")

class GLOMAPTrackingPreview(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="GLOMAPTrackingPreview",
            display_name="GLOMAP Tracking Preview",
            category="3D/GLOMAP",
            description="Visualize tracking points overlaid on video frames",
            inputs=[
                io.Image.Input("images", tooltip="Original video frames"),
                GLOMAP_TRACKING_DATA.Input("tracking_data"),
                io.Int.Input("point_size", default=4, min=1, max=20),
                io.Combo.Input("point_color", options=[
                    "green", "cyan", "yellow", "by_error"
                ]),
            ],
            outputs=[
                io.Image.Output(display_name="preview_images"),
            ],
        )

    @classmethod
    def execute(cls, images, tracking_data, point_size, point_color) -> io.NodeOutput:
        b, h, w, c = images.shape
        images_tensor = images.cpu().numpy()
        out_images = []
        
        idx_to_image_data = {}
        for img_id, img_data in tracking_data["images"].items():
            try:
                frame_idx = int(img_data.name.split("_")[1].split(".")[0])
                idx_to_image_data[frame_idx] = img_data
            except Exception:
                pass
                
        for i in range(b):
            frame = (np.clip(images_tensor[i], 0, 1) * 255).astype(np.uint8)
            if i in idx_to_image_data:
                frame = draw_tracking_points_on_frame(
                    frame, 
                    idx_to_image_data[i], 
                    tracking_data["points3D"], 
                    tracking_data["cameras"],
                    point_size, point_color
                )
            out_images.append(frame.astype(np.float32) / 255.0)
            
        out_tensor = torch.from_numpy(np.stack(out_images))
        return io.NodeOutput(out_tensor)
