import torch

def get_gpu_info():
    info = {
        "is_available": False,
        "device_count": 0,
        "name": "None",
        "vram_gb": 0,
        "cuda_version": "None"
    }
    
    if torch.cuda.is_available():
        info["is_available"] = True
        info["device_count"] = torch.cuda.device_count()
        info["name"] = torch.cuda.get_device_name(0)
        # get_device_properties total_memory is in bytes
        info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
        info["cuda_version"] = torch.version.cuda
        
    return info
