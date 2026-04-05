import cv2
import numpy as np

def draw_tracking_points_on_frame(frame, image_data, points_data, cameras, point_size=4, point_color="green"):
    # frame is RGB uint8 numpy array [H, W, 3] or [H, W, 4]
    
    # We enforce contiguous array for cv2
    out_frame = np.ascontiguousarray(frame.copy())
    
    color = (0, 255, 0)
    if point_color == "cyan":
        color = (0, 255, 255)
    elif point_color == "yellow":
        color = (255, 255, 0)
        
    xys = image_data.xys
    p3d_ids = image_data.point3D_ids
    
    for xy, p3d_id in zip(xys, p3d_ids):
        # -1 means point is not triangulated into 3D
        if p3d_id != -1:
            u, v = int(xy[0]), int(xy[1])
            if point_color == "by_error" and p3d_id in points_data:
                err = points_data[p3d_id].error
                # Map error 0 to 2 pixels: Green to Red
                # OpenCV uses BGR for some drawing operations, but we are working directly on an RGB frame!
                r = int(min(255, (err / 2.0) * 255))
                g = int(min(255, max(0, 255 - r)))
                c = (r, g, 0) # RGB
                cv2.circle(out_frame, (u, v), point_size, c, -1)
            else:
                cv2.circle(out_frame, (u, v), point_size, color, -1)
                
    return out_frame
