from comfy_api.latest import ComfyExtension
from .nodes.downloader import GLOMAPSetup
from .nodes.camera_tracker import GLOMAPCameraTracker
from .nodes.camera_exporter import GLOMAPExportCamera
from .nodes.tracking_preview import GLOMAPTrackingPreview

WEB_DIRECTORY = "./web"

class GLOMAPExtension(ComfyExtension):
    async def get_node_list(self):
        return [
            GLOMAPSetup,
            GLOMAPCameraTracker,
            GLOMAPExportCamera,
            GLOMAPTrackingPreview
        ]

async def comfy_entrypoint():
    return GLOMAPExtension()
