import os
import numpy as np
from collections import namedtuple

Camera = namedtuple("Camera", ["id", "model", "width", "height", "params"])
Image = namedtuple("Image", ["id", "qvec", "tvec", "camera_id", "name", "xys", "point3D_ids"])
Point3D = namedtuple("Point3D", ["id", "xyz", "rgb", "error"])

def qvec2rotmat(qvec):
    return np.array([
        [1 - 2 * qvec[2]**2 - 2 * qvec[3]**2,
         2 * qvec[1] * qvec[2] - 2 * qvec[0] * qvec[3],
         2 * qvec[3] * qvec[1] + 2 * qvec[0] * qvec[2]],
        [2 * qvec[1] * qvec[2] + 2 * qvec[0] * qvec[3],
         1 - 2 * qvec[1]**2 - 2 * qvec[3]**2,
         2 * qvec[2] * qvec[3] - 2 * qvec[0] * qvec[1]],
        [2 * qvec[3] * qvec[1] - 2 * qvec[0] * qvec[2],
         2 * qvec[2] * qvec[3] + 2 * qvec[0] * qvec[1],
         1 - 2 * qvec[1]**2 - 2 * qvec[2]**2]])

def read_cameras_text(path):
    cameras = {}
    if not os.path.exists(path):
        return cameras
    with open(path, "r") as fid:
        for line in fid:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            elems = line.split()
            camera_id = int(elems[0])
            model = elems[1]
            width = int(elems[2])
            height = int(elems[3])
            params = np.array(tuple(map(float, elems[4:])))
            cameras[camera_id] = Camera(id=camera_id, model=model,
                                        width=width, height=height, params=params)
    return cameras

def read_images_text(path):
    images = {}
    if not os.path.exists(path):
        return images
    with open(path, "r") as fid:
        while True:
            line = fid.readline()
            if not line:
                break
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            elems = line.split()
            image_id = int(elems[0])
            qvec = np.array(tuple(map(float, elems[1:5])))
            tvec = np.array(tuple(map(float, elems[5:8])))
            camera_id = int(elems[8])
            image_name = elems[9]
            
            elems2 = fid.readline().strip().split()
            xys = np.column_stack([tuple(map(float, elems2[0::3])),
                                   tuple(map(float, elems2[1::3]))]) if len(elems2) > 0 else np.zeros((0, 2))
            point3D_ids = np.array(tuple(map(int, elems2[2::3]))) if len(elems2) > 0 else np.zeros((0,), dtype=int)
            images[image_id] = Image(id=image_id, qvec=qvec, tvec=tvec,
                                     camera_id=camera_id, name=image_name, xys=xys, point3D_ids=point3D_ids)
    return images

def read_points3D_text(path):
    points3D = {}
    if not os.path.exists(path):
        return points3D
    with open(path, "r") as fid:
        for line in fid:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            elems = line.split()
            point3D_id = int(elems[0])
            xyz = np.array(tuple(map(float, elems[1:4])))
            rgb = np.array(tuple(map(int, elems[4:7])))
            error = float(elems[7])
            points3D[point3D_id] = Point3D(id=point3D_id, xyz=xyz, rgb=rgb, error=error)
    return points3D

def read_model(path, ext=".txt"):
    cameras = read_cameras_text(os.path.join(path, "cameras" + ext))
    images = read_images_text(os.path.join(path, "images" + ext))
    points3D = read_points3D_text(os.path.join(path, "points3D" + ext))
    return cameras, images, points3D
