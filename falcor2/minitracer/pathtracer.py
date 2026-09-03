# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from os import PathLike
from typing import Any, Optional, Union

from slangpy import Device, Texture, uint2, uint3
from slangpy.core.function import FunctionNode

from falcor2.minitracer.scene import Scene
from falcor2.minitracer.camera import Camera
from falcor2.minitracer.properties import PropertyObject, Property
from falcor2.minitracer.accumulator import Accumulator

import slangpy as spy


class RayTracingPipelineAPI(str, Enum):
    """Ray tracing pipeline API used by MiniTracer."""

    legacy = "legacy"
    structural = "structural"


class PathTracer(PropertyObject):
    def __init__(self, device: "Device"):
        super().__init__()
        self._device = device
        self._utils = spy.Module(device.load_module("falcor2.utils"))
        self._scene = spy.Module(device.load_module("falcor2.minitracer.scene"))
        self._module = spy.Module(
            device.load_module("falcor2.minitracer.renderers.simplepathtracer"),
            link=[self._utils, self._scene],
        )
        self._legacy_module: Optional[spy.Module] = None
        self._structural_module: Optional[spy.Module] = None
        self._constants = {}
        self._temp_accumulator: Optional[Accumulator] = None
        self._use_raytracing_pipeline = False
        self._ray_tracing_pipeline_api = RayTracingPipelineAPI.legacy
        # CUDA/OptiX does not support TraceRayInline
        if self._device.info.type == spy.DeviceType.cuda:
            self._use_raytracing_pipeline = True
        self.settings_changed()

    def settings_changed(self):
        self._constants["ENABLE_NEE"] = self.enable_nee
        self._constants["ENABLE_MIS"] = self.enable_mis
        self._constants["ENABLE_EMISSIVE_TRIANGLES"] = self.enable_emissive_triangles
        self._constants["ENABLE_ENV_MAP"] = self.enable_env_map
        self._constants["MAX_DEPTH"] = self.max_depth
        self._constants["ENV_MAP_AS_BACKGROUND"] = self.env_map_as_background
        self._constants["BACKGROUND_COLOR"] = self.background_color

    # Settings properties
    enable_nee = Property(value=True, label="Enable NEE", notify=settings_changed)
    enable_mis = Property(
        value=True, label="Enable MIS", notify=settings_changed, enable_if="@self.enable_nee"
    )
    enable_emissive_triangles = Property(
        value=True, label="Enable emissive triangles", notify=settings_changed
    )
    enable_env_map = Property(value=True, label="Enable env map", notify=settings_changed)
    max_depth = Property(value=3, label="Max depth", notify=settings_changed, min=1, max=10)
    env_map_as_background = Property(
        value=True, label="Env map as background", notify=settings_changed
    )
    background_color = Property(value=spy.float3(0.0, 0.0, 0.0), label="Background color")

    @property
    def use_raytracing_pipeline(self) -> bool:
        return self._use_raytracing_pipeline

    @use_raytracing_pipeline.setter
    def use_raytracing_pipeline(self, value: bool):
        if self._device.info.type == spy.DeviceType.cuda and not value:
            raise ValueError("Inline path tracing is not supported on CUDA/OptiX devices")
        self._use_raytracing_pipeline = value

    @property
    def ray_tracing_pipeline_api(self) -> RayTracingPipelineAPI:
        """Select the legacy or structural API when pipeline ray tracing is enabled."""
        return self._ray_tracing_pipeline_api

    @ray_tracing_pipeline_api.setter
    def ray_tracing_pipeline_api(self, value: Union[RayTracingPipelineAPI, str]):
        try:
            mode = RayTracingPipelineAPI(value)
        except ValueError:
            choices = ", ".join(mode.value for mode in RayTracingPipelineAPI)
            message = f"Unknown ray tracing pipeline API '{value}'; choose {choices}"
            raise ValueError(message) from None
        if (
            mode == RayTracingPipelineAPI.structural
            and not self._device.slang_session.desc.compiler_options.enable_experimental_features
        ):
            raise ValueError(
                "Structural ray tracing requires enable_experimental_features in the device's "
                "compiler options; use falcor2.minitracer.tools.create_device()."
            )
        self._ray_tracing_pipeline_api = mode

    def _get_structural_module(self) -> spy.Module:
        if self._structural_module is None:
            self._structural_module = spy.Module(
                self._device.load_module(
                    "falcor2.minitracer.renderers.simplepathtracer_structural"
                ),
                link=[self._module],
            )
        return self._structural_module

    def _get_legacy_module(self) -> spy.Module:
        if self._legacy_module is None:
            self._legacy_module = spy.Module(
                self._device.load_module("falcor2.minitracer.renderers.simplepathtracer_legacy"),
                link=[self._module],
            )
        return self._legacy_module

    def _get_render_module(self) -> spy.Module:
        if self._use_raytracing_pipeline:
            if self._ray_tracing_pipeline_api == RayTracingPipelineAPI.structural:
                return self._get_structural_module()
            return self._get_legacy_module()
        return self._module

    def render(
        self,
        scene: Scene,
        camera: Camera,
        color: spy.Tensor,
        spp: int,
        iteration: int,
        cmd: Optional[spy.CommandEncoder] = None,
    ):
        # Update camera
        camera.width = color.shape[1]
        camera.height = color.shape[0]
        camera.recompute()

        self.call(
            self.find_render_function(self._get_render_module(), "render"),
            scene=scene,
            ray_sampler=camera,
            output=color,
            spp=spp,
            iteration=iteration,
            _append_to=cmd,
        )

    def render_bwd(
        self,
        scene: Scene,
        camera: Camera,
        color: spy.Tensor,
        spp: int,
        iteration: int,
        cmd: Optional[spy.CommandEncoder] = None,
    ):
        # Update camera
        camera.width = color.shape[1]
        camera.height = color.shape[0]
        camera.recompute()

        self.call(
            self.find_render_function(self._get_render_module(), "render_bwd"),
            scene=scene,
            ray_sampler=camera,
            output_grad=color.grad,
            spp=spp,
            iteration=iteration,
            _append_to=cmd,
        )

    def render_guides(
        self,
        scene: Scene,
        camera: Camera,
        depth: spy.Tensor,
        albedo: spy.Tensor,
        position: spy.Tensor,
        normal: spy.Tensor,
        tangent: spy.Tensor,
        shading_normal: spy.Tensor,
        uv: spy.Tensor,
        specular: spy.Tensor,
        metallic: spy.Tensor,
        roughness: spy.Tensor,
        spp: int = 16,
        cmd: Optional[spy.CommandEncoder] = None,
    ):
        # Update camera
        camera.width = depth.shape[1]
        camera.height = depth.shape[0]
        camera.recompute()

        self.call(
            self.find_render_function(self._get_render_module(), "render_guides"),
            scene=scene,
            ray_sampler=camera,
            spp=spp,
            depth=depth,
            albedo=albedo,
            position=position,
            normal=normal,
            tangent=tangent,
            shading_normal=shading_normal,
            uv=uv,
            specular=specular,
            metallic=metallic,
            roughness=roughness,
            _append_to=cmd,
        )

    def render_accumulated(
        self,
        scene: Scene,
        camera: Camera,
        color: spy.Tensor,
        spp: int,
        iterations: int = 1,
        first_iteration: int = 0,
        cmd: Optional[spy.CommandEncoder] = None,
    ):
        width = color.shape[1]
        height = color.shape[0]
        if (
            self._temp_accumulator == None
            or width != self._temp_accumulator.width
            or height != self._temp_accumulator.height
        ):
            self._temp_accumulator = Accumulator(self._device, width, height)

        self._temp_accumulator.reset(cmd)

        for i in range(iterations):
            self.render(scene, camera, color, spp, first_iteration + i, cmd)
            self._temp_accumulator.update(color, cmd)

        self._temp_accumulator.output(color, cmd)

    def resample(
        self,
        input: spy.Tensor,
        output: Texture,
        output_pos: uint2,
        output_size: uint2,
        scale: float = 1,
        accumulator: bool = False,
        set_abs: bool = False,
        tone_map: bool = False,
    ):
        if isinstance(input.dtype, spy.reflection.ScalarType):
            self._module.resample_grayscale.dispatch(
                thread_count=uint3(output_size.x, output_size.y, 1),
                input=input,
                output=output,
                output_pos=output_pos,
                output_size=output_size,
                scale=scale,
                set_abs=set_abs,
                tone_map=tone_map,
            )
        elif isinstance(input.dtype, spy.reflection.VectorType) and input.dtype.num_elements == 2:
            self._module.resample_rg.dispatch(
                thread_count=uint3(output_size.x, output_size.y, 1),
                input=input,
                output=output,
                output_pos=output_pos,
                output_size=output_size,
                scale=scale,
                set_abs=set_abs,
                tone_map=tone_map,
            )
        elif isinstance(input.dtype, spy.reflection.VectorType) and input.dtype.num_elements == 3:
            self._module.resample_rgb.dispatch(
                thread_count=uint3(output_size.x, output_size.y, 1),
                input=input,
                output=output,
                output_pos=output_pos,
                output_size=output_size,
                scale=scale,
                set_abs=set_abs,
                tone_map=tone_map,
            )
        elif isinstance(input.dtype, spy.reflection.VectorType) and input.dtype.num_elements == 4:
            self._module.resample.dispatch(
                thread_count=uint3(output_size.x, output_size.y, 1),
                input=input,
                output=output,
                output_pos=output_pos,
                output_size=output_size,
                scale=scale,
                set_abs=set_abs,
                tone_map=tone_map,
                accumulator=accumulator,
            )
        else:
            raise ValueError("Unsupported input type for resample")

    def apply_tonemap(self, input: spy.Tensor, output: spy.Tensor):
        self._module.apply_tonemap(input, output)

    def load_module(self, path: PathLike[str]):
        link_root = self._module
        if self._use_raytracing_pipeline:
            if self._ray_tracing_pipeline_api == RayTracingPipelineAPI.structural:
                link_root = self._get_structural_module()
            else:
                link_root = self._get_legacy_module()
        module = spy.Module.load_from_file(
            self._device,
            path=str(path),
            link=[link_root],
        )
        return module

    def find_render_function(
        self,
        module: spy.Module,
        func_name: str,
    ) -> FunctionNode:
        if self._use_raytracing_pipeline:
            if self._ray_tracing_pipeline_api == RayTracingPipelineAPI.structural:
                intersector = "StructuralRayTracingSceneIntersector"
            else:
                intersector = "RayTracingSceneIntersector"
            return module.require_function(f"{func_name}<{intersector}>")
        else:
            return module.require_function(func_name + "<RayQuerySceneIntersector>")

    def call(
        self,
        func: FunctionNode,
        scene: Scene,
        **kwargs,
    ):
        call_func: Any = func
        if self._use_raytracing_pipeline:
            call_func = call_func.constants(self._constants).set({"g_scene": scene.get_this()})
            if self._ray_tracing_pipeline_api == RayTracingPipelineAPI.structural:
                call_func = call_func.ray_tracing(
                    trace_program_layout="MiniTracerProgramLayout",
                    max_recursion=5,
                    max_ray_payload_size=32,
                )
            else:
                call_func = call_func.ray_tracing(
                    hit_groups=[
                        {
                            "hit_group_name": "rt_hit",
                            "closest_hit_entry_point": "rt_closest_hit",
                            "any_hit_entry_point": "rt_any_hit",
                        }
                    ],
                    miss_entry_points=["rt_miss"],
                    max_recursion=5,
                    max_ray_payload_size=32,
                )
        else:
            call_func = call_func.constants(self._constants).set({"g_scene": scene.get_this()})
        return call_func.call(**kwargs)
