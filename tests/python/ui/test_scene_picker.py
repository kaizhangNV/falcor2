# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

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


INVALID_GEOMETRY_INSTANCE_ID = np.uint32(0xFFFFFFFF)


STRUCTURAL_SETUP_PADDING_SOURCE = r"""
import slang.raytracing;

struct AdapterTestPayload
{
    uint value;
}

struct AdapterTestTraceContext : rt::ITraceContext
{
    typealias Payload = AdapterTestPayload;
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct AdapterTestHitContext : rt::IHitContext
{
    typealias TraceContext = AdapterTestTraceContext;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct AdapterTestClosestHit : rt::IClosestHitShader<AdapterTestHitContext>
{
    void invoke(rt::ClosestHitInput<AdapterTestHitContext> input)
    {
        input.payload.value = 1;
    }
}

struct AdapterTestHitGroup : rt::IHitGroup
{
    typealias Slot = rt::HitGroupSlot<0>;
    typealias Context = AdapterTestHitContext;
    typealias ClosestHit = AdapterTestClosestHit;
    typealias AnyHit = rt::NoAnyHit<AdapterTestHitContext>;
    typealias Intersection = rt::NoIntersection<AdapterTestHitContext>;
}

struct AdapterTestMissContext : rt::IMissGroupContext
{
    typealias TraceContext = AdapterTestTraceContext;
    typealias Record = void;
}

struct AdapterTestMiss : rt::IMissShader<AdapterTestMissContext>
{
    void invoke(rt::MissInput<AdapterTestMissContext> input)
    {
        input.payload.value = 0;
    }
}

struct AdapterTestMissGroup : rt::IMissGroup
{
    typealias Slot = rt::MissSlot<0>;
    typealias Context = AdapterTestMissContext;
    typealias Miss = AdapterTestMiss;
}

struct AdapterTestLayout : rt::ITraceProgramLayout
{
    typealias TraceContext = AdapterTestTraceContext;
    typealias HitGroups = rt::HitGroupList<AdapterTestTraceContext, AdapterTestHitGroup>;
    typealias MissGroups = rt::MissGroupList<AdapterTestTraceContext, AdapterTestMissGroup>;
    typealias CallableGroups = rt::NoCallableGroups<AdapterTestTraceContext>;
}

rt::TraceProgramDescriptor<AdapterTestLayout> adapter_test_program;

// Reserve the setup adapter's preferred padding name as an ordinary stage.
[shader("raygeneration")]
public void __dummy_hit_group() { }
"""


@pytest.fixture
def device(device_type: spy.DeviceType) -> spy.Device:
    return helpers.get_device(device_type, enable_experimental_features=True)


@pytest.fixture
def test_scene(device: spy.Device) -> LayeredQuadScene:
    return create_layered_quad_scene(device)


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_find_entity_by_geometry_instance_id(test_scene: LayeredQuadScene) -> None:
    scene = test_scene.scene

    result = ui.ScenePicker.find_entity_by_geometry_instance_id(
        scene, test_scene.front_instance.geometry_instance_id
    )
    assert result is test_scene.front_entity

    invalid_result = ui.ScenePicker.find_entity_by_geometry_instance_id(
        scene, f2.GeometryInstanceID.invalid
    )
    assert invalid_result is None

    out_of_range_result = ui.ScenePicker.find_entity_by_geometry_instance_id(
        scene, f2.GeometryInstanceID(999999)
    )
    assert out_of_range_result is None


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_render(device: spy.Device, test_scene: LayeredQuadScene) -> None:
    picker = ui.ScenePicker(device)

    assert picker.geometry_instance_id_texture is None
    assert picker.pick(spy.uint2(0, 0)) == f2.GeometryInstanceID.invalid
    assert picker.pick_entity(test_scene.scene, spy.uint2(0, 0)) is None

    command_encoder = device.create_command_encoder()
    picker.render(command_encoder, test_scene.scene, test_scene.camera)
    device.submit_command_buffer(command_encoder.finish())

    assert picker.geometry_instance_id_texture is not None
    assert picker.geometry_instance_id_texture.width == test_scene.camera.width
    assert picker.geometry_instance_id_texture.height == test_scene.camera.height


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_structural_setup_pads_scene_policy_without_name_collision(
    device: spy.Device,
    test_scene: LayeredQuadScene,
) -> None:
    module = device.load_module_from_source(
        "test_structural_setup_padding_collision",
        STRUCTURAL_SETUP_PADDING_SOURCE,
    )
    setup = f2.SceneRayTracingSetup.create_structural(
        test_scene.scene,
        module,
        "AdapterTestLayout",
    )

    # Scene's geometry-major policy has two geometry types and three ray types.
    # The structural layout supplies only triangle/ray-type zero, so the adapter
    # must preserve that slot and pad the other five with one empty hit group.
    assert len(setup.sbt_hit_group_names) == 6
    real_hit_group_name = setup.sbt_hit_group_names[0]
    dummy_hit_group_name = setup.sbt_hit_group_names[1]
    assert real_hit_group_name
    assert real_hit_group_name != dummy_hit_group_name
    assert setup.sbt_hit_group_names[1:] == [dummy_hit_group_name] * 5

    # The preferred dummy name is already a ray-generation entry point above.
    # Verify padding picked a collision-free name and emitted exactly one matching
    # empty descriptor for all padded slots.
    assert dummy_hit_group_name.startswith("__dummy_hit_group_")
    matching_dummy_groups = [
        hit_group
        for hit_group in setup.hit_groups
        if hit_group.hit_group_name == dummy_hit_group_name
    ]
    assert len(matching_dummy_groups) == 1
    assert matching_dummy_groups[0].closest_hit_entry_point == ""
    assert matching_dummy_groups[0].any_hit_entry_point == ""
    assert matching_dummy_groups[0].intersection_entry_point == ""

    assert len(setup.sbt_miss_entry_points) == 3
    assert setup.sbt_miss_entry_points[0]
    assert setup.sbt_miss_entry_points[1:] == ["", ""]


@pytest.mark.parametrize("device_type", helpers.DEFAULT_DEVICE_TYPES)
def test_structural_pipeline_matches_legacy_complete_id_map(
    device_type: spy.DeviceType,
    device: spy.Device,
    test_scene: LayeredQuadScene,
) -> None:
    if not device.has_feature(spy.Feature.acceleration_structure):
        pytest.skip("Acceleration structures are not supported on this device")
    if not device.has_feature(spy.Feature.ray_tracing):
        pytest.skip("Ray tracing pipelines are not supported on this device")

    _, legacy_ids = render_scene_picker_ids(
        device,
        test_scene,
        use_raytracing_pipeline=True,
        pipeline_api=f2.RayTracingPipelineAPI.legacy,
    )
    _, structural_ids = render_scene_picker_ids(
        device,
        test_scene,
        use_raytracing_pipeline=True,
        pipeline_api=f2.RayTracingPipelineAPI.structural,
    )

    np.testing.assert_array_equal(structural_ids, legacy_ids)

    # The full image covers both independently addressable quads and misses, so
    # equality exercises closest-hit payload materialization as well as miss.
    unique_ids = set(np.unique(legacy_ids).tolist())
    assert int(test_scene.front_instance.geometry_instance_id) in unique_ids
    assert int(test_scene.front_instance.geometry_instance_id) + 1 in unique_ids
    assert int(test_scene.rear_instance.geometry_instance_id) in unique_ids
    assert int(test_scene.rear_instance.geometry_instance_id) + 1 in unique_ids
    assert int(INVALID_GEOMETRY_INSTANCE_ID) in unique_ids

    # CUDA has no inline RayQuery path in this shader. Other RT backends should
    # also agree with the unchanged inline implementation.
    if device_type != spy.DeviceType.cuda:
        _, inline_ids = render_scene_picker_ids(
            device,
            test_scene,
            use_raytracing_pipeline=False,
        )
        np.testing.assert_array_equal(structural_ids, inline_ids)


if __name__ == "__main__":
    pytest.main([__file__, "-vs"])
