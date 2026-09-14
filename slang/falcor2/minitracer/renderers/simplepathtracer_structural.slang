// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import slang.raytracing;
import falcor2.minitracer.scene;
import falcor2.utils;

// Structural ray-tracing counterpart to the stages in simplepathtracer_legacy.slang. The shared
// renderer remains in simplepathtracer.slang so both pipeline variants use the same rendering code.
//
struct MiniTracerTraceContext : rt::ITraceContext
{
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct MiniTracerHitContext : rt::IHitContext
{
    typealias TraceContext = MiniTracerTraceContext;
    typealias Payload = HitInfo;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct MiniTracerClosestHit : rt::IClosestHitShader
{
    typealias Context = MiniTracerHitContext;

    void invoke(rt::ClosestHitInput<Context> input)
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

struct MiniTracerAnyHit : rt::IAnyHitShader
{
    typealias Context = MiniTracerHitContext;

    void invoke(rt::AnyHitInput<Context> input)
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
    typealias Context = MiniTracerHitContext;
    typealias ClosestHit = MiniTracerClosestHit;
    typealias AnyHit = MiniTracerAnyHit;
    typealias Intersection = rt::NoIntersection<Context>;
}

struct MiniTracerMissContext : rt::IPayloadContext
{
    typealias TraceContext = MiniTracerTraceContext;
    typealias Payload = HitInfo;
    typealias Record = void;
}

struct MiniTracerMiss : rt::IMissShader
{
    typealias Context = MiniTracerMissContext;
    void invoke(rt::MissInput<Context> input) { }
}

struct MiniTracerProgramSchema : rt::ITraceProgramSchema
{
    typealias TraceContext = MiniTracerTraceContext;
    typealias HitGroups = rt::HitGroupList<MiniTracerHitGroup>;
    typealias MissShaders = rt::MissShaderList<MiniTracerMiss>;
    typealias CallableShaders = rt::NoCallableShaders;
}

rt::TraceProgramDescriptor<MiniTracerProgramSchema> mini_tracer_program;

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
        rt::RayTracer<MiniTracerProgramSchema> tracer;
        tracer.trace(desc, g_scene.tlas, mini_tracer_program, hit);
        return hit;
    }

    bool is_occluded(Ray ray, float alpha_threshold)
    {
        HitInfo hit = intersect(ray, alpha_threshold);
        return hit.valid;
    }
};
