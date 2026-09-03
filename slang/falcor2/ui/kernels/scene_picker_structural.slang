// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import slang.raytracing;
import falcor2.render;
import falcor2.utils;

// This file intentionally uses an implicit module. The current structural ray-tracing prototype
// diagnoses synthesized stage methods for unsupported targets when placed in an explicit module.

// TODO: This is a workaround for CUDA not passing ray-gen entry point parameters correctly.
// https://github.com/shader-slang/slang/issues/10188
struct RenderIdsParams
{
    Camera camera;
    RWTexture2D<uint> output;
};
ParameterBlock<RenderIdsParams> g_render_ids_params;

struct ScenePickerTraceContext : rt::ITraceContext
{
    typealias Payload = HitInfo;
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct ScenePickerHitContext : rt::IHitContext
{
    typealias TraceContext = ScenePickerTraceContext;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct ScenePickerClosestHit : rt::IClosestHitShader<ScenePickerHitContext>
{
    void invoke(rt::ClosestHitInput<ScenePickerHitContext> input)
    {
        __target_switch
        {
        case hlsl:
        case glsl:
        case spirv:
        case cuda:
            input.payload = make_triangle_hit_info(
                GeometryInstanceID(input.instanceID + input.geometryIndex),
                input.primitiveIndex,
                input.triangle.barycentricCoord
            );
        default:
            // Falcor has no Metal pipeline runtime yet. Keep the stage materializable there while
            // the imported HitInfo packing helper remains unavailable for the Metal capability.
            input.payload.geometry_type = GeometryType::triangle;
            input.payload.geometry_instance_id = GeometryInstanceID(input.instanceID + input.geometryIndex);
            input.payload.primitive_index = input.primitiveIndex;
        }
    }
}

struct ScenePickerHitGroup : rt::IHitGroup
{
    typealias Slot = rt::HitGroupSlot<0>;
    typealias Context = ScenePickerHitContext;
    typealias ClosestHit = ScenePickerClosestHit;
    typealias AnyHit = rt::NoAnyHit<ScenePickerHitContext>;
    typealias Intersection = rt::NoIntersection<ScenePickerHitContext>;
}

struct ScenePickerMissContext : rt::IMissGroupContext
{
    typealias TraceContext = ScenePickerTraceContext;
    typealias Record = void;
}

struct ScenePickerMiss : rt::IMissShader<ScenePickerMissContext>
{
    void invoke(rt::MissInput<ScenePickerMissContext> input) { }
}

struct ScenePickerMissGroup : rt::IMissGroup
{
    typealias Slot = rt::MissSlot<0>;
    typealias Context = ScenePickerMissContext;
    typealias Miss = ScenePickerMiss;
}

struct ScenePickerProgramLayout : rt::ITraceProgramLayout
{
    typealias TraceContext = ScenePickerTraceContext;
    typealias HitGroups = rt::HitGroupList<ScenePickerTraceContext, ScenePickerHitGroup>;
    typealias MissGroups = rt::MissGroupList<ScenePickerTraceContext, ScenePickerMissGroup>;
    typealias CallableGroups = rt::NoCallableGroups<ScenePickerTraceContext>;
}

rt::TraceProgramDescriptor<ScenePickerProgramLayout> scene_picker_program;

struct StructuralScenePickerIntersector : ISceneIntersector
{
    HitInfo intersect(Ray ray)
    {
        rt::RayTraversalDesc desc = {};
        desc.ray.origin = ray.origin;
        desc.ray.direction = ray.dir;
        desc.ray.tMin = ray.t_min;
        desc.ray.tMax = ray.t_max;
        desc.rayFlags = RAY_FLAG_NONE;
        desc.instanceMask = 0xff;
        desc.sbtOffset = 0;
        desc.sbtStride = 0;
        desc.missIndex = 0;

        HitInfo hit = {};
        rt::RayTracer<ScenePickerProgramLayout> tracer;
        tracer.trace(desc, g_scene.tlas, scene_picker_program, hit);
        return hit;
    }

    bool is_occluded(Ray ray) { return intersect(ray).valid; }
}

[shader("raygeneration")]
public void render_ids_ray_gen()
{
    uint2 dims;
    g_render_ids_params.output.GetDimensions(dims.x, dims.y);

    uint2 pixel = DispatchRaysIndex().xy;
    if (any(pixel >= dims))
        return;

    float2 uv = (float2(pixel) + 0.5) / float2(dims);
    uv.y = 1 - uv.y;

    Ray ray = g_render_ids_params.camera.get_ray(uv);
    StructuralScenePickerIntersector intersector;
    HitInfo hit = intersector.intersect(ray);
    g_render_ids_params.output[pixel] = hit.valid ? uint(hit.geometry_instance_id) : 0xffffffff;
}
