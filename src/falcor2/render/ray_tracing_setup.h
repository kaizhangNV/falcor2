// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "falcor2/render/fwd.h"
#include "falcor2/render/shared_scene_types.h"

#include "falcor2/core/macros.h"

#include <sgl/device/fwd.h>
#include <sgl/device/shader.h>
#include <sgl/device/pipeline.h>
#include <sgl/device/raytracing.h>

#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace falcor {

/// Shader API used to implement a native ray-tracing pipeline.
enum class RayTracingPipelineAPI {
    legacy,
    structural,
};

/// Helper to create a ray tracing pipeline and shader table for a scene.
///
/// Based on the scene's hit group policy the following is provided:
/// - a list of entry point names to link into the ray tracing shader program.
/// - a list of hit group descriptors for pipeline creation.
/// - a list of hit group names for ShaderTableDesc (ordered per scene's hit group policy).
/// - a list of miss entry point names for ShaderTableDesc (one per ray type).
/// - ray tracing pipeline flags.
///
/// In addition, this helper also provides functions to further simplify pipeline and shader table creation from the
/// collected data:
/// - link_program() to link a shader program with the collected entry points plus additional ones (e.g., ray gen).
/// - create_pipeline() to create a ray tracing pipeline from the linked shader program.
/// - create_shader_table() to create a shader table from the linked shader program and ray gen entry points.
///
struct FALCOR_API SceneRayTracingSetup {

    /// Options for creating the ray tracing setup.
    struct Options {
        /// Skip hit groups for geometry types that are not present in the scene (replace with dummy entries).
        bool skip_unused_geometry_types{true};
    };

    /// Scene-derived physical shader-table shape and flags for structural ray tracing.
    struct StructuralRequirements {
        uint32_t hit_group_record_count{0};
        uint32_t miss_shader_record_count{0};
        uint32_t callable_shader_record_count{0};
        sgl::RayTracingPipelineFlags pipeline_flags{sgl::RayTracingPipelineFlags::none};
    };

    /// One host-selected physical structural shader record.
    struct StructuralShaderRecord {
        /// Fully qualified shader-side schema entry type. Empty selects an empty physical record.
        std::string type_name;
        /// Application bytes copied after the native shader identifier.
        std::vector<uint8_t> data;
    };

    /// Structural miss and per-geometry hit records for one ray type.
    struct StructuralRayDesc {
        StructuralShaderRecord miss_shader;
        std::unordered_map<shared::GeometryType, StructuralShaderRecord> hit_groups;
    };

    /// Description of a single ray type.
    /// This describes ray types defined with the helper macros found in scene_ray_tracing.slangh.
    struct RayDesc {
        /// Ray type name (for example "intersect", "visibility", etc.).
        /// Needs to match the ray type name used in the SCENE_RAY_TYPE_XXX macros.
        std::string name;
        /// Whether this ray type has an associated miss shader.
        /// Needs SCENE_RAY_TYPE_MISS to be defined for this ray type.
        bool has_miss{false};
        /// Whether this ray type has an associated closest hit shader.
        /// Needs SCENE_RAY_TYPE_CLOSEST_HIT to be defined for this ray type.
        bool has_closest_hit{false};
        /// Whether this ray type has an associated any hit shader.
        /// Needs SCENE_RAY_TYPE_ANY_HIT to be defined for this ray type.
        bool has_any_hit{false};
    };

    /// Description of a single ray type with its miss shader and hit groups per geometry type.
    struct PerGeometryTypeRayDesc {
        /// Miss shader entry point name.
        std::string miss_entry_point;
        /// Hit groups keyed by geometry type.
        std::unordered_map<shared::GeometryType, sgl::HitGroupDesc> hit_groups;
    };

    /// Create a ray tracing setup for a scene given ray type descriptions.
    /// Missing ray types, geometry types, and unused scene geometry types are filled with dummy entries.
    /// @param scene The scene to create the setup for.
    /// @param ray_descs Per-ray-type descriptions (miss shader + hit groups keyed by geometry type).
    /// @param options Optional configuration options.
    /// @return The populated ray tracing setup.
    static SceneRayTracingSetup
    create(const Scene* scene, std::span<const RayDesc> ray_descs, std::optional<Options> options = std::nullopt);

    static SceneRayTracingSetup
    create(const Scene* scene, std::initializer_list<RayDesc> ray_descs, std::optional<Options> options = std::nullopt)
    {
        return create(scene, std::span<const RayDesc>(ray_descs.begin(), ray_descs.size()), options);
    }

    /// Create a ray tracing setup for a scene given per-ray-type descriptions.
    /// Missing ray types, geometry types, and unused scene geometry types are filled with dummy entries.
    /// @param scene The scene to create the setup for.
    /// @param ray_descs Per-ray-type descriptions (miss shader + hit groups keyed by geometry type).
    /// @param options Optional configuration options.
    /// @return The populated ray tracing setup.
    static SceneRayTracingSetup create(
        const Scene* scene,
        std::span<const PerGeometryTypeRayDesc> ray_descs,
        std::optional<Options> options = std::nullopt
    );

    static SceneRayTracingSetup create(
        const Scene* scene,
        std::initializer_list<PerGeometryTypeRayDesc> ray_descs,
        std::optional<Options> options = std::nullopt
    )
    {
        return create(scene, std::span<const PerGeometryTypeRayDesc>(ray_descs.begin(), ray_descs.size()), options);
    }

    /// Return the scene policy requirements for a structural ray-tracing call.
    /// This validates the currently supported policy and geometry types without materializing stages.
    static StructuralRequirements get_structural_requirements(const Scene* scene);

    /// Create a ray tracing setup from a reflected structural schema and host-owned physical records.
    /// @param scene The scene to create the setup for.
    /// @param module The composed Slang module that owns the reflected schema.
    /// @param schema_name Name of the structural trace-program schema.
    /// @param ray_descs Per-ray-type physical shader records. Records are flattened geometry-major.
    /// @param options Optional configuration options.
    /// @return The populated ray tracing setup.
    static SceneRayTracingSetup create_structural(
        const Scene* scene,
        sgl::SlangModule* module,
        std::string_view schema_name,
        std::span<const StructuralRayDesc> ray_descs,
        std::optional<Options> options = std::nullopt
    );

    static SceneRayTracingSetup create_structural(
        const Scene* scene,
        sgl::SlangModule* module,
        std::string_view schema_name,
        std::initializer_list<StructuralRayDesc> ray_descs,
        std::optional<Options> options = std::nullopt
    )
    {
        return create_structural(
            scene,
            module,
            schema_name,
            std::span<const StructuralRayDesc>(ray_descs.begin(), ray_descs.size()),
            options
        );
    }

    /// Entry point names needed for the ray tracing pipeline.
    std::vector<std::string> entry_points;
    /// Hit group descriptors for RayTracingPipelineDesc.
    std::vector<sgl::HitGroupDesc> hit_groups;
    /// Hit group names for ShaderTableDesc (ordered per scene's hit group policy).
    std::vector<std::string> sbt_hit_group_names;
    /// Miss entry point names for ShaderTableDesc (one per ray type).
    std::vector<std::string> sbt_miss_entry_points;
    /// Callable entry point names for ShaderTableDesc.
    std::vector<std::string> sbt_callable_entry_points;
    /// Application record bytes parallel to sbt_hit_group_names.
    std::vector<std::vector<uint8_t>> sbt_hit_group_record_data;
    /// Application record bytes parallel to sbt_miss_entry_points.
    std::vector<std::vector<uint8_t>> sbt_miss_shader_record_data;
    /// Application record bytes parallel to sbt_callable_entry_points.
    std::vector<std::vector<uint8_t>> sbt_callable_shader_record_data;
    /// Ray tracing pipeline flags (e.g., enable_linear_swept_spheres).
    sgl::RayTracingPipelineFlags pipeline_flags{sgl::RayTracingPipelineFlags::none};
    /// Reflected native payload size for a structural schema, or zero for a legacy setup.
    uint32_t max_ray_payload_size{0};
    /// Reflected native hit-attribute size for a structural schema, or zero for a legacy setup.
    uint32_t max_attribute_size{0};

    /// Link a shader program with the setup's entry points plus additional ones (e.g., ray gen).
    /// @param module The composed Slang module containing all entry points.
    /// @param additional_entry_points Additional entry point names to include (e.g., ray gen shaders).
    /// @return The linked shader program.
    sgl::ref<sgl::ShaderProgram>
    link_program(sgl::ref<sgl::SlangModule> module, std::vector<std::string> additional_entry_points = {}) const;

    /// Create a ray tracing pipeline from this setup.
    /// The hit_groups field is overwritten and flags are OR'ed with the setup's pipeline_flags.
    /// @param desc Pipeline descriptor (hit_groups is overwritten, flags are combined).
    /// @return The created ray tracing pipeline.
    sgl::ref<sgl::RayTracingPipeline> create_pipeline(sgl::RayTracingPipelineDesc desc) const;

    /// Create a shader table from this setup.
    /// @param program The linked shader program.
    /// @param ray_gen_entry_points Ray generation entry point names.
    /// @return The created shader table.
    sgl::ref<sgl::ShaderTable>
    create_shader_table(sgl::ref<sgl::ShaderProgram> program, std::vector<std::string> ray_gen_entry_points) const;

private:
    /// Structural stages are materialized entry points and cannot be looked up again by name.
    std::vector<sgl::ref<sgl::SlangEntryPoint>> m_materialized_entry_points;
    bool m_has_reflected_abi_limits{false};
};

} // namespace falcor
