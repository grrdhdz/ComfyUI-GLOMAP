import sys
import bpy
import json
import numpy as np

# Usage: blender --background --python scripts/blender_export.py -- --config config.json

def get_args():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]

def read_colmap_images(txt_path):
    images = []
    with open(txt_path, 'r') as f:
        while True:
            line = f.readline()
            if not line: break
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            elems = line.split()
            image_id = int(elems[0])
            qw, qx, qy, qz = map(float, elems[1:5])
            tx, ty, tz = map(float, elems[5:8])
            cam_id = int(elems[8])
            name = elems[9]
            
            images.append({
                'id': image_id, 'q': (qw, qx, qy, qz), 't': (tx, ty, tz), 'name': name
            })
            
            # Skip points line
            f.readline()
    return images

def read_colmap_points(txt_path):
    points = []
    with open(txt_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            elems = line.split()
            x, y, z = map(float, elems[1:4])
            r, g, b = map(int, elems[4:7])
            points.append((x, y, z, r, g, b))
    return points

def qvec2rotmat(qvec):
    qw, qx, qy, qz = qvec
    return np.array([
        [1 - 2 * qy**2 - 2 * qz**2, 2 * qx * qy - 2 * qw * qz, 2 * qz * qx + 2 * qw * qy],
        [2 * qx * qy + 2 * qw * qz, 1 - 2 * qx**2 - 2 * qz**2, 2 * qy * qz - 2 * qw * qx],
        [2 * qz * qx - 2 * qw * qy, 2 * qy * qz + 2 * qw * qx, 1 - 2 * qx**2 - 2 * qy**2]])

def main():
    args = get_args()
    if len(args) < 2:
        print("Missing config file argument")
        sys.exit(1)
        
    config_file = args[1]
    with open(config_file, 'r') as f:
        cfg = json.load(f)
        
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 1. Setup Camera
    cam_data = bpy.data.cameras.new("GLOMAP_CamData")
    # In a real impl we'd parse cameras.txt for focal length, assume 35mm equivalent for now
    cam_data.sensor_width = 36.0
    cam_data.lens = 35.0
    
    cam_obj = bpy.data.objects.new("GLOMAP_Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    
    # 2. Add animation keyframes
    images = read_colmap_images(cfg['images_txt'])
    scene_scale = cfg.get('scene_scale', 1.0)
    
    for img in images:
        try:
            frame_idx = int(img['name'].split('_')[1].split('.')[0])
        except:
            frame_idx = img['id']
            
        R = qvec2rotmat(img['q'])
        t = np.array(img['t'])
        
        # Colmap (World -> Cam) to Blender (Cam -> World)
        R_inv = R.T
        t_inv = -np.dot(R_inv, t) * scene_scale
        
        # Colmap coords to Blender Coords mapping (Opencv to Blender)
        # Blender Cam looks down -Z, Y is UP. OpenCV looks down +Z, -Y is UP.
        import mathutils
        world_mat = mathutils.Matrix(R_inv.tolist())
        world_mat.transpose()
        
        # Apply transforms
        cam_obj.location = t_inv
        
        # We need to rotate correctly for blender
        rot_mat_b = mathutils.Matrix(((1,0,0),(0,-1,0),(0,0,-1)))
        cam_obj.rotation_euler = (world_mat @ rot_mat_b).to_euler()
        
        cam_obj.keyframe_insert(data_path="location", frame=frame_idx)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame_idx)
        
    # 3. Add Point Cloud
    if cfg.get('export_pointcloud', True):
        points = read_colmap_points(cfg['points_txt'])
        mesh = bpy.data.meshes.new("GLOMAP_PointCloud")
        verts = [(p[0]*scene_scale, p[1]*scene_scale, p[2]*scene_scale) for p in points]
        mesh.from_pydata(verts, [], [])
        mesh.update()
        
        pc_obj = bpy.data.objects.new("GLOMAP_PointCloud", mesh)
        
        if cfg.get('up_axis') == 'Y_UP':
            # Note: Blender is naturally Z_UP, so if user wants Y_UP we rotate the whole scene before export
            pass 
            
        bpy.context.scene.collection.objects.link(pc_obj)

    # Transform entire scene if needed
    if cfg.get('up_axis') == 'Y_UP':
        root = bpy.data.objects.new("Root", None)
        bpy.context.scene.collection.objects.link(root)
        cam_obj.parent = root
        if cfg.get('export_pointcloud', True):
            pc_obj.parent = root
        root.rotation_euler = (np.pi/2, 0, 0) # Rotate -90 on X so Y is UP in FBX? Depends on FBX exporter settings.
        
    # 4. Export
    fmt = cfg['format']
    out_path = cfg['out_path']
    
    bpy.ops.object.select_all(action='SELECT')
    
    if fmt == 'fbx':
        bpy.ops.export_scene.fbx(filepath=out_path, use_selection=True, global_scale=1.0)
    elif fmt == 'alembic':
        bpy.ops.wm.alembic_export(filepath=out_path, selected=True)
        
    print(f"Blender export completed: {out_path}")

if __name__ == "__main__":
    main()
