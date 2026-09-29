# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
from pathlib import Path

import falcor2.minitracer.tools as mt
import slangpy as spy

DATA_DIR = Path(__file__).parent.parent.parent / "data"

DEVICE_TYPES = {
    "automatic": spy.DeviceType.automatic,
    "d3d12": spy.DeviceType.d3d12,
    "vulkan": spy.DeviceType.vulkan,
    "metal": spy.DeviceType.metal,
    "cuda": spy.DeviceType.cuda,
}


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return result


def configure_pipeline(renderer: mt.Renderer, pipeline_api: str) -> None:
    if pipeline_api == "auto":
        return
    if pipeline_api == "inline":
        renderer.use_raytracing_pipeline = False
        return

    renderer.ray_tracing_pipeline_api = pipeline_api
    renderer.use_raytracing_pipeline = True


def main(
    input_path: str,
    device_type: spy.DeviceType = spy.DeviceType.automatic,
    pipeline_api: str = "auto",
    headless: bool = False,
    width: int = 1024,
    height: int = 1024,
    spp: int = 32,
    output: Path = Path("output/minitracer.png"),
) -> int:
    path = Path(input_path)

    if not path.exists():
        print(f"Input file does not exist: {path}")
        return 1

    device = mt.create_device(device_type)

    # Load scene + create camera, env map and renderer
    print(f"Loading scene from: {path}")
    scene = mt.load_scene(device, path, rescale_to=0.85)

    # Add env map (and optionally adjust brightness)
    envmap = scene.create_env_map(DATA_DIR / "assets/envmaps/aerodynamics_workshop_512.hdr")
    envmap.scaling_factor = spy.float3(1)

    # Create camera and renderer
    camera = scene.create_camera(width, height, 45)
    renderer = mt.create_renderer(device)
    configure_pipeline(renderer, pipeline_api)

    # Various config options for the renderer
    # Next-event estimation (default=true)
    renderer.enable_nee = True
    # Multiple importance sampling (default=true)
    renderer.enable_mis = True
    # Whether to include emissive triangles lighting (default=true)
    renderer.enable_emissive_triangles = True
    # Whether to include env map lighting (default=true)
    renderer.enable_env_map = True
    # Whether to use the env map as a background (default=true)
    renderer.env_map_as_background = False
    # Background color if not using env map (default=black)
    renderer.background_color = spy.float3(0.0, 0.0, 0.0)
    # Max path depth (default=3)
    renderer.max_depth = 3
    # Whether to apply simple ACES tone mapping (default=True)
    renderer.tone_map = True

    # Initial camera position
    radius = 1.8
    camera.transform.pos = spy.float3(radius, 0.2, 0)
    camera.transform.rot = spy.math.quat_from_look_at(
        -spy.math.normalize(camera.transform.pos), spy.float3(0, 1, 0)
    )

    # Enable this to add a ground plane
    # box = scene.create_box(spy.float3(10, 0.01, 10))
    # box.transform.pos = spy.float3(0, -0.425, 0)
    # grey_mat = scene.create_material("default")
    # grey_mat.albedo = scene.create_texture(16,16,spy.float3(0.25, 0.25, 0.25))
    # box.material = grey_mat

    active_api = (
        renderer.ray_tracing_pipeline_api.value if renderer.use_raytracing_pipeline else "inline"
    )
    print(f"Rendering with {active_api} ray tracing on {device.info.type.name}")

    if headless:
        output.parent.mkdir(parents=True, exist_ok=True)
        image = renderer.render(scene, camera, spp=spp)
        mt.save_image(image, output)
        print(f"Saved {output}")
        return 0

    viewer = mt.create_viewer(scene, camera, renderer, spp=spp)
    viewer.run()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a glTF or USD scene with MiniTracer.",
        epilog=(
            "Example: python examples/minitracer/basic.py "
            "data/assets/kronos/Box/glTF-Binary/Box.glb --device vulkan "
            "--pipeline-api structural --headless --width 128 --height 128 --spp 4"
        ),
    )
    parser.add_argument("input_path", help="Path to a .gltf, .glb, or USD scene")
    parser.add_argument("--device", choices=DEVICE_TYPES, default="automatic")
    parser.add_argument(
        "--pipeline-api",
        choices=("auto", "inline", "legacy", "structural"),
        default="auto",
        help="Ray tracing path (default: inline, except legacy pipeline on CUDA)",
    )
    parser.add_argument("--headless", action="store_true", help="Render one image without a window")
    parser.add_argument("--width", type=positive_int, default=1024)
    parser.add_argument("--height", type=positive_int, default=1024)
    parser.add_argument("--spp", type=positive_int, default=32, help="Samples per pixel")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/minitracer.png"),
        help="Headless output image path",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        main(
            input_path=args.input_path,
            device_type=DEVICE_TYPES[args.device],
            pipeline_api=args.pipeline_api,
            headless=args.headless,
            width=args.width,
            height=args.height,
            spp=args.spp,
            output=args.output,
        )
    )
