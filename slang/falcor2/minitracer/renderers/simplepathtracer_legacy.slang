// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

module simplepathtracer_legacy;

import falcor2.minitracer.scene;
import falcor2.utils;

// Legacy pipeline ray-tracing variant. Keeping these stages outside the shared renderer lets the
// structural variant compose the same rendering code without selecting both ray-tracing APIs.

public struct RayTracingSceneIntersector : ISceneIntersector
{
    public HitInfo intersect(Ray ray, float alpha_threshold)
    {
        HitInfo hit = {};
        TraceRay(
            g_scene.tlas,
            0,
            0xff,
            0 /* RayContributionToHitGroupIndex */,
            0 /* MultiplierForGeometryContributionHitGroupIndex */,
            0 /* MissShaderIndex */,
            ray.to_ray_desc(),
            hit
        );
        return hit;
    }

    public bool is_occluded(Ray ray, float alpha_threshold)
    {
        HitInfo hit = intersect(ray, alpha_threshold);
        return hit.valid;
    }
};

[shader("miss")]
public void rt_miss(inout HitInfo hit)
{
    // hit.valid = false;
}

[shader("closesthit")]
void rt_closest_hit(inout HitInfo hit, BuiltInTriangleIntersectionAttributes attribs)
{
    hit.valid = true;
    hit.bary = attribs.barycentrics;
    hit.t = RayTCurrent();
#ifndef __TARGET_CUDA__
    hit.geometry_instance_id = GeometryInstanceID(InstanceID() + GeometryIndex());
#else
    hit.geometry_instance_id = GeometryInstanceID(InstanceID());
#endif
    hit.primitive_index = PrimitiveIndex();
}

[shader("anyhit")]
void rt_any_hit(inout HitInfo /*hit*/, BuiltInTriangleIntersectionAttributes attribs)
{
    HitInfo temp_hit = {};
    temp_hit.valid = true;
    temp_hit.bary = attribs.barycentrics;
    temp_hit.t = RayTCurrent();
#ifndef __TARGET_CUDA__
    temp_hit.geometry_instance_id = GeometryInstanceID(InstanceID() + GeometryIndex());
#else
    temp_hit.geometry_instance_id = GeometryInstanceID(InstanceID());
#endif
    temp_hit.primitive_index = PrimitiveIndex();

    if (!g_scene.is_valid_hit(temp_hit, WorldRayDirection(), 1.0))
        IgnoreHit();
}
