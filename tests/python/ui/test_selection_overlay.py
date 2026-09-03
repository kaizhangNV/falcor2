# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Focused runtime parity tests for SelectionOverlay ray tracing."""

from __future__ import annotations

import numpy as np
import pytest
import slangpy as spy

import falcor2 as f2
import falcor2.testing.helpers as helpers
import falcor2.ui as ui

from ._raytracing_test_utils import (
    LayeredQuadScene,
    create_layered_quad_scene,
    render_scene_picker_ids,
)


@pytest.fixture
def device(device_type: spy.DeviceType) -> spy.Device:
    return helpers.get_device(device_type, enable_experimental_features=True)


@pytest.fixture
def test_scene(device: spy.Device) -> LayeredQuadScene:
    return create_layered_quad_scene(device)


def _render_selected_hit_mask(
    device: spy.Device,
    test_scene: LayeredQuadScene,
    geometry_instance_id_texture: spy.Texture,
    *,
    use_raytracing_pipeline: bool,
    pipeline_api: f2.RayTracingPipelineAPI | None = None,
) -> np.ndarray:
    options = ui.SelectionOverlay.Options()
    options.show_occluded = True
    overlay = ui.SelectionOverlay(device, options)
    if pipeline_api is not None:
        overlay.ray_tracing_pipeline_api = pipeline_api
    overlay.use_raytracing_pipeline = use_raytracing_pipeline

    # Setting IDs directly intentionally disables the host AABB shortcut. Every
    # pixel then reaches the trace implementation being compared.
    overlay.set_selected_geometry_instance_ids([test_scene.rear_instance.geometry_instance_id])

    output = device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=test_scene.camera.width,
        height=test_scene.camera.height,
        mip_count=1,
        usage=spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access,
        label="selection_overlay_test_output",
    )

    command_encoder = device.create_command_encoder()
    command_encoder.clear_texture_float(output, clear_value=spy.float4(0.0))
    overlay.draw_overlay(
        command_encoder,
        output,
        geometry_instance_id_texture,
        test_scene.scene,
        test_scene.camera,
    )
    device.submit_command_buffer(command_encoder.finish())

    selected_hit_texture = overlay.selected_hit_texture
    assert selected_hit_texture is not None
    return np.asarray(selected_hit_texture.to_numpy(), dtype=np.uint32).copy()


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_structural_any_hit_matches_legacy_complete_mask(
    device_type: spy.DeviceType,
    device: spy.Device,
    test_scene: LayeredQuadScene,
) -> None:
    if not device.has_feature(spy.Feature.acceleration_structure):
        pytest.skip("Acceleration structures are not supported on this device")
    if not device.has_feature(spy.Feature.ray_tracing):
        pytest.skip("Ray tracing pipelines are not supported on this device")

    # Keep the picker (and therefore its internal texture) alive while all
    # SelectionOverlay variants consume the same visible-ID input.
    picker, visible_ids = render_scene_picker_ids(
        device,
        test_scene,
        use_raytracing_pipeline=True,
        pipeline_api=f2.RayTracingPipelineAPI.legacy,
    )
    geometry_instance_id_texture = picker.geometry_instance_id_texture
    assert geometry_instance_id_texture is not None

    legacy_mask = _render_selected_hit_mask(
        device,
        test_scene,
        geometry_instance_id_texture,
        use_raytracing_pipeline=True,
        pipeline_api=f2.RayTracingPipelineAPI.legacy,
    )
    structural_mask = _render_selected_hit_mask(
        device,
        test_scene,
        geometry_instance_id_texture,
        use_raytracing_pipeline=True,
        pipeline_api=f2.RayTracingPipelineAPI.structural,
    )

    np.testing.assert_array_equal(structural_mask, legacy_mask)
    assert set(np.unique(legacy_mask).tolist()) == {0, 1}

    front_id = int(test_scene.front_instance.geometry_instance_id)
    rear_id = int(test_scene.rear_instance.geometry_instance_id)

    # At least one selected rear hit must lie behind the visible front quad.
    # Reaching it requires any-hit to ignore the non-selected front candidate,
    # continue traversal, and accept/end-search on the selected rear candidate.
    assert np.any((visible_ids == front_id) & (legacy_mask == 1))
    assert np.any((visible_ids == rear_id) & (legacy_mask == 1))
    assert np.any((visible_ids == np.uint32(0xFFFFFFFF)) & (legacy_mask == 0))

    # CUDA intentionally has no inline RayQuery version of this shader.
    if device_type != spy.DeviceType.cuda:
        inline_mask = _render_selected_hit_mask(
            device,
            test_scene,
            geometry_instance_id_texture,
            use_raytracing_pipeline=False,
        )
        np.testing.assert_array_equal(structural_mask, inline_mask)


if __name__ == "__main__":
    pytest.main([__file__, "-vs"])
