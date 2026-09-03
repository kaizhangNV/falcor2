# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Configuration-only tests for ReferencePathTracer's Phase 4 API switch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import slangpy as spy

import falcor2 as f2
from falcor2.rendernodes import ReferencePathTracerNode, VisibilityRayMode


def make_unloaded_node(
    *,
    experimental: bool,
    ray_query: bool,
    visibility: VisibilityRayMode = VisibilityRayMode.ray_query,
) -> tuple[ReferencePathTracerNode, list[str]]:
    """Construct just the property state so tests never load the structural shader leaf."""
    compiler_options = SimpleNamespace(enable_experimental_features=experimental)
    device = SimpleNamespace(
        slang_session=SimpleNamespace(
            desc=SimpleNamespace(compiler_options=compiler_options),
        )
    )

    def has_feature(feature: spy.Feature) -> bool:
        return feature == spy.Feature.ray_query and ray_query

    device.has_feature = has_feature

    node = object.__new__(ReferencePathTracerNode)
    node._device = device
    node._ray_tracing_pipeline_api = f2.RayTracingPipelineAPI.legacy
    node._visibility_ray_mode = visibility
    node._module = object()
    node._render_func = object()
    node._legacy_module = None
    node._structural_module = None
    settings_events: list[str] = []

    def settings_changed() -> None:
        settings_events.append("changed")
        node._render_func = None

    node.settings_changed = settings_changed
    return node, settings_events


def test_structural_selection_requires_experimental_features() -> None:
    node, settings_events = make_unloaded_node(experimental=False, ray_query=True)

    with pytest.raises(RuntimeError, match="experimental features"):
        node.ray_tracing_pipeline_api = "structural"

    assert node.ray_tracing_pipeline_api == f2.RayTracingPipelineAPI.legacy
    assert settings_events == []


def test_structural_selection_requires_inline_ray_query() -> None:
    node, settings_events = make_unloaded_node(experimental=True, ray_query=False)

    with pytest.raises(RuntimeError, match="requires inline RayQuery visibility"):
        node.ray_tracing_pipeline_api = f2.RayTracingPipelineAPI.structural

    assert node.ray_tracing_pipeline_api == f2.RayTracingPipelineAPI.legacy
    assert settings_events == []


def test_structural_selection_maps_trace_ray_visibility_without_loading_leaf() -> None:
    node, settings_events = make_unloaded_node(
        experimental=True,
        ray_query=True,
        visibility=VisibilityRayMode.trace_ray,
    )

    with pytest.warns(RuntimeWarning, match="maps trace-ray visibility"):
        node.ray_tracing_pipeline_api = "structural"

    assert node.ray_tracing_pipeline_api == f2.RayTracingPipelineAPI.structural
    assert node.visibility_ray_mode == VisibilityRayMode.ray_query
    assert node._module is None
    assert node._render_func is None
    assert settings_events == ["changed"]
    assert node._structural_module is None


def test_trace_ray_visibility_remains_compatible_alias_in_structural_mode() -> None:
    node, settings_events = make_unloaded_node(experimental=True, ray_query=True)
    node._ray_tracing_pipeline_api = f2.RayTracingPipelineAPI.structural

    with pytest.warns(RuntimeWarning, match="maps trace-ray visibility"):
        node.visibility_ray_mode = VisibilityRayMode.trace_ray

    assert node.visibility_ray_mode == VisibilityRayMode.ray_query
    assert settings_events == ["changed"]


def test_pipeline_api_rejects_unknown_string() -> None:
    node, settings_events = make_unloaded_node(experimental=True, ray_query=True)

    with pytest.raises(ValueError, match="choose legacy or structural"):
        node.ray_tracing_pipeline_api = "inline"

    assert node.ray_tracing_pipeline_api == f2.RayTracingPipelineAPI.legacy
    assert settings_events == []


def test_pipeline_api_rejects_unknown_enum_value() -> None:
    node, settings_events = make_unloaded_node(experimental=True, ray_query=True)

    with pytest.raises(ValueError, match="choose legacy or structural"):
        node.ray_tracing_pipeline_api = 2  # type: ignore[assignment]

    assert node.ray_tracing_pipeline_api == f2.RayTracingPipelineAPI.legacy
    assert settings_events == []
