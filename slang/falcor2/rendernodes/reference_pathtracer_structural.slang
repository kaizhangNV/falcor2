// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import slang.raytracing;
__exported import falcor2.rendernodes.reference_pathtracer;
import falcor2.render;
import falcor2.utils;

struct ReferencePathTracerTraceContext : rt::ITraceContext
{
    typealias AccelerationStructure = rt::AccelerationStructure;
    typealias Motion = rt::NoMotion;
}

struct ScatterHitContext : rt::IHitContext
{
    typealias TraceContext = ReferencePathTracerTraceContext;
    typealias Payload = PathPayload;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

struct VisibilityHitContext : rt::IHitContext
{
    typealias TraceContext = ReferencePathTracerTraceContext;
    typealias Payload = VisibilityPayload;
    typealias Primitive = rt::TrianglePrimitive;
    typealias Record = void;
}

void handle_structural_scatter_hit(inout PathPayload payload, HitInfo hit);

struct ScatterClosestHit : rt::IClosestHitShader
{
    typealias Context = ScatterHitContext;

    void invoke(rt::ClosestHitInput<Context> input)
    {
        __target_switch
        {
        case hlsl:
        case glsl:
        case spirv:
        case cuda:
            HitInfo hit = {};
            hit.geometry_type = GeometryType::triangle;
            hit.geometry_instance_id = GeometryInstanceID(input.instanceID + input.geometryIndex);
            hit.primitive_index = input.primitiveIndex;
            TriangleHitData hit_data = { input.triangle.barycentricCoord };
            hit._hit_data = reinterpret<HitData>(hit_data);
            handle_structural_scatter_hit(input.payload, hit);
        default:
            break;
        }
    }
}

struct VisibilityAnyHit : rt::IAnyHitShader
{
    typealias Context = VisibilityHitContext;

    void invoke(rt::AnyHitInput<Context> input)
    {
        __target_switch
        {
        case hlsl:
        case glsl:
        case spirv:
        case cuda:
            Ray ray = Ray(input.worldSpaceOrigin, input.worldSpaceDirection, input.minDistance, input.distance);
            HitInfo hit = {};
            hit.geometry_type = GeometryType::triangle;
            hit.geometry_instance_id = GeometryInstanceID(input.instanceID + input.geometryIndex);
            hit.primitive_index = input.primitiveIndex;
            TriangleHitData hit_data = { input.triangle.barycentricCoord };
            hit._hit_data = reinterpret<HitData>(hit_data);
            if (OpacityEvaluator::is_valid_hit(ray, hit))
                input.acceptHitAndEndSearch();
            else
                input.ignoreHit();
        default:
            break;
        }
    }
}

struct ScatterHitGroup : rt::IHitGroup
{
    typealias Context = ScatterHitContext;
    typealias ClosestHit = ScatterClosestHit;
    typealias AnyHit = rt::NoAnyHit<Context>;
    typealias Intersection = rt::NoIntersection<Context>;
}

struct VisibilityHitGroup : rt::IHitGroup
{
    typealias Context = VisibilityHitContext;
    typealias ClosestHit = rt::NoClosestHit<Context>;
    typealias AnyHit = VisibilityAnyHit;
    typealias Intersection = rt::NoIntersection<Context>;
}

struct ScatterMissContext : rt::IPayloadContext
{
    typealias TraceContext = ReferencePathTracerTraceContext;
    typealias Payload = PathPayload;
    typealias Record = void;
}

struct VisibilityMissContext : rt::IPayloadContext
{
    typealias TraceContext = ReferencePathTracerTraceContext;
    typealias Payload = VisibilityPayload;
    typealias Record = void;
}

struct ScatterMiss : rt::IMissShader
{
    typealias Context = ScatterMissContext;

    void invoke(rt::MissInput<Context> input)
    {
        __target_switch
        {
        case hlsl:
        case glsl:
        case spirv:
        case cuda:
            handle_scatter_miss(input.payload);
        default:
            break;
        }
    }
}

struct VisibilityMiss : rt::IMissShader
{
    typealias Context = VisibilityMissContext;
    void invoke(rt::MissInput<Context> input) { input.payload.visible = true; }
}

struct ReferencePathTracerProgramSchema : rt::ITraceProgramSchema
{
    typealias TraceContext = ReferencePathTracerTraceContext;
    typealias HitGroups = rt::HitGroupList<ScatterHitGroup, VisibilityHitGroup>;
    typealias MissShaders = rt::MissShaderList<ScatterMiss, VisibilityMiss>;
    typealias CallableShaders = rt::NoCallableShaders;
}

rt::TraceProgramDescriptor<ReferencePathTracerProgramSchema> reference_path_tracer_program;

struct StructuralTraceRayVisibilityQuery : IVisibilityQuery
{
    bool is_occluded(Ray ray)
    {
        rt::RayTraversalDesc desc = {};
        desc.ray.origin = ray.origin;
        desc.ray.direction = ray.dir;
        desc.ray.tMin = ray.t_min;
        desc.ray.tMax = ray.t_max;
        desc.rayFlags = RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH | RAY_FLAG_SKIP_CLOSEST_HIT_SHADER;
        desc.instanceMask = 0xff;
        desc.sbtOffset = VISIBILITY_RAY_INDEX;
        desc.sbtStride = 0;
        desc.missIndex = VISIBILITY_RAY_INDEX;

        VisibilityPayload payload = {};
        rt::RayTracer<ReferencePathTracerProgramSchema> tracer;
        tracer.trace(desc, g_scene.tlas, reference_path_tracer_program, payload);
        return !payload.visible;
    }
}

void handle_structural_scatter_hit(inout PathPayload payload, HitInfo hit)
{
    if (VISIBILITY_RAY_MODE == VisibilityRayMode::trace_ray) {
        StructuralTraceRayVisibilityQuery visibility_query;
        handle_scatter_hit(visibility_query, payload, hit);
    } else {
        InlineVisibilityQuery visibility_query;
        handle_scatter_hit(visibility_query, payload, hit);
    }
}

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

        rt::RayTracer<ReferencePathTracerProgramSchema> tracer;
        tracer.trace(desc, g_scene.tlas, reference_path_tracer_program, payload);
    }
}

/// Structural mode uses the shared non-SER scheduler. Visibility may use either inline traversal or
/// the second payload partition in the same structural pipeline.
struct StructuralSimpleScheduler : IPathScheduler
{
    float3 trace_path(no_diff Ray ray, no_diff uint path_id, no_diff UniformSampleGenerator sg)
    {
        SimpleScheduler<StructuralScatterTracer> scheduler;
        return scheduler.trace_path(ray, path_id, sg);
    }
}
