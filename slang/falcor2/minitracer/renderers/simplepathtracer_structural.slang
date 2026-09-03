// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import slang.raytracing;
import falcor2.minitracer.scene;
import falcor2.utils;

// Structural ray-tracing counterpart to the stages in simplepathtracer_legacy.slang. The shared
// renderer remains in simplepathtracer.slang so both pipeline variants use the same rendering code.
//
// Keep this in legacy/implicit-module mode with unannotated structural declarations for now. At the
// compiler revision used by this port, changing it to an explicit/modern module diagnoses the stage
// invoke() methods as missing Metal support even when the declarations stay unannotated/internal and
// the target is Vulkan/CUDA (E36119). Legacy-module visibility still makes these declarations
// available to reflection and to modules composed through SlangPy.

struct MiniTracerTraceContext : rt::ITraceContext
{
    typealias Payload = HitInfo;
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct MiniTracerHitContext : rt::IHitContext
{
    typealias TraceContext = MiniTracerTraceContext;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct MiniTracerClosestHit : rt::IClosestHitShader<MiniTracerHitContext>
{
    void invoke(rt::ClosestHitInput<MiniTracerHitContext> input)
    {
        input.payload.valid = true;
        input.payload.bary = input.triangle.barycentricCoord;
        input.payload.t = input.distance;
#ifndef __TARGET_CUDA__
        input.payload.geometry_instance_id = GeometryInstanceID(input.instanceID + input.geometryIndex);
#else
        input.payload.geometry_instance_id = GeometryInstanceID(input.instanceID);
#endif
        input.payload.primitive_index = input.primitiveIndex;
    }
}

struct MiniTracerAnyHit : rt::IAnyHitShader<MiniTracerHitContext>
{
    void invoke(rt::AnyHitInput<MiniTracerHitContext> input)
    {
        HitInfo temp_hit = {};
        temp_hit.valid = true;
        temp_hit.bary = input.triangle.barycentricCoord;
        temp_hit.t = input.distance;
#ifndef __TARGET_CUDA__
        temp_hit.geometry_instance_id = GeometryInstanceID(input.instanceID + input.geometryIndex);
#else
        temp_hit.geometry_instance_id = GeometryInstanceID(input.instanceID);
#endif
        temp_hit.primitive_index = input.primitiveIndex;

        // Match the legacy pipeline, whose any-hit stage uses a fixed alpha threshold.
        if (!g_scene.is_valid_hit(temp_hit, input.worldSpaceDirection, 1.0))
            input.ignoreHit();
    }
}

struct MiniTracerHitGroup : rt::IHitGroup
{
    typealias Slot = rt::HitGroupSlot<0>;
    typealias Context = MiniTracerHitContext;
    typealias ClosestHit = MiniTracerClosestHit;
    typealias AnyHit = MiniTracerAnyHit;
    typealias Intersection = rt::NoIntersection<MiniTracerHitContext>;
}

struct MiniTracerMissContext : rt::IMissGroupContext
{
    typealias TraceContext = MiniTracerTraceContext;
    typealias Record = void;
}

struct MiniTracerMiss : rt::IMissShader<MiniTracerMissContext>
{
    void invoke(rt::MissInput<MiniTracerMissContext> input) { }
}

struct MiniTracerMissGroup : rt::IMissGroup
{
    typealias Slot = rt::MissSlot<0>;
    typealias Context = MiniTracerMissContext;
    typealias Miss = MiniTracerMiss;
}

struct MiniTracerProgramLayout : rt::ITraceProgramLayout
{
    typealias TraceContext = MiniTracerTraceContext;
    typealias HitGroups = rt::HitGroupList<MiniTracerTraceContext, MiniTracerHitGroup>;
    typealias MissGroups = rt::MissGroupList<MiniTracerTraceContext, MiniTracerMissGroup>;
    typealias CallableGroups = rt::NoCallableGroups<MiniTracerTraceContext>;
}

rt::TraceProgramDescriptor<MiniTracerProgramLayout> mini_tracer_program;

struct StructuralRayTracingSceneIntersector : ISceneIntersector
{
    HitInfo intersect(Ray ray, float alpha_threshold)
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
        rt::RayTracer<MiniTracerProgramLayout> tracer;
        tracer.trace(desc, g_scene.tlas, mini_tracer_program, hit);
        return hit;
    }

    bool is_occluded(Ray ray, float alpha_threshold)
    {
        HitInfo hit = intersect(ray, alpha_threshold);
        return hit.valid;
    }
};
