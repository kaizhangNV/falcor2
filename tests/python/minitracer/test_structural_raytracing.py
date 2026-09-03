# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Focused parity test for MiniTracer's structural ray tracing pipeline."""

import numpy as np
import pytest

import falcor2 as f2
import falcor2.minitracer.tools as mt
import falcor2.testing.helpers as helpers
import slangpy as spy


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_structural_pipeline_matches_legacy(device_type: spy.DeviceType):
    device = mt.create_device(device_type)
    if not device.has_feature(spy.Feature.acceleration_structure):
        pytest.skip("Acceleration structures are not supported on this device")
    if not device.has_feature(spy.Feature.ray_tracing):
        pytest.skip("Ray tracing pipelines are not supported on this device")

    scene = mt.create_scene(device)
    emissive = scene.create_material("emissive")
    emissive.albedo = scene.black_texture
    emissive.emission = scene.create_texture(1, 1, spy.float3(2.0, 1.0, 0.5))
    emissive.double_sided = True

    box = scene.create_box(spy.float3(1.0, 1.0, 1.0))
    box.material = emissive

    # Put a fully transparent surface in front of the light so parity also covers any-hit
    # rejection rather than only closest-hit and miss materialization.
    transparent = scene.create_material("transparent")
    transparent.albedo = scene.create_texture(1, 1, spy.float4(1.0, 1.0, 1.0, 0.0))
    transparent.alpha_mode = f2.AlphaMode.blend
    occluder = scene.create_box(spy.float3(1.4, 1.4, 0.1))
    occluder.transform.pos = spy.float3(0.0, 0.0, 1.0)
    occluder.material = transparent

    camera = scene.create_camera(32, 32, 45)
    camera.transform.pos = spy.float3(0.0, 0.0, 3.0)

    renderer = mt.create_renderer(device)
    renderer.enable_nee = False
    renderer.enable_mis = False
    renderer.enable_env_map = False
    renderer.enable_emissive_triangles = True
    renderer.max_depth = 1
    renderer.tone_map = False
    renderer.use_raytracing_pipeline = True

    renderer.ray_tracing_pipeline_api = "legacy"
    legacy = renderer.render(scene, camera, spp=1).to_numpy()

    renderer.ray_tracing_pipeline_api = "structural"
    structural = renderer.render(scene, camera, spp=1).to_numpy()

    assert np.isfinite(structural).all()
    assert np.max(legacy[..., :3]) > 0.0
    mse = np.mean(np.square(structural.astype(np.float64) - legacy.astype(np.float64)))
    assert mse <= 0.001
