// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

module reference_legacy;

#include "falcor2/render/scene_ray_tracing.slangh"

__exported import falcor2.rendernodes.reference_pathtracer;
import falcor2.utils;

/// Pipeline visibility implementation retained for the legacy API comparison path.
struct LegacyTraceRayVisibilityQuery : IVisibilityQuery
{
    bool is_occluded(Ray ray)
    {
        VisibilityPayload payload = {};
        TraceRay(
            g_scene.tlas,
            RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH | RAY_FLAG_SKIP_CLOSEST_HIT_SHADER,
            0xff,
            VISIBILITY_RAY_INDEX,
            0 /* MultiplierForGeometryContributionHitGroupIndex */,
            VISIBILITY_RAY_INDEX,
            ray.to_ray_desc(),
            payload
        );
        return !payload.visible;
    }
};

SCENE_RAY_TYPE_MISS(scatter, scatter_miss, PathPayload);
void scatter_miss(inout PathPayload payload)
{
    handle_scatter_miss(payload);
}

SCENE_RAY_TYPE_CLOSEST_HIT(scatter, scatter_closest_hit, PathPayload);
void scatter_closest_hit<D : IDeferredHitInfo>(inout PathPayload payload, D deferred_hit)
{
    if (VISIBILITY_RAY_MODE == VisibilityRayMode::ray_query) {
        InlineVisibilityQuery visibility_query;
        handle_scatter_hit(visibility_query, payload, deferred_hit.create());
    } else if (VISIBILITY_RAY_MODE == VisibilityRayMode::trace_ray) {
        LegacyTraceRayVisibilityQuery visibility_query;
        handle_scatter_hit(visibility_query, payload, deferred_hit.create());
    }
}

SCENE_RAY_TYPE_MISS(visibility, visibility_miss, VisibilityPayload);
void visibility_miss(inout VisibilityPayload payload)
{
    payload.visible = true;
}

SCENE_RAY_TYPE_ANY_HIT(visibility, visibility_any_hit, VisibilityPayload);
void visibility_any_hit<D : IDeferredHitInfo>(inout VisibilityPayload payload, D deferred_hit)
{
    Ray ray = Ray(WorldRayOrigin(), WorldRayDirection(), RayTMin(), RayTCurrent());
    HitInfo hit = deferred_hit.create();
    if (OpacityEvaluator::is_valid_hit(ray, hit))
        AcceptHitAndEndSearch();
    else
        IgnoreHit();
}

struct LegacyScatterTracer : IScatterTracer
{
    void trace(no_diff Ray ray, inout PathPayload payload)
    {
        TraceRay(
            g_scene.tlas,
            0,
            0xff,
            SCATTER_RAY_INDEX,
            0 /* MultiplierForGeometryContributionHitGroupIndex */,
            SCATTER_RAY_INDEX,
            ray.to_ray_desc(),
            payload
        );
    }
};

/// Compatibility wrapper that uses the shared non-SER scheduler.
public struct LegacySimpleScheduler : IPathScheduler
{
    public float3 trace_path(no_diff Ray ray, no_diff uint path_id, no_diff UniformSampleGenerator sg)
    {
        SimpleScheduler<LegacyScatterTracer> scheduler;
        return scheduler.trace_path(ray, path_id, sg);
    }
};
