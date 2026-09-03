// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import slang.raytracing;
import falcor2.render;
import falcor2.utils;

// This file intentionally uses an implicit module. The current structural ray-tracing prototype
// diagnoses synthesized stage methods for unsupported targets when placed in an explicit module.

bool is_selected(uint id, StructuredBuffer<uint> selection_bitmap, uint selection_bitmap_bit_count)
{
    return id < selection_bitmap_bit_count && (selection_bitmap[id / 32] & (1u << (id % 32))) != 0;
}

bool aabb_cull_ray(inout Ray ray, float3 aabb_min, float3 aabb_max, bool aabb_enabled)
{
    if (!aabb_enabled)
        return false;

    float3 center = (aabb_min + aabb_max) * 0.5;
    float3 extent = (aabb_max - aabb_min) * 0.5;
    const float MIN_EXTENT = 1e-5;
    extent = max(extent * 1.001, float3(MIN_EXTENT));
    aabb_min = center - extent;
    aabb_max = center + extent;

    float2 near_far;
    if (!intersect_ray_aabb(ray.origin, ray.dir, aabb_min, aabb_max, near_far))
        return true;
    ray.t_min = max(ray.t_min, near_far.x);
    ray.t_max = min(ray.t_max, near_far.y);
    return false;
}

// TODO: This is a workaround for CUDA not passing ray-gen entry point parameters correctly.
// https://github.com/shader-slang/slang/issues/10188
struct SelectionProbeParams
{
    Camera camera;
    StructuredBuffer<uint> selection_bitmap;
    uint selection_bitmap_bit_count;
    RWTexture2D<uint> selected_hit_texture;
    float3 aabb_min;
    float3 aabb_max;
    bool aabb_enabled;
};
ParameterBlock<SelectionProbeParams> g_selection_probe_params;

struct SelectionProbePayload
{
    uint hit;
}

struct SelectionProbeTraceContext : rt::ITraceContext
{
    typealias Payload = SelectionProbePayload;
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct SelectionProbeHitContext : rt::IHitContext
{
    typealias TraceContext = SelectionProbeTraceContext;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct SelectionProbeAnyHit : rt::IAnyHitShader<SelectionProbeHitContext>
{
    void invoke(rt::AnyHitInput<SelectionProbeHitContext> input)
    {
        uint id = input.instanceID + input.geometryIndex;
        if (is_selected(
                id,
                g_selection_probe_params.selection_bitmap,
                g_selection_probe_params.selection_bitmap_bit_count
            )) {
            input.payload.hit = 1;
            input.acceptHitAndEndSearch();
        } else {
            input.ignoreHit();
        }
    }
}

struct SelectionProbeHitGroup : rt::IHitGroup
{
    typealias Slot = rt::HitGroupSlot<0>;
    typealias Context = SelectionProbeHitContext;
    typealias ClosestHit = rt::NoClosestHit<SelectionProbeHitContext>;
    typealias AnyHit = SelectionProbeAnyHit;
    typealias Intersection = rt::NoIntersection<SelectionProbeHitContext>;
}

struct SelectionProbeMissContext : rt::IMissGroupContext
{
    typealias TraceContext = SelectionProbeTraceContext;
    typealias Record = void;
}

struct SelectionProbeMiss : rt::IMissShader<SelectionProbeMissContext>
{
    void invoke(rt::MissInput<SelectionProbeMissContext> input) { input.payload.hit = 0; }
}

struct SelectionProbeMissGroup : rt::IMissGroup
{
    typealias Slot = rt::MissSlot<0>;
    typealias Context = SelectionProbeMissContext;
    typealias Miss = SelectionProbeMiss;
}

struct SelectionProbeProgramLayout : rt::ITraceProgramLayout
{
    typealias TraceContext = SelectionProbeTraceContext;
    typealias HitGroups = rt::HitGroupList<SelectionProbeTraceContext, SelectionProbeHitGroup>;
    typealias MissGroups = rt::MissGroupList<SelectionProbeTraceContext, SelectionProbeMissGroup>;
    typealias CallableGroups = rt::NoCallableGroups<SelectionProbeTraceContext>;
}

rt::TraceProgramDescriptor<SelectionProbeProgramLayout> selection_probe_program;

[shader("raygeneration")]
public void selection_probe_ray_gen()
{
    uint2 dims;
    g_selection_probe_params.selected_hit_texture.GetDimensions(dims.x, dims.y);

    uint2 pixel = DispatchRaysIndex().xy;
    if (any(pixel >= dims))
        return;

    float2 uv = (float2(pixel) + 0.5) / float2(dims);
    uv.y = 1 - uv.y;

    Ray ray = g_selection_probe_params.camera.get_ray(uv);
    if (aabb_cull_ray(
            ray,
            g_selection_probe_params.aabb_min,
            g_selection_probe_params.aabb_max,
            g_selection_probe_params.aabb_enabled
        )) {
        g_selection_probe_params.selected_hit_texture[pixel] = 0u;
        return;
    }

    rt::RayTraversalDesc desc = {};
    desc.ray.origin = ray.origin;
    desc.ray.direction = ray.dir;
    desc.ray.tMin = ray.t_min;
    desc.ray.tMax = ray.t_max;
    desc.rayFlags = RAY_FLAG_FORCE_NON_OPAQUE;
    desc.instanceMask = 0xff;
    desc.sbtOffset = 0;
    desc.sbtStride = 0;
    desc.missIndex = 0;

    SelectionProbePayload payload = {};
    rt::RayTracer<SelectionProbeProgramLayout> tracer;
    tracer.trace(desc, g_scene.tlas, selection_probe_program, payload);
    g_selection_probe_params.selected_hit_texture[pixel] = payload.hit;
}
