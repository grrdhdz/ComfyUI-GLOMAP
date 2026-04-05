import torch
import numpy as np
from PIL import Image
from pathlib import Path
from tqdm import tqdm

def save_tensor_images(images, workspace_dir: Path, filename_prefix="frame_", fps_override=0.0, original_fps=30.0):
    """
    Saves a ComfyUI IMAGE tensor to disk as individual high-quality JPEG files.
    ComfyUI IMAGE tensors are shaped [B, H, W, C] and value range is 0.0 - 1.0.
    """
    images_dir = workspace_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    b, h, w, c = images.shape
    
    step = 1
    if fps_override > 0.0 and fps_override < original_fps:
        step = max(1, int(round(original_fps / fps_override)))
        
    print(f"[Frame Prep] Saving frames to {images_dir}. Sub-sample step: {step}. Total original frames: {b}")
    
    saved_paths = []
    
    for i in tqdm(range(0, b, step), desc="Saving frames"):
        img_tensor = images[i].cpu().numpy()
        img_array = (np.clip(img_tensor, 0, 1) * 255.0).astype(np.uint8)
        
        if c == 4:
            img_array = img_array[:, :, :3]
            
        img = Image.fromarray(img_array, mode="RGB")
        file_path = images_dir / f"{filename_prefix}{i:04d}.jpg"
        img.save(file_path, "JPEG", quality=98)
        saved_paths.append(str(file_path))
        
    return str(images_dir), saved_paths
