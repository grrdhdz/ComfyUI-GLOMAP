import math
import numpy as np
from pathlib import Path
import shutil

def rotmat2euler(R):
    sy = math.sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])
    singular = sy < 1e-6
    if not singular:
        x = math.atan2(R[2,1] , R[2,2])
        y = math.atan2(-R[2,0], sy)
        z = math.atan2(R[1,0], R[0,0])
    else:
        x = math.atan2(-R[1,2], R[1,1])
        y = math.atan2(-R[2,0], sy)
        z = 0
    return np.array([x, y, z])

def get_camera_poses(reconstruction_data):
    """ Returns ordered list of frame_idx and 4x4 matrices from camera to world. """
    images = reconstruction_data["images"]
    from .colmap_parser import qvec2rotmat
    
    poses = []
    for image_id, img in images.items():
        # Extrinsics map from World to Camera
        R = qvec2rotmat(img.qvec)
        t = img.tvec
        
        # We need Camera to World
        R_inv = R.T
        t_inv = -np.dot(R_inv, t)
        
        # Build 4x4 matrix
        mat = np.eye(4)
        mat[:3, :3] = R_inv
        mat[:3, 3] = t_inv
        
        # Name format expected: "frame_0000.jpg"
        try:
            frame_idx = int(img.name.split("_")[1].split(".")[0])
        except:
            frame_idx = image_id # fallback
            
        poses.append((frame_idx, mat))
        
    poses.sort(key=lambda x: x[0])
    return poses

def export_ply(reconstruction_data, out_path, scene_scale=1.0):
    points3D = reconstruction_data["points3D"]
    with open(out_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points3D)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        
        for p_id, p in points3D.items():
            xyz = p.xyz * scene_scale
            rgb = p.rgb
            f.write(f"{xyz[0]} {xyz[1]} {xyz[2]} {rgb[0]} {rgb[1]} {rgb[2]}\n")
            
    return str(out_path)

def export_colmap_native(reconstruction_data, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Just copy the text files
    txt_dir = Path(reconstruction_data["text_model_path"])
    for f in ["cameras.txt", "images.txt", "points3D.txt"]:
        src = txt_dir / f
        if src.exists():
            shutil.copy2(src, out_dir / f)
            
    return str(out_dir)

def export_nuke_nk(reconstruction_data, out_path, scene_scale=1.0, original_fps=30):
    poses = get_camera_poses(reconstruction_data)
    
    with open(out_path, 'w') as f:
        f.write(f"Camera3 {{\n")
        f.write(f" translate {{{{curve ")
        for frame, mat in poses:
            t = mat[:3, 3] * scene_scale
            f.write(f"x{frame} {t[0]} {t[1]} {t[2]} ")
        f.write(f"}}}}\n")
        
        f.write(f" rotate {{{{curve ")
        for frame, mat in poses:
            R = mat[:3, :3]
            # Nuke uses ZYX rotation by default, we need to convert correctly.
            # But simpler here is to provide basic euler
            euler = np.degrees(rotmat2euler(R))
            f.write(f"x{frame} {euler[0]} {euler[1]} {euler[2]} ")
        f.write(f"}}}}\n")
        f.write(f" name GLOMAP_Camera\n")
        f.write(f"}}\n")
        
    return str(out_path)
