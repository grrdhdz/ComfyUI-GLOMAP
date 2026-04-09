import subprocess
from pathlib import Path


def run_colmap_command(cmd_args, cwd=None):
    print(f"[COLMAP Runner] Executing: {' '.join(str(a) for a in cmd_args)}")

    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        bufsize=1,
    )

    for line in iter(process.stdout.readline, ""):
        print(line, end="")

    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        raise RuntimeError(
            f"COLMAP command failed with return code {return_code}. Args: {cmd_args}"
        )


def _detect_flag(colmap_exe, subcommand, flag_name):
    """Check if a specific flag exists in a COLMAP subcommand's help output."""
    try:
        help_out = subprocess.check_output(
            [colmap_exe, subcommand, "--help"],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        help_out = e.output
    return flag_name in help_out


def feature_extract(
    colmap_exe,
    db_path,
    images_dir,
    max_image_size=4096,
    max_num_features=16384,
    single_camera=True,
    use_gpu=True,
    camera_model="SIMPLE_RADIAL",
):
    """Extract SIFT features from images using GPU (SiftGPU) when available."""
    # Detect modern flag namespace (COLMAP 4.0+)
    use_feature_ext_ns = _detect_flag(
        colmap_exe, "feature_extractor", "--FeatureExtraction.use_gpu"
    )

    args = [
        colmap_exe,
        "feature_extractor",
        "--database_path",
        str(db_path),
        "--image_path",
        str(images_dir),
        "--ImageReader.single_camera",
        "1" if single_camera else "0",
        "--ImageReader.camera_model",
        camera_model,
        # max_num_features is usually still under SiftExtraction in 4.0.2
        "--SiftExtraction.max_num_features",
        str(max_num_features),
    ]

    if use_feature_ext_ns:
        args.extend([
            "--FeatureExtraction.use_gpu", "1" if use_gpu else "0",
            "--FeatureExtraction.max_image_size", str(max_image_size)
        ])
    else:
        args.extend([
            "--SiftExtraction.use_gpu", "1" if use_gpu else "0",
            "--SiftExtraction.max_image_size", str(max_image_size)
        ])

    run_colmap_command(args)


def run_matcher(
    colmap_exe, db_path, matching_type="sequential", use_gpu=True, vocab_tree_path=""
):
    """Run feature matching using GPU when available."""
    # Detect modern flag namespace (COLMAP 4.0+)
    use_feature_match_ns = _detect_flag(
        colmap_exe, "sequential_matcher", "--FeatureMatching.use_gpu"
    )

    gpu_args = [
        "--FeatureMatching.use_gpu" if use_feature_match_ns else "--SiftMatching.use_gpu",
        "1" if use_gpu else "0",
    ]

    if matching_type == "sequential":
        args = [
            colmap_exe,
            "sequential_matcher",
            "--database_path",
            str(db_path),
            "--SequentialMatching.overlap",
            "10",
        ] + gpu_args
    elif matching_type == "exhaustive":
        args = [
            colmap_exe,
            "exhaustive_matcher",
            "--database_path",
            str(db_path),
        ] + gpu_args
    elif matching_type == "vocab_tree":
        args = [
            colmap_exe,
            "vocab_tree_matcher",
            "--database_path",
            str(db_path),
            "--VocabTreeMatching.vocab_tree_path",
            str(vocab_tree_path),
        ] + gpu_args
    else:
        raise ValueError(f"Unknown matching type: {matching_type}")

    run_colmap_command(args)


def run_view_graph_calibrator(colmap_exe, db_path):
    """
    Pre-calibrates focal lengths using the view graph.
    Critical for video frames that lack EXIF focal length data.
    Must be run AFTER matching and BEFORE global_mapper.
    Available in COLMAP 4.0+.
    """
    try:
        help_out = subprocess.check_output(
            [colmap_exe, "help"], stderr=subprocess.STDOUT, text=True
        )
        if "view_graph_calibrator" not in help_out:
            print(
                "[COLMAP Runner] view_graph_calibrator not available in this COLMAP version. "
                "Skipping — global_mapper will handle calibration internally."
            )
            return
    except Exception as e:
        print(
            f"[COLMAP Runner] Warning: could not check for view_graph_calibrator: {e}"
        )
        return

    args = [
        colmap_exe,
        "view_graph_calibrator",
        "--database_path",
        str(db_path),
    ]
    run_colmap_command(args)


def run_mapper(
    colmap_exe,
    db_path,
    images_dir,
    output_path,
    mapper_type="glomap",
    use_gpu=True,
):
    """
    Run 3D reconstruction using either global (GLOMAP) or incremental mapper.

    For global mapper (GLOMAP integrated into COLMAP 4.0+):
      - Uses --BundleAdjustment.use_gpu for GPU-accelerated bundle adjustment via cuDSS
      - Uses --GlobalPositioning.use_gpu for GPU-accelerated global positioning via cuDSS

    For incremental mapper:
      - Uses --Mapper.ba_use_gpu for GPU-accelerated bundle adjustment
    """
    Path(output_path).mkdir(parents=True, exist_ok=True)

    is_global = "glomap" in mapper_type.lower() or "global" in mapper_type.lower()

    if is_global:
        # COLMAP 4.0+ integrated global_mapper (was GLOMAP standalone)
        # GPU flags in integrated version: 
        # --GlobalMapper.ba_ceres_use_gpu and --GlobalMapper.gp_use_gpu
        args = [
            colmap_exe,
            "global_mapper",
            "--database_path",
            str(db_path),
            "--image_path",
            str(images_dir),
            "--output_path",
            str(output_path),
            "--GlobalMapper.ba_ceres_use_gpu",
            "1" if use_gpu else "0",
            "--GlobalMapper.gp_use_gpu",
            "1" if use_gpu else "0",
        ]
        run_colmap_command(args)
    else:
        # Incremental mapper
        args = [
            colmap_exe,
            "mapper",
            "--database_path",
            str(db_path),
            "--image_path",
            str(images_dir),
            "--output_path",
            str(output_path),
            "--Mapper.ba_use_gpu",
            "1" if use_gpu else "0",
        ]
        run_colmap_command(args)

    # Check for incremental mapper output structure (subfolder "0")
    expected_incremental_dir = Path(output_path) / "0"
    if (
        expected_incremental_dir.exists()
        and (expected_incremental_dir / "cameras.bin").exists()
    ):
        return str(expected_incremental_dir)
    return str(output_path)


def convert_model_to_text(colmap_exe, input_path, output_path):
    """Convert binary model to text format for parsing."""
    Path(output_path).mkdir(parents=True, exist_ok=True)
    args = [
        colmap_exe,
        "model_converter",
        "--input_path",
        str(input_path),
        "--output_path",
        str(output_path),
        "--output_type",
        "TXT",
    ]
    run_colmap_command(args)
