// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import slang.raytracing;
__exported import falcor2.rendernodes.reference_pathtracer;
import falcor2.render;
import falcor2.utils;

// This file intentionally uses an implicit module. The current structural ray-tracing prototype
// diagnoses synthesized stage methods for unsupported targets when placed in an explicit module.

struct ScatterTraceContext : rt::ITraceContext
{
    typealias Payload = PathPayload;
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct ScatterHitContext : rt::IHitContext
{
    typealias TraceContext = ScatterTraceContext;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct ScatterClosestHit : rt::IClosestHitShader<ScatterHitContext>
{
    void invoke(rt::ClosestHitInput<ScatterHitContext> input)
    {
        __target_switch
        {
        case hlsl:
        case glsl:
        case spirv:
        case cuda:
            // Pack the same triangle HitInfo as make_triangle_hit_info() without calling an
            // imported helper from a synthesized stage.
            HitInfo hit = {};
            hit.geometry_type = GeometryType::triangle;
            hit.geometry_instance_id = GeometryInstanceID(input.instanceID + input.geometryIndex);
            hit.primitive_index = input.primitiveIndex;
            TriangleHitData hit_data = { input.triangle.barycentricCoord };
            hit._hit_data = reinterpret<HitData>(hit_data);
            InlineVisibilityQuery visibility_query;
            handle_scatter_hit(visibility_query, input.payload, hit);
        default:
            // Falcor has no Metal pipeline runtime yet. Keep the layout materializable for
            // compile-only checks without claiming a functional Metal ReferencePathTracer.
            break;
        }
    }
}

struct ScatterHitGroup : rt::IHitGroup
{
    typealias Slot = rt::HitGroupSlot<0>;
    typealias Context = ScatterHitContext;
    typealias ClosestHit = ScatterClosestHit;
    typealias AnyHit = rt::NoAnyHit<ScatterHitContext>;
    typealias Intersection = rt::NoIntersection<ScatterHitContext>;
}

struct ScatterMissContext : rt::IMissGroupContext
{
    typealias TraceContext = ScatterTraceContext;
    typealias Record = void;
}

struct ScatterMiss : rt::IMissShader<ScatterMissContext>
{
    void invoke(rt::MissInput<ScatterMissContext> input)
    {
        __target_switch
        {
        case hlsl:
        case glsl:
        case spirv:
        case cuda:
            handle_scatter_miss(input.payload);
        default:
            // Compile-only Metal fallback; see ScatterClosestHit above.
            break;
        }
    }
}

struct ScatterMissGroup : rt::IMissGroup
{
    typealias Slot = rt::MissSlot<0>;
    typealias Context = ScatterMissContext;
    typealias Miss = ScatterMiss;
}

struct ScatterProgramLayout : rt::ITraceProgramLayout
{
    typealias TraceContext = ScatterTraceContext;
    typealias HitGroups = rt::HitGroupList<ScatterTraceContext, ScatterHitGroup>;
    typealias MissGroups = rt::MissGroupList<ScatterTraceContext, ScatterMissGroup>;
    typealias CallableGroups = rt::NoCallableGroups<ScatterTraceContext>;
}

rt::TraceProgramDescriptor<ScatterProgramLayout> scatter_program;

struct StructuralScatterTracer : IScatterTracer
{
    void trace(no_diff Ray ray, inout PathPayload payload)
    {
        rt::RayTraversalDesc desc = {};
        desc.ray.origin = ray.origin;
        desc.ray.direction = ray.dir;
        desc.ray.tMin = ray.t_min;
        desc.ray.tMax = ray.t_max;
        desc.rayFlags = RAY_FLAG_NONE;
        desc.instanceMask = 0xff;
        desc.sbtOffset = SCATTER_RAY_INDEX;
        desc.sbtStride = 0;
        desc.missIndex = SCATTER_RAY_INDEX;

        rt::RayTracer<ScatterProgramLayout> tracer;
        tracer.trace(desc, g_scene.tlas, scatter_program, payload);
    }
};

/// Structural Phase 4 always uses the shared non-SER scheduler.
struct StructuralSimpleScheduler : IPathScheduler
{
    float3 trace_path(no_diff Ray ray, no_diff uint path_id, no_diff UniformSampleGenerator sg)
    {
        SimpleScheduler<StructuralScatterTracer> scheduler;
        return scheduler.trace_path(ray, path_id, sg);
    }
};
