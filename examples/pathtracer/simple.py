# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import falcor2 as f2
import slangpy as spy
from falcor2.editor import Editor, EditorConfig, get_slang_include_paths, save_image
from falcor2.rendernodes import PathTracerPipeline

DESCRIPTION = "Example PathTracer"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENE_PATH = PROJECT_ROOT / "data/scenes/cornell-box.py"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

DEVICE_TYPES = {
    "automatic": spy.DeviceType.automatic,
    "d3d12": spy.DeviceType.d3d12,
    "vulkan": spy.DeviceType.vulkan,
    "cuda": spy.DeviceType.cuda,
}

PIPELINE_APIS = {
    "legacy": f2.RayTracingPipelineAPI.legacy,
    "structural": f2.RayTracingPipelineAPI.structural,
}


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return result


def non_negative_int(value: str) -> int:
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Example: python examples/pathtracer/simple.py --device-type vulkan "
            "--pipeline-api structural --frames 8 --output output/pathtracer-structural.png"
        ),
    )
    parser.add_argument(
        "--scene-path",
        type=Path,
        default=DEFAULT_SCENE_PATH,
        help="Path to a scene file.",
    )
    parser.add_argument(
        "--device-type",
        choices=DEVICE_TYPES,
        default="automatic",
        help="Device type used for renderer.",
    )
    parser.add_argument(
        "--pipeline-api",
        choices=PIPELINE_APIS,
        default="legacy",
        help="Ray-tracing pipeline shader API used for path-scatter rays.",
    )
    parser.add_argument("--width", type=positive_int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=positive_int, default=DEFAULT_HEIGHT)
    parser.add_argument("--spp", type=positive_int, default=1, help="Samples per rendered frame.")
    parser.add_argument("--max-depth", type=positive_int, default=3)
    parser.add_argument(
        "--frames",
        type=non_negative_int,
        default=0,
        help="Exit after this many rendered frames; zero runs until the window is closed.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Save the final rendered frame when the sample exits.",
    )
    return parser.parse_args(argv)


def create_pathtracer_device(
    device_type: spy.DeviceType,
    pipeline_api: str,
) -> spy.Device:
    """Create a presentation device with structural RT enabled when requested."""
    return spy.Device(
        type=device_type,
        compiler_options={
            "include_paths": [*get_slang_include_paths(), PROJECT_ROOT / "external"],
            "enable_experimental_features": pipeline_api == "structural",
        },
    )


def configure_pipeline(pipeline: PathTracerPipeline, args: argparse.Namespace) -> None:
    """Apply command-line path-tracing settings before the first render."""
    pipeline.spp = args.spp
    pipeline.path_tracer.ray_tracing_pipeline_api = PIPELINE_APIS[args.pipeline_api]
    pipeline.path_tracer.max_depth = args.max_depth
    pipeline.path_tracer.enable_nee = True
    pipeline.path_tracer.enable_mis = True
    pipeline.path_tracer.enable_analytic_lights = True
    pipeline.path_tracer.enable_environment_light = True
    pipeline.path_tracer.enable_emissive_triangles = True
    pipeline.path_tracer.env_map_as_background = True
    pipeline.tone_map = True


def main() -> int:
    args = parse_args()
    scene_path = args.scene_path.resolve()
    if not scene_path.exists():
        raise FileNotFoundError(f"Scene does not exist: {scene_path}")

    device = create_pathtracer_device(DEVICE_TYPES[args.device_type], args.pipeline_api)
    editor: Editor | None = None
    try:
        scene = f2.Scene.create(device, scene_path)

        pipeline = PathTracerPipeline.create(device)
        configure_pipeline(pipeline, args)

        editor = Editor.create(
            device,
            config=EditorConfig(
                width=args.width,
                height=args.height,
                title=DESCRIPTION,
                vsync=False,
            ),
            scene=scene,
        )

        path_tracer = pipeline.path_tracer
        print(f"Device: {device.info.type.name}")
        print(
            "PathTracer ray tracing: "
            f"{args.pipeline_api} scatter pipeline, "
            f"{path_tracer.visibility_ray_mode.name} visibility, "
            f"{path_tracer.scheduling_mode.name} scheduling"
        )
        print("The viewport overlay reports live frame rate; press Escape to exit.")

        rendered_frames = 0
        last_image = None
        while editor.update():
            if not editor.needs_render:
                continue
            last_image = pipeline(scene)
            editor.present(last_image)
            rendered_frames += 1
            if args.frames and rendered_frames >= args.frames:
                break

        if args.output is not None:
            if last_image is None:
                raise RuntimeError("No frame was rendered; cannot save output")
            save_image(last_image, args.output)
            print(f"Saved final frame: {args.output.resolve()}")
    finally:
        if editor is not None:
            editor.close()
        device.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
