import subprocess
from pathlib import Path

def run_colmap_command(cmd_args, cwd=None):
    """
    Executes a COLMAP CLI command and monitors its output.
    cmd_args: list of string arguments, e.g. ["C:/path/to/COLMAP.bat", "feature_extractor", ...]
    """
    print(f"[COLMAP Runner] Executing: {' '.join(cmd_args)}")
    
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        bufsize=1
    )
    
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
        
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        raise RuntimeError(f"COLMAP command failed with return code {return_code}. Args: {cmd_args}")

def feature_extract(colmap_exe, db_path, images_dir, max_image_size=4096, max_num_features=16384, single_camera=True, use_gpu=True, camera_model="SIMPLE_RADIAL"):
    args = [
        colmap_exe, "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(images_dir),
        "--ImageReader.single_camera", "1" if single_camera else "0",
        "--ImageReader.camera_model", camera_model,
        "--FeatureExtraction.max_image_size", str(max_image_size),
        "--SiftExtraction.max_num_features", str(max_num_features),
        "--FeatureExtraction.use_gpu", "1" if use_gpu else "0",
    ]
    run_colmap_command(args)

def run_matcher(colmap_exe, db_path, matching_type="sequential", use_gpu=True, vocab_tree_path=""):
    if matching_type == "sequential":
        args = [
            colmap_exe, "sequential_matcher",
            "--database_path", str(db_path),
            "--SequentialMatching.overlap", "10",
            "--SequentialMatching.loop_detection", "0",
            "--FeatureMatching.use_gpu", "1" if use_gpu else "0",
        ]
    elif matching_type == "exhaustive":
        args = [
            colmap_exe, "exhaustive_matcher",
            "--database_path", str(db_path),
            "--FeatureMatching.use_gpu", "1" if use_gpu else "0",
        ]
    elif matching_type == "vocab_tree":
        args = [
            colmap_exe, "vocab_tree_matcher",
            "--database_path", str(db_path),
            "--VocabTreeMatching.vocab_tree_path", str(vocab_tree_path),
            "--FeatureMatching.use_gpu", "1" if use_gpu else "0",
        ]
    else:
        raise ValueError(f"Unknown matching type: {matching_type}")
        
    run_colmap_command(args)

def run_view_graph_calibrator(colmap_exe, db_path):
    """
    Pre-calibrates focal lengths using the view graph.
    This is critical for video frames that lack EXIF focal length data.
    Must be run AFTER matching and BEFORE global_mapper.
    """
    args = [
        colmap_exe, "view_graph_calibrator",
        "--database_path", str(db_path),
    ]
    run_colmap_command(args)

def run_mapper(colmap_exe, db_path, images_dir, output_path, mapper_type="glomap"):
    Path(output_path).mkdir(parents=True, exist_ok=True)
    
    cmd = "global_mapper" if "glomap" in mapper_type.lower() else "mapper"
        
    args = [
        colmap_exe, cmd,
        "--database_path", str(db_path),
        "--image_path", str(images_dir),
        "--output_path", str(output_path)
    ]
    
    run_colmap_command(args)
    
    # In incremental mapping, it outputs to 0/ 1/ subdirectories, we should return the best model path (0).
    # With global_mapper, it usually directly writes cameras.bin, images.bin, points3D.bin to the target directory.
    expected_incremental_dir = Path(output_path) / "0"
    if expected_incremental_dir.exists() and (expected_incremental_dir / "cameras.bin").exists():
        return str(expected_incremental_dir)
    return str(output_path)

def convert_model_to_text(colmap_exe, input_path, output_path):
    Path(output_path).mkdir(parents=True, exist_ok=True)
    args = [
        colmap_exe, "model_converter",
        "--input_path", str(input_path),
        "--output_path", str(output_path),
        "--output_type", "TXT"
    ]
    run_colmap_command(args)
