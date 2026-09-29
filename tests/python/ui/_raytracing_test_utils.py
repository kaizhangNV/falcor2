# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Self-contained scene helpers for UI ray-tracing parity tests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import slangpy as spy

import falcor2 as f2
import falcor2.testing.helpers as helpers
import falcor2.ui as ui


@dataclass
class LayeredQuadScene:
    scene: f2.Scene
    camera: f2.Camera
    front_entity: f2.Entity
    front_instance: f2.GeometryInstance
    rear_entity: f2.Entity
    rear_instance: f2.GeometryInstance


def _add_quad(
    scene: f2.Scene,
    material: f2.Material,
    *,
    name: str,
    z: float,
    size: float,
) -> tuple[f2.Entity, f2.GeometryInstance]:
    """Add a camera-facing XY quad with one independently addressable RT instance."""
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
    normals = np.tile(np.array([0.0, 0.0, -1.0], dtype=np.float32), (4, 1))
    tangents = np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float32), (4, 1))
    handedness = np.ones((4,), dtype=np.float32)
    texcoords = np.array(
        [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
        dtype=np.float32,
    )
    indices = np.array([[0, 2, 1], [2, 3, 1]], dtype=np.uint32)

    geometry = scene.create_geometry(f2.StaticMeshGeometry)
    geometry.set_mesh_data(
        positions=positions,
        # Keep the two triangles in separate BLAS geometries. Their scene IDs
        # differ by GeometryIndex, which catches CUDA/OptiX implementations that
        # accidentally report every hit as geometry zero.
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


def create_layered_quad_scene(
    device: spy.Device,
    *,
    width: int = 32,
    height: int = 24,
) -> LayeredQuadScene:
    """Create two overlapping quads plus background pixels for hit/miss coverage.

    The smaller front quad occludes the center of the larger rear quad. Selecting
    the rear quad therefore exercises SelectionOverlay's any-hit ignore path for
    the front candidate before accepting the selected candidate behind it.
    """
    scene = f2.Scene.create(device)
    material = scene.create_material("StandardMaterial")

    front_entity, front_instance = _add_quad(
        scene,
        material,
        name="front_quad",
        z=0.0,
        size=0.8,
    )
    rear_entity, rear_instance = _add_quad(
        scene,
        material,
        name="rear_quad",
        z=0.5,
        size=1.8,
    )

    camera = helpers.create_test_camera(
        scene,
        width=width,
        height=height,
        fov_y=45.0,
        position=spy.float3(0.0, 0.0, -2.0),
        rotation=spy.math.quat_from_look_at(
            spy.float3(0.0, 0.0, 1.0),
            spy.float3(0.0, 1.0, 0.0),
        ),
    )
    scene.update()

    return LayeredQuadScene(
        scene=scene,
        camera=camera,
        front_entity=front_entity,
        front_instance=front_instance,
        rear_entity=rear_entity,
        rear_instance=rear_instance,
    )


def render_scene_picker_ids(
    device: spy.Device,
    test_scene: LayeredQuadScene,
    *,
    use_raytracing_pipeline: bool,
    pipeline_api: f2.RayTracingPipelineAPI | None = None,
) -> tuple[ui.ScenePicker, np.ndarray]:
    """Render and read back the complete ScenePicker ID map for one API mode."""
    picker = ui.ScenePicker(device)
    if pipeline_api is not None:
        picker.ray_tracing_pipeline_api = pipeline_api
    picker.use_raytracing_pipeline = use_raytracing_pipeline

    command_encoder = device.create_command_encoder()
    picker.render(command_encoder, test_scene.scene, test_scene.camera)
    device.submit_command_buffer(command_encoder.finish())

    texture = picker.geometry_instance_id_texture
    assert texture is not None
    return picker, np.asarray(texture.to_numpy(), dtype=np.uint32).copy()
