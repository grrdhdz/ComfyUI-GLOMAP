import torch
import numpy as np
from PIL import Image
from pathlib import Path
import cv2
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

def extract_frames_from_video(video_path, workspace_dir: Path, filename_prefix="frame_", fps_override=0.0, source_fps=0.0):
    """
    Extracts frames from a video file directly to disk using OpenCV, bypassing ComfyUI tensor RAM entirely.
    """
    images_dir = workspace_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")
        
    detected_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    original_fps = source_fps if source_fps > 0.0 else detected_fps
    if original_fps <= 0: original_fps = 30.0
    
    step = 1
    if fps_override > 0.0 and fps_override < original_fps:
        step = max(1, int(round(original_fps / fps_override)))
        
    print(f"[Frame Prep] Extracting frames to {images_dir}. Sub-sample step: {step}. Total original frames: {total_frames}")
    
    saved_paths = []
    frame_idx = 0
    
    with tqdm(total=total_frames, desc="Extracting frames") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % step == 0:
                file_path = images_dir / f"{filename_prefix}{frame_idx:04d}.jpg"
                # Save as high-quality JPEG
                cv2.imwrite(str(file_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
                saved_paths.append(str(file_path))
                
            frame_idx += 1
            pbar.update(1)
            
    cap.release()
    return str(images_dir), saved_paths
