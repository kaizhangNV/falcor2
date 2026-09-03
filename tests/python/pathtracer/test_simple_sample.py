# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Configuration tests for the interactive ReferencePathTracer sample."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import slangpy as spy

import falcor2 as f2

PROJECT_ROOT = Path(__file__).parents[3]
SAMPLE_PATH = PROJECT_ROOT / "examples/pathtracer/simple.py"


@pytest.fixture(scope="module")
def sample() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reference_pathtracer_sample", SAMPLE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load sample: {SAMPLE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_args_preserves_legacy_interactive_defaults(sample: ModuleType) -> None:
    args = sample.parse_args([])

    assert args.pipeline_api == "legacy"
    assert args.frames == 0
    assert args.output is None
    assert args.spp == 1
    assert args.max_depth == 3


def test_parse_args_accepts_reproducible_structural_capture(sample: ModuleType) -> None:
    args = sample.parse_args(
        [
            "--device-type",
            "vulkan",
            "--pipeline-api",
            "structural",
            "--frames",
            "8",
            "--output",
            "output/phase4.png",
            "--width",
            "640",
            "--height",
            "360",
            "--spp",
            "2",
            "--max-depth",
            "5",
        ]
    )

    assert args.device_type == "vulkan"
    assert args.pipeline_api == "structural"
    assert args.frames == 8
    assert args.output == Path("output/phase4.png")
    assert (args.width, args.height, args.spp, args.max_depth) == (640, 360, 2, 5)


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--frames", "-1"),
        ("--width", "0"),
        ("--height", "0"),
        ("--spp", "0"),
        ("--max-depth", "0"),
    ],
)
def test_parse_args_rejects_invalid_counts(
    sample: ModuleType,
    option: str,
    value: str,
) -> None:
    with pytest.raises(SystemExit):
        sample.parse_args([option, value])


@pytest.mark.parametrize(
    ("pipeline_api", "expected_experimental"),
    [("legacy", False), ("structural", True)],
)
def test_device_enables_experimental_features_only_for_structural(
    sample: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    pipeline_api: str,
    expected_experimental: bool,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def create_device(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(sample.spy, "Device", create_device)

    result = sample.create_pathtracer_device(spy.DeviceType.vulkan, pipeline_api)

    assert result is sentinel
    assert captured["type"] == spy.DeviceType.vulkan
    compiler_options = captured["compiler_options"]
    assert isinstance(compiler_options, dict)
    assert compiler_options["enable_experimental_features"] is expected_experimental
    assert sample.PROJECT_ROOT / "external" in compiler_options["include_paths"]


@pytest.mark.parametrize(
    ("pipeline_api", "expected_api"),
    [
        ("legacy", f2.RayTracingPipelineAPI.legacy),
        ("structural", f2.RayTracingPipelineAPI.structural),
    ],
)
def test_configure_pipeline_selects_scatter_api(
    sample: ModuleType,
    pipeline_api: str,
    expected_api: f2.RayTracingPipelineAPI,
) -> None:
    path_tracer = SimpleNamespace()
    pipeline = SimpleNamespace(path_tracer=path_tracer)
    args = SimpleNamespace(pipeline_api=pipeline_api, spp=4, max_depth=7)

    sample.configure_pipeline(pipeline, args)

    assert pipeline.spp == 4
    assert path_tracer.ray_tracing_pipeline_api == expected_api
    assert path_tracer.max_depth == 7
    assert path_tracer.enable_nee is True
    assert path_tracer.enable_mis is True
    assert path_tracer.enable_analytic_lights is True
    assert path_tracer.enable_environment_light is True
    assert path_tracer.enable_emissive_triangles is True
    assert path_tracer.env_map_as_background is True
    assert pipeline.tone_map is True
