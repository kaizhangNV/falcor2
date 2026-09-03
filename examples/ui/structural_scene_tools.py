# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Render a standalone ScenePicker -> SelectionOverlay structural RT example.

The sample builds two overlapping triangle quads. ScenePicker produces the visible geometry-ID
texture, then SelectionOverlay consumes that exact texture and traces through the front quad to
highlight the selected rear quad. Three PNG files are written so the result is easy to inspect
without running the Falcor editor.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import slangpy as spy

import falcor2 as f2
import falcor2.ui as ui

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "structural-scene-tools"

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


@dataclass
class SampleScene:
    scene: f2.Scene
    camera: f2.Camera
    front_entity: f2.Entity
    front_instance: f2.GeometryInstance
    rear_entity: f2.Entity
    rear_instance: f2.GeometryInstance


class PipelineService(Protocol):
    ray_tracing_pipeline_api: f2.RayTracingPipelineAPI
    use_raytracing_pipeline: bool


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device",
        choices=DEVICE_TYPES,
        default="vulkan",
        help="Graphics backend (default: vulkan).",
    )
    parser.add_argument(
        "--pipeline-api",
        choices=PIPELINE_APIS,
        default="structural",
        help="Pipeline shader API (default: structural).",
    )
    parser.add_argument("--width", type=positive_int, default=640)
    parser.add_argument("--height", type=positive_int, default=480)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"PNG output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    return parser.parse_args()


def create_device(device_type: spy.DeviceType) -> spy.Device:
    return spy.Device(
        type=device_type,
        compiler_options={
            "include_paths": [spy.SHADER_PATH, PROJECT_ROOT / "slang"],
            "enable_experimental_features": True,
        },
    )


def add_quad(
    scene: f2.Scene,
    material: f2.Material,
    *,
    name: str,
    z: float,
    size: float,
) -> tuple[f2.Entity, f2.GeometryInstance]:
    half_size = size * 0.5
    positions = np.array(
        [
            [-half_size, -half_size, z],
            [+half_size, -half_size, z],
            [-half_size, +half_size, z],
            [+half_size, +half_size, z],
        ],
        dtype=np.float32,
    )
    indices = np.array([[0, 2, 1], [2, 3, 1]], dtype=np.uint32)
    normals = np.tile(np.array([0.0, 0.0, -1.0], dtype=np.float32), (4, 1))
    tangents = np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float32), (4, 1))
    handedness = np.ones((4,), dtype=np.float32)
    texcoords = np.array(
        [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
        dtype=np.float32,
    )

    geometry = scene.create_geometry(f2.StaticMeshGeometry)
    geometry.set_mesh_data(
        positions=positions,
        # Keep each triangle in its own BLAS geometry so the sample also demonstrates that
        # structural geometryIndex contributes to Falcor's geometry-instance ID.
        sub_mesh_indices=[indices[0:1], indices[1:2]],
        normals=normals,
        tangents=tangents,
        handedness=handedness,
        texcoords=texcoords,
        name=name,
    )

    entity = scene.create_entity()
    instance = entity.create_component(f2.GeometryInstance)
    instance.geometry = geometry
    instance.materials = [material, material]
    return entity, instance


def create_sample_scene(device: spy.Device, width: int, height: int) -> SampleScene:
    scene = f2.Scene.create(device)
    material = scene.create_material("StandardMaterial")

    front_entity, front_instance = add_quad(
        scene,
        material,
        name="front_occluder",
        z=0.0,
        size=0.8,
    )
    rear_entity, rear_instance = add_quad(
        scene,
        material,
        name="selected_rear_quad",
        z=0.5,
        size=1.8,
    )

    camera_entity = scene.create_entity()
    camera = camera_entity.create_component(f2.Camera)
    camera.width = width
    camera.height = height
    camera.fov_y = 45.0

    transform = f2.Transform()
    transform.translation = spy.float3(0.0, 0.0, -2.0)
    transform.rotation = spy.math.quat_from_look_at(
        spy.float3(0.0, 0.0, 1.0),
        spy.float3(0.0, 1.0, 0.0),
    )
    camera_entity.transform = transform
    scene.update()

    return SampleScene(
        scene=scene,
        camera=camera,
        front_entity=front_entity,
        front_instance=front_instance,
        rear_entity=rear_entity,
        rear_instance=rear_instance,
    )


def configure_pipeline(service: PipelineService, pipeline_api: f2.RayTracingPipelineAPI) -> None:
    # Both assignments are required. Selecting the API alone does not switch Vulkan/D3D12 away
    # from their default inline path.
    service.ray_tracing_pipeline_api = pipeline_api
    service.use_raytracing_pipeline = True


def colorize_geometry_ids(ids: np.ndarray, front_id: int, rear_id: int) -> np.ndarray:
    rgb = np.empty((*ids.shape, 3), dtype=np.float32)
    rgb[:] = (0.035, 0.050, 0.080)
    rgb[ids == np.uint32(rear_id)] = (0.08, 0.30, 0.72)
    rgb[ids == np.uint32(rear_id + 1)] = (0.08, 0.55, 0.68)
    rgb[ids == np.uint32(front_id)] = (0.78, 0.16, 0.13)
    rgb[ids == np.uint32(front_id + 1)] = (0.92, 0.45, 0.10)
    return rgb


def write_rgb_png(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = np.ones((*rgb.shape[:2], 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    bitmap = spy.Bitmap(
        data=np.ascontiguousarray(rgba),
        pixel_format=spy.Bitmap.PixelFormat.rgba,
        srgb_gamma=False,
    )
    bitmap = bitmap.convert(component_type=spy.Bitmap.ComponentType.uint8, srgb_gamma=True)
    bitmap.write(path)


def run_sample(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    pipeline_name = args.pipeline_api
    pipeline_api = PIPELINE_APIS[pipeline_name]
    device = create_device(DEVICE_TYPES[args.device])

    try:
        if not device.has_feature(spy.Feature.acceleration_structure):
            raise RuntimeError(f"{device.info.type.name} does not support acceleration structures")
        if not device.has_feature(spy.Feature.ray_tracing):
            raise RuntimeError(f"{device.info.type.name} does not support ray-tracing pipelines")

        sample = create_sample_scene(device, args.width, args.height)
        front_id = int(sample.front_instance.geometry_instance_id)
        rear_id = int(sample.rear_instance.geometry_instance_id)
        front_ids = [
            front_id + index for index in range(sample.front_instance.geometry_instance_count)
        ]
        rear_ids = [
            rear_id + index for index in range(sample.rear_instance.geometry_instance_count)
        ]

        picker = ui.ScenePicker(device)
        configure_pipeline(picker, pipeline_api)

        command_encoder = device.create_command_encoder()
        picker.render(command_encoder, sample.scene, sample.camera)
        device.submit_command_buffer(command_encoder.finish())
        device.wait()

        geometry_id_texture = picker.geometry_instance_id_texture
        if geometry_id_texture is None:
            raise RuntimeError("ScenePicker did not produce a geometry-ID texture")
        ids = np.asarray(geometry_id_texture.to_numpy(), dtype=np.uint32).copy()
        base_rgb = colorize_geometry_ids(ids, front_id, rear_id)

        center_id = int(picker.pick(spy.uint2(args.width // 2, args.height // 2)))
        if center_id not in front_ids:
            raise RuntimeError(f"Center pick returned {center_id}; expected one of {front_ids}")

        options = ui.SelectionOverlay.Options()
        options.show_occluded = True
        options.selection_color = spy.float3(0.20, 1.00, 0.42)
        options.fill_opacity = 0.30
        overlay = ui.SelectionOverlay(device, options)
        configure_pipeline(overlay, pipeline_api)

        # Direct IDs disable the optional AABB shortcut. Rays therefore encounter the front
        # non-selected candidate before accepting the selected rear candidate behind it.
        overlay.set_selected_geometry_instance_ids(
            [f2.GeometryInstanceID(geometry_id) for geometry_id in rear_ids]
        )

        base_rgba = np.ones((*base_rgb.shape[:2], 4), dtype=np.float32)
        base_rgba[..., :3] = base_rgb
        output_texture = device.create_texture(
            type=spy.TextureType.texture_2d,
            format=spy.Format.rgba32_float,
            width=args.width,
            height=args.height,
            mip_count=1,
            usage=spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access,
            data=np.ascontiguousarray(base_rgba),
            label="structural_scene_tools_output",
        )

        command_encoder = device.create_command_encoder()
        overlay.draw_overlay(
            command_encoder,
            output_texture,
            geometry_id_texture,
            sample.scene,
            sample.camera,
        )
        device.submit_command_buffer(command_encoder.finish())
        device.wait()

        selected_hit_texture = overlay.selected_hit_texture
        if selected_hit_texture is None:
            raise RuntimeError("SelectionProbe did not produce a selected-hit texture")
        selected_mask = np.asarray(selected_hit_texture.to_numpy(), dtype=np.uint32).copy()
        overlay_rgb = np.asarray(output_texture.to_numpy(), dtype=np.float32)[..., :3].copy()
        occluded_hit_count = int(np.count_nonzero(np.isin(ids, front_ids) & (selected_mask != 0)))
        if occluded_hit_count == 0:
            raise RuntimeError(
                "SelectionProbe did not find the selected rear geometry behind the front occluder"
            )

        picker_path = output_dir / f"scene-picker-{pipeline_name}.png"
        probe_path = output_dir / f"selection-probe-{pipeline_name}.png"
        overlay_path = output_dir / f"selection-overlay-{pipeline_name}.png"

        write_rgb_png(picker_path, base_rgb)
        write_rgb_png(
            probe_path,
            np.where(selected_mask[..., None] != 0, (0.20, 1.00, 0.42), (0.02, 0.03, 0.05)),
        )
        write_rgb_png(overlay_path, overlay_rgb)

        unique_ids = sorted(int(value) for value in np.unique(ids))
        print(f"Backend: {device.info.type.name}")
        print(f"Pipeline API: {pipeline_name}")
        print(f"Front geometry IDs: {front_ids}")
        print(f"Rear geometry IDs: {rear_ids}")
        print(f"Center pick: {center_id} (front geometry range)")
        print(f"Geometry-ID values: {unique_ids}")
        print(f"Selected/occluded pixels: {int(np.count_nonzero(selected_mask))}")
        print(f"Selected pixels hidden behind the front quad: {occluded_hit_count}")
        print(f"Wrote {picker_path}")
        print(f"Wrote {probe_path}")
        print(f"Wrote {overlay_path}")
    finally:
        device.close()


if __name__ == "__main__":
    run_sample(parse_args())
