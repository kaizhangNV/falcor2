# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Interactive Cornell-box demo for structural ScenePicker and SelectionProbe tracing."""

from __future__ import annotations

import argparse
from pathlib import Path

import falcor2 as f2
import slangpy as spy
from falcor2.editor import Editor, EditorConfig, get_slang_include_paths, save_image
from falcor2.rendernodes import PathTracerPipeline

DESCRIPTION = "Falcor2 structural ScenePicker + SelectionProbe"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENE_PATH = PROJECT_ROOT / "data/scenes/cornell-box.py"
DEFAULT_OCCLUDED_ENTITY = "/cornell_box/tall_box_back/tall_box_back"

DEVICE_TYPES = {
    "automatic": spy.DeviceType.automatic,
    "d3d12": spy.DeviceType.d3d12,
    "vulkan": spy.DeviceType.vulkan,
}


def non_negative_int(value: str) -> int:
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return result


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Left-click an object in the viewport to exercise structural ScenePicker. "
            "Select a hidden mesh in the Outliner to see SelectionProbe highlight it "
            "through its occluder. Press F5 to toggle the editor and Escape to exit."
        ),
    )
    parser.add_argument("--scene-path", type=Path, default=DEFAULT_SCENE_PATH)
    parser.add_argument("--device", choices=DEVICE_TYPES, default="automatic")
    parser.add_argument("--width", type=positive_int, default=1280)
    parser.add_argument("--height", type=positive_int, default=720)
    parser.add_argument(
        "--spp", type=positive_int, default=1, help="Path-tracing samples per frame"
    )
    parser.add_argument("--max-depth", type=positive_int, default=3)
    parser.add_argument(
        "--show-occluded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run SelectionProbe so selected geometry remains visible through occluders",
    )
    parser.add_argument(
        "--initial-selection",
        default=DEFAULT_OCCLUDED_ENTITY,
        metavar="ENTITY_NAME",
        help=(
            "Select an entity at startup; use "
            f"'{DEFAULT_OCCLUDED_ENTITY}' to demonstrate an occluded selection"
        ),
    )
    parser.add_argument(
        "--frames",
        type=non_negative_int,
        default=0,
        help="Exit after this many rendered frames; zero runs interactively until closed",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Save the final post-overlay viewport when the sample exits",
    )
    return parser.parse_args()


def create_device(device_type: spy.DeviceType) -> spy.Device:
    """Create a presentation-capable device with structural RT enabled in Slang."""
    return spy.Device(
        type=device_type,
        compiler_options={
            "include_paths": get_slang_include_paths(),
            "enable_experimental_features": True,
        },
    )


def require_ray_tracing(device: spy.Device) -> None:
    if device.info.type not in (spy.DeviceType.d3d12, spy.DeviceType.vulkan):
        raise RuntimeError(
            "This interactive sample currently requires D3D12 or Vulkan; "
            f"automatic device selection chose {device.info.type.name}"
        )
    if not device.has_feature(spy.Feature.acceleration_structure):
        raise RuntimeError(f"{device.info.type.name} does not support acceleration structures")
    if not device.has_feature(spy.Feature.ray_tracing):
        raise RuntimeError(f"{device.info.type.name} does not support ray-tracing pipelines")


def configure_structural_scene_interaction(editor: Editor, show_occluded: bool) -> None:
    """Use structural pipeline tracing for both production editor RT passes."""
    editor.scene_picker.ray_tracing_pipeline_api = f2.RayTracingPipelineAPI.structural
    editor.scene_picker.use_raytracing_pipeline = True

    editor.selection_overlay.ray_tracing_pipeline_api = f2.RayTracingPipelineAPI.structural
    editor.selection_overlay.use_raytracing_pipeline = True

    options = editor.selection_overlay.options
    options.show_occluded = show_occluded
    options.selection_color = spy.float3(0.1, 1.0, 0.2)
    options.fill_opacity = 0.2
    editor.selection_overlay.options = options


def configure_path_tracer(device: spy.Device, args: argparse.Namespace) -> PathTracerPipeline:
    pipeline = PathTracerPipeline.create(device)
    pipeline.spp = args.spp
    pipeline.path_tracer.max_depth = args.max_depth
    pipeline.path_tracer.enable_nee = True
    pipeline.path_tracer.enable_mis = True
    pipeline.path_tracer.enable_analytic_lights = True
    pipeline.path_tracer.enable_environment_light = True
    pipeline.path_tracer.enable_emissive_triangles = True
    pipeline.path_tracer.env_map_as_background = True
    pipeline.tone_map = True
    return pipeline


def set_initial_selection(editor: Editor, entity_name: str | None) -> None:
    if entity_name is None:
        return
    scene = editor.scene
    assert scene is not None
    matches = scene.entities.find_all(entity_name)
    if not matches:
        raise ValueError(f"Scene has no entity named {entity_name!r}")
    entity = next(
        (
            candidate
            for candidate in matches
            if any(isinstance(component, f2.GeometryInstance) for component in candidate.components)
        ),
        matches[0],
    )
    editor.scene_editor.selected_object = entity
    # Make bounded one-frame captures useful as well. The interaction controller
    # will synchronize the same selection after the first presented frame.
    editor.selection_overlay.set_selected_entity(entity)
    print(f"Initial selection: {entity.name}")


def main() -> int:
    args = parse_args()
    scene_path = args.scene_path.resolve()
    if not scene_path.exists():
        raise FileNotFoundError(f"Scene does not exist: {scene_path}")

    device = create_device(DEVICE_TYPES[args.device])
    editor: Editor | None = None
    try:
        require_ray_tracing(device)
        scene = f2.Scene.create(device, scene_path)
        if scene.active_camera is None:
            raise RuntimeError(f"Scene does not contain an active camera: {scene_path}")
        # Assign stable geometry-instance IDs before an optional startup selection
        # builds SelectionOverlay's ID bitmap.
        scene.update()

        pipeline = configure_path_tracer(device, args)
        editor = Editor.create(
            device,
            config=EditorConfig(
                width=args.width,
                height=args.height,
                title=DESCRIPTION,
                vsync=True,
                mcp=False,
            ),
            scene=scene,
        )
        configure_structural_scene_interaction(editor, args.show_occluded)
        set_initial_selection(editor, args.initial_selection)

        print(f"Device: {device.info.type.name}")
        print("ScenePicker ray tracing: structural pipeline")
        print("SelectionProbe ray tracing: structural pipeline")
        print(
            "Main PathTracer: unchanged "
            "(this demo only ports editor picking and selection tracing)"
        )
        print("Left-click viewport geometry to pick it; press Escape to exit.")

        rendered_frames = 0
        while editor.update():
            if not editor.needs_render:
                continue
            editor.present(pipeline(scene))
            rendered_frames += 1
            if args.frames and rendered_frames >= args.frames:
                break

        if args.output is not None:
            if editor.output is None:
                raise RuntimeError("No frame was rendered; cannot save output")
            save_image(editor.output.color_target, args.output)
            print(f"Saved post-overlay viewport: {args.output.resolve()}")
    finally:
        if editor is not None:
            editor.close()
        device.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
