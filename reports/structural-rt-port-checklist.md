# Structural Ray Tracing Port Checklist and Change Ledger

**Updated:** 2026-09-14

**Scope:** revised shader schema plus host-owned runtime SBT records.

Legend: `[x]` means implemented or observed at the revision named here. `[ ]` means pending; each
pending item says whether it gates this port or is a deferred extension. Earlier phase results are
historical and are not silently reused.

## Exact revision tuple

- [x] Design archived at `kaizhangNV/slang:archive/structural-rt-with-design-docs-20260825`, commit
  `524aa27903d6ab7f46b3220466b1c7ed3415cce5`.
- [x] Slang compiler/fork branch `kaizhangNV/slang:draft/unified-pipeline-rt-api` pinned to
  `29969e72bacd308672b37e23a1b2ad7ea88c5ee2`.
- [x] Current implementation tracked by
  [`shader-slang/slang#12691`](https://github.com/shader-slang/slang/pull/12691).
- [x] slang-rhi branch `kaizhangNV/slang-rhi:codex/structural-rt-rhi-combined` pinned to
  `5661193d9415fb3c84c068afb149b85ea7fe2310`.
- [x] SlangPy branch `codex/dynamic-schema-host-bridge` is published at
  `fc9713b5d93501bded86d9082f4575573f50ef01` (migration commit `93b0e98b...`, based on
  `77205c2f3a5313c772d2df6c3cd19600887e938d`).
- [x] Falcor branch `codex/dynamic-schema-rt-port` has validation code head
  `6502d2d759e88bfced4af03a1a86423af8167a43`. The focused analytic-light RPT regression is
  `e300c18c74144b82585908b212e20c9150eb86d6`; the reusable Windows validator was added in
  `3229faa...` and extended through `9d0706c...`; the D3D environment-handle workaround is
  finalized in `278cbfb...`, followed by validator hardening in `9acbf18...`;
  `1ea1cf9...` returns success after the expected D3D diagnostic is classified, and `6502d2d...`
  classifies the inherited Vulkan LSS diagnostics while rejecting unexpected driver errors;
  and the SelectionProbe Metal-record workaround is `6131bc8fe3ea790de39ef5eba1c99cea199a8ec1`.
  The dependency integration is `ed005961d49032432c5c0c6a90a52d509e87f79f`, and the main migration is
  `042ba5d58a1e0c3ac33f01056bfbfd0066de6b16` (based on `b151bebcc5b7406ba9604e867569bdace6fe682a`).
- [x] Commit and push SlangPy; point the Falcor working tree at exact commit `fc9713b5...`.
- [x] Commit and push Falcor with the final SlangPy gitlink.
- [x] Verify the validation code head resolves the Falcor, SlangPy, and nested slang-rhi revisions
  to `6502d2d...`, `fc9713b5...`, and `5661193d...` respectively.

## Changed-file inventory

This lists every project-authored file in the revised port. The Falcor entries are the exact delta
from baseline `b151beb...` through the validation code head; the dependency entries cover the
integration commits named here rather than unrelated upstream submodule history. Detailed behavior
and tests are checked below.

- [x] Falcor Python and dependency: `examples/pathtracer/simple.py`,
  `falcor2/minitracer/pathtracer.py`, `falcor2/rendernodes/reference_pathtracer_node.py`, and the
  `external/slangpy` gitlink.
- [x] Falcor shaders: `slang/falcor2/minitracer/renderers/simplepathtracer_structural.slang`,
  `slang/falcor2/minitracer/scene/core.slang`, `slang/falcor2/render/lights/env_map_light.slang`,
  `slang/falcor2/rendernodes/reference_pathtracer.slang`,
  `slang/falcor2/rendernodes/reference_pathtracer_structural.slang`,
  `slang/falcor2/ui/kernels/scene_picker_structural.slang`, and
  `slang/falcor2/ui/kernels/selection_probe_structural.slang`.
- [x] Falcor C++/bindings: `src/falcor2/render/ray_tracing_setup.{h,cpp}`,
  `src/falcor2/ui/scene_picker.cpp`, `src/falcor2/ui/selection_overlay.{h,cpp}`, and
  `src/falcor2_ext/render/ray_tracing_setup.cpp`.
- [x] Falcor tests/tool: `tests/native/render/test_scene.cpp`,
  `tests/python/pathtracer/test_pathtracer.py`,
  `tests/python/pathtracer/test_reference_pathtracer_pipeline_api.py`,
  `tests/python/pathtracer/test_simple_sample.py`, `tests/python/ui/test_scene_picker.py`, and
  `tools/validate_revised_schema_windows.ps1`.
- [x] Falcor reports: `reports/structural-rt-port-plan.md`,
  `reports/structural-rt-port-checklist.md`, `reports/structural-rt-phase3-reproduction.md`, and
  `reports/structural-rt-phase4-reproduction.md`.
- [x] SlangPy bridge/configuration: `.agents/execplans/dynamic-structural-rt-schema-bridge.md`,
  `.gitmodules`, the `external/slang-rhi` gitlink, `slangpy/core/{calldata,function}.py`, and
  `slangpy/slang/staticarray.slang`.
- [x] SlangPy native layer: `src/sgl/device/fwd.h`, `pipeline.cpp`, `print.slang`,
  `raytracing.{h,cpp}`, `reflection.{h,cpp}`, and `types.h`; plus
  `src/slangpy_ext/device/raytracing.cpp`, `reflection.cpp`, and `shader.cpp`.
- [x] SlangPy tests: `slangpy/tests/slangpy_tests/test_raytracing.py`,
  `slangpy/tests/slangpy_tests/test_raytracing_config.py`,
  `slangpy/tests/slangpy_tests/test_raytracing_structural.slang`, and
  `tests/sgl/device/test_structural_raytracing.cpp`.
- [x] slang-rhi build/API/shared files: `CMakeLists.txt`, `include/slang-rhi.h`,
  `src/rhi-shared.{h,cpp}`, and `src/debug-layer/debug-device.cpp`.
- [x] slang-rhi backend files: `src/d3d12/d3d12-{command,device,shader-table}.cpp`,
  `src/d3d12/d3d12-shader-table.h`, `src/vulkan/vk-{device,shader-table}.cpp`,
  `src/vulkan/vk-shader-table.h`, `src/cuda/cuda-device.cpp`, and
  `src/cuda/optix-api.h` and `src/cuda/optix-api-impl.cpp`.
- [x] slang-rhi tests: `tests/test-ray-tracing-common.h`,
  `tests/test-ray-tracing-hitobject-intrinsics.{cpp,slang}`,
  `tests/test-ray-tracing-intrinsics.{cpp,slang}`,
  `tests/test-ray-tracing-shader-record-data.slang`, and `tests/test-shader-table.cpp`.
  Together these are the full file set for application-record transport (`6bea990...`) and the
  OptiX callable lookup/stack fixes (`e6525c2...`, `5661193...`).
- [x] Slang descriptor-lowering fixes `c8fbc736...`/`cdecb750...` change
  `source/slang/slang-emit.cpp`, `source/slang/slang-ir-metal-structural-ray-tracing.cpp`,
  `source/slang/slang-ir-structural-ray-tracing.{h,cpp}`, and
  `tests/ray-tracing-2/target/portable/trace-call.slang`.
- [x] Further Slang fixes authored for this integration: `f0ae84e7...` changes
  `prelude/slang-cuda-prelude.h`, `tests/ray-tracing-2/runtime/shaders/multiple-payloads.slang`, and
  `tools/gfx-unit-test/structural-ray-tracing/structural-ray-tracing-test-util.cpp`;
  `29969e72...` changes `source/slang/slang-check-structural-ray-tracing.cpp`,
  `tests/ray-tracing-2/frontend/module/visibility-unrelated-generics.slang`, and
  `tests/ray-tracing-2/frontend/module/visibility_unrelated_generics_lib.slang`.

## Historical provenance

These verified commits explain the previous port and remain useful when reviewing the new diff.
They do not prove the revised schema implementation.

### Slang compiler history

- `7b2bf16a65406ad4fc5973b78c05bc044e57dc24` — CUDA structural hit attributes.
- `8bc787db46d61f3816528a5eb08709a379074d54` — target-safe structural entry-point names.
- `b035d437be74e1ffb6c671c4e6630f07326e300b` — Metal Release termination fix.
- `e95ef5fbd549e43ef4a93502917975baf6a87848` — Metal Release regression.
- `49facf2c3639d84dded49f4dfcc8d983adab904e` — generic structural entry-point names.
- `6bf10cd992ba0e00233f67f8652b49b1fbba4e31` and
  `036132fa8fbfbe2e9300a0e0edb46d0405d973d0` — CUDA geometry-index fix and regression.
- `0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617` — structural stage type-flow roots.
- `f0ae84e7f330a3436aa7e38a26b3e67eda91569b` — exact OptiX payload register counts.
- `c8fbc73618b25034822d7ddb1bbf752749ce473a` — intermediate descriptor erasure plus DXIL
  live-uniform regression; validation exposed over-broad non-Metal erasure.
- `cdecb75031c1ce125985e51032c00a11c1f85492` — preserve the source descriptor shape on
  Vulkan/CUDA until target lowering; erase it early only for D3D.
- `29969e72bacd308672b37e23a1b2ad7ea88c5ee2` — scope structural runtime generic checks to modules
  whose dependency closure imports the trusted ray-tracing API.

### slang-rhi history

- `6bea990` — application data in hit, miss, and callable shader records.
- `e6525c2` — OptiX callable entry-point lookup.
- `5661193` — OptiX callable stack-size configuration and tests.

### SlangPy and Falcor history

- SlangPy `c2e73c0b1b0eed0577e544e6abdadfa1d32f7910` — initial host bridge.
- SlangPy `aa8840bc8ca644c45ea9d475f3f937b66faf8208` — Phase 1 plan closure.
- SlangPy `77205c2f3a5313c772d2df6c3cd19600887e938d` — composed structural calls.
- Falcor `af526615e77f4e59dc1169e5cff48101f0fa27fe` — Phase 1 integration.
- Falcor `cb73af277afdca68ac082871bfcdb5ceb6800ae8` — MiniTracer port.
- Falcor `bb92a32c09c26322a0eb474bd5031c0d4f65cd0f` — scene UI port.
- Falcor `f4062580a80b9765567f10a7c4eff840d68ccc0a` — runnable UI samples.
- Falcor `12448a57d16a53009973d3ff7b3a31eff2095d74` — ReferencePathTracer scatter port.
- Falcor `b151bebcc5b7406ba9604e867569bdace6fe682a` — old Phase 4 acceptance report.

## Shader contract migration

- [x] Replace shader-declared SBT positions with `ITraceProgramSchema` declarations.
- [x] Make each schema list only the finite set of hit groups, miss shaders, and callable shaders.
- [x] Move payload type selection from the shared trace context to `IHitContext` and
  `IPayloadContext`.
- [x] Give each stage an associated `Context` and use the revised non-parameterized stage
  interfaces.
- [x] Use `HitGroupList`, `MissShaderList`, and `CallableShaderList` without physical positions.
- [x] Treat reflected hit/miss function indices as compiler identities local to payload partitions,
  and callable indices as program-wide identities; neither kind is a physical SBT record index.
- [x] Put `PathPayload` and `VisibilityPayload` in one ReferencePathTracer schema.
- [x] Keep the existing inline `RayQuery` implementations unchanged.
- [x] Keep legacy pipeline shaders available for A/B validation.
- [x] Leave SER and hardware LSS out of the structural shader contract for this port.

## Slang compiler

- [x] Consume schema reflection for payload partitions, program types, function indices, record
  types, native payload/attribute sizes, and target entry-point metadata.
- [x] Pin the exact compiler revision instead of accepting an arbitrary PR checkout.
- [x] Fix OptiX trace/traverse/invoke helpers to pass the exact payload register count for payloads
  larger than eight words.
- [x] Add a compiler regression with an observable ten-word payload.
- [x] Validate compiler revision `cdecb750...`: trace-call 5/5 and portable 114/114.
- [x] Validate Cornell direct DXIL compilation and byte-identical legacy/structural output on
  Vulkan and OptiX.
- [x] Consume the reflected group-level name for synthesized `NoClosestHit`; restored focused
  coverage includes Metal name forwarding.
- [x] Add DXIL SIMPLE regression coverage with a live ordinary uniform in `c8fbc736...`.
- [x] Restrict early descriptor erasure to D3D in `cdecb750...`; Vulkan/CUDA retain the source shape
  until their target-specific lowering consumes it.
- [x] Fix linkage-wide structural generic checking in `29969e72...`: checks now require the current
  module or a dependency to import the trusted ray-tracing API.
- [x] Add and pass a regression that imports `slang.raytracing` before an unrelated module containing
  SlangPy-shaped vector and integer generics; this failed before the visibility fix.
- [x] Run the complete `tests/ray-tracing-2` suite at `29969e72...`: 384/384 passed.

## slang-rhi

- [x] Add owned application bytes to native shader records.
- [x] Transport application bytes in hit, miss, and callable records on D3D12, Vulkan, and OptiX.
  Vulkan and OptiX stages can read them. DXR rejects state creation for a live non-void `Record`
  because the pipeline lacks local root signatures; this is recorded below.
- [x] Validate record counts, sizes, alignment/stride, and data ownership in the shared layer and
  backend implementations.
- [x] Add shader-table record-data coverage.
- [x] Fix OptiX callable program lookup and callable stack sizing.
- [x] Pin the SlangPy nested submodule to `5661193d...` and its writable fork URL.
- [x] Re-run focused RHI tests from the final SlangPy checkout: 17 unique Vulkan/CUDA cases and
  956 assertions passed for shader-table records, callable lookup/stack sizing, and hit/miss bytes.

## SlangPy/SGL reflection and materialization

- [x] Replace old reflection wrappers with schema, payload-partition, hit-group, miss-shader, and
  callable-shader information.
- [x] Preserve reflected objects after their temporary reflection owner is released.
- [x] Expose open-section flags, record strides, maximum native sizes, function indices, record
  type layouts, primitive information, and target entry-point names.
- [x] Resolve structural stages by checked source name and shader stage.
- [x] Preserve renamed and specialized stage identity.
- [x] Resolve stages through composed modules and retain hot-reload metadata.
- [x] Diagnose ambiguous same-name ownership and generated-name collisions.
- [x] Accept ordered physical hit, miss, and callable type lists from the host.
- [x] Allow duplicate schema entry types at multiple physical record positions.
- [x] Use an empty type name for an empty physical record.
- [x] Accept per-record application bytes and zero-initialize omitted data for non-void records.
- [x] Reject data on empty records, unknown types, wrong section types, and oversized/undersized
  record values.
- [x] Derive maximum payload and attribute sizes from schema reflection.
- [x] Preserve collision-free names for empty native hit groups.
- [x] Retain materialized entry-point objects through pipeline linking.
- [x] Forward record bytes through `ShaderTableDesc` to slang-rhi.
- [x] Forward the synthesized `NoClosestHit` group-level name when no concrete closest-hit stage
  exists.
- [x] On Metal, skip standalone any-hit/intersection materialization when final reflection reports
  those logical stages were folded into candidate dispatchers.
- [x] Cover synthesized `NoClosestHit` forwarding and folded candidate-stage handling with focused
  cloned-reflection tests.
- [x] Make the native ABI-size expectation target-specific: Metal correctly reports zero because
  it has no native pipeline payload/attribute size settings; portable targets retain 4/8 in the
  fixture. The corrected Vulkan bridge passes 121/121 assertions.
- [x] Update SlangPy's `print.slang`/`staticarray.slang` matrix generic parameter to
  `MatrixLayoutMode` for Slang 2026.17.1 and cover it through native shader loading.

Primary touched areas:

- `src/sgl/device/reflection.{h,cpp}` and `src/slangpy_ext/device/reflection.cpp`;
- `src/sgl/device/raytracing.{h,cpp}`, `src/sgl/device/pipeline.cpp`, and
  `src/slangpy_ext/device/raytracing.cpp`;
- `src/slangpy_ext/device/shader.cpp`, `src/sgl/device/fwd.h`, and `src/sgl/device/types.h`; and
- `tests/sgl/device/test_structural_raytracing.cpp`.

## SlangPy functional API

- [x] Replace the structural configuration with `trace_program_schema`.
- [x] Add ordered `structural_*_types` and parallel `structural_*_record_data` arguments.
- [x] Reject mixing schema configuration with legacy hit/miss/callable arguments.
- [x] Reject explicit legacy ABI sizes in schema mode.
- [x] Require each data list to be empty or parallel to its type list.
- [x] Include schema name, exact type order, empty records, repetitions, and record bytes in cache
  identity.
- [x] Record the current high-level behavior: `CallData` uses the full identity for both pipeline
  and shader table, so a host-only record reorder/data edit also rebuilds the pipeline.
- [x] Defer the non-gating optimization to split pipeline identity from shader-table instance identity so
  host-only record changes can reuse the pipeline. Low-level SGL already supports creating a new
  table; this does not block correctness or indicate a shader API gap.
- [x] Compose generated prelude code with the base module before schema reflection/materialization.
- [x] Pass reflected ABI sizes and materialized records to pipeline/table creation.
- [x] Update Python configuration and runtime canary shaders/tests.
- [x] Maintain the living SlangPy ExecPlan at
  `.agents/execplans/dynamic-structural-rt-schema-bridge.md`.
- [x] Run the full SlangPy pre-commit suite; pyright reports zero errors and `git diff --check`
  passes.

Primary touched areas:

- `slangpy/core/function.py` and `slangpy/core/calldata.py`;
- `slangpy/tests/slangpy_tests/test_raytracing_config.py`;
- `slangpy/tests/slangpy_tests/test_raytracing.py`; and
- `slangpy/tests/slangpy_tests/test_raytracing_structural.slang`.

## Falcor scene integration

- [x] Add `StructuralShaderRecord` with schema type name plus application bytes.
- [x] Add `StructuralRayDesc` for one miss record and per-geometry hit records.
- [x] Reflect the required physical record counts from the scene policy.
- [x] Flatten hit records as `geometry_row * ray_type_count + ray_type`.
- [x] Preserve empty ray/geometry combinations instead of compacting the table.
- [x] Forward hit, miss, and callable application bytes when creating the shader table.
- [x] Retain structural materialized entry points until linking completes.
- [x] Expose the new helper structures and methods in `falcor2_ext`.
- [x] Reject structural LSS scenes explicitly.
- [x] Require zero callable records in the current scene-specific helper.
- [x] Add focused native coverage for exact geometry-major ordering, empty records, repeated
  program types with distinct application bytes, and reflected pipeline ABI limits.

Primary touched areas:

- `src/falcor2/render/ray_tracing_setup.{h,cpp}`;
- `src/falcor2_ext/render/ray_tracing_setup.cpp`; and
- `src/falcor2/ui/scene_picker.cpp` and `src/falcor2/ui/selection_overlay.{h,cpp}`.

## Sample checklist

### MiniTracer

- [x] Define `MiniTracerProgramSchema` with triangle closest-hit/any-hit and miss behavior.
- [x] Select schema mode from `Renderer.ray_tracing_pipeline_api`.
- [x] Supply one physical hit-group type and one miss-shader type from Python.
- [x] Keep legacy pipeline and inline intersector modes.
- [x] Re-run legacy/structural output parity on Vulkan with Slang `29969e72...`.
- [x] Leave a new inline-only parity run out of scope because that path was not changed by the
  pipeline migration.

Files: `slang/falcor2/minitracer/renderers/simplepathtracer_structural.slang` and
`falcor2/minitracer/pathtracer.py`.

### ScenePicker

- [x] Define `ScenePickerProgramSchema` with triangle closest-hit and miss entries.
- [x] Build its physical table through `SceneRayTracingSetup::create_structural()`.
- [x] Preserve legacy pipeline and compute/inline selection.
- [x] Retain the CUDA ray-generation global parameter-block workaround.
- [x] Re-run exact picked-ID map parity on Vulkan with Slang `29969e72...`.

Files: `slang/falcor2/ui/kernels/scene_picker_structural.slang` and
`src/falcor2/ui/scene_picker.cpp`.

### SelectionProbe

- [x] Define `SelectionProbeProgramSchema` with triangle any-hit and miss entries.
- [x] Preserve ignore-hit and accept/end-search behavior.
- [x] Build its physical table through `SceneRayTracingSetup::create_structural()`.
- [x] Carry the Metal selection-bitmap GPU address and bit count in 16 bytes of host-owned
  application record data, because generated Metal candidate functions cannot read ordinary
  globals. With the 16-byte system header, the final Metal hit-record stride is 32 bytes. Keep the
  existing global-buffer path on D3D12/Vulkan/CUDA.
- [x] Coarsely rebuild the Metal pipeline/table after selection changes or buffer reallocation so
  the record address/count cannot go stale. Defer table-only reconstruction as non-gating cache
  work; portable pipelines are not invalidated.
- [x] Leave its inline `RayQuery` path unchanged.
- [x] Retain the CUDA ray-generation global parameter-block workaround.
- [x] Re-run exact selection-mask parity on a layered non-opaque Vulkan scene. This exercises both
  `ignoreHit()` and accept/end-search in the structural any-hit stage.

Files: `slang/falcor2/ui/kernels/selection_probe_structural.slang` and
`src/falcor2/ui/selection_overlay.{h,cpp}`.

### ReferencePathTracer

- [x] Define one schema with `ScatterHitGroup`, `VisibilityHitGroup`, `ScatterMiss`, and
  `VisibilityMiss`.
- [x] Associate scatter with `PathPayload` and visibility with `VisibilityPayload`.
- [x] Build the six hit and three miss records in host-owned geometry-major order.
- [x] Keep the LSS record row empty and reject scenes that actually contain LSS.
- [x] Keep inline visibility selectable.
- [x] Add pipeline visibility at ray type `1` with recursion depth `2`.
- [x] Use recursion depth `1` when visibility remains inline.
- [x] Remove the obsolete test assumption that structural RPT requires `RayQuery`; devices without
  it select pipeline visibility.
- [x] Map `SchedulingMode.ser` to the simple scheduler with a warning.
- [x] Re-run legacy/structural Vulkan output parity for both inline `RayQuery` and pipeline
  `TraceRay` visibility.
- [x] Add a point-lit, environment-free legacy/structural regression for both visibility modes.
  Falcor still composes every `ILight` witness, so D3D12 also needs the explicit descriptor-handle
  construction workaround below even when this fixture disables environment lighting at runtime.
- [x] Verify the real composed program supplies `ILight`/`IMaterial` conformances and materializes
  both payload partitions. A standalone probe also succeeds after composing `ConstantLight` and
  `StandardMaterial` explicitly.
- [x] Classify RPT opacity any-hit coverage as deferred inherited Falcor integration. Triangle BLAS
  geometry is currently opaque and `OpacityEvaluator` is `AcceptAll`; the current scene therefore
  does not exercise RPT `ignoreHit()`.

Files: `slang/falcor2/rendernodes/reference_pathtracer_structural.slang`,
`falcor2/rendernodes/reference_pathtracer_node.py`, and
`tests/python/pathtracer/test_pathtracer.py`.

## Validation record

### Historical `cdecb750...` implementation baseline

- [x] At Slang `cdecb750...`, trace-call passed 5/5, portable passed 114/114, Cornell direct DXIL
  compiled cleanly, and Cornell legacy/structural output was byte-identical on Vulkan and OptiX.
- [x] At Slang `cdecb750...`, the focused SGL bridge passed 121/121 assertions, SlangPy configuration
  passed 19/19, and both Vulkan legacy and repeated-record/distinct-byte structural runtime canaries
  passed.
- [x] Rebuild SlangPy and Falcor against Slang `cdecb750...` (reported version
  `2026.17.1-156-gcdecb7503`) with the eight-job limiter for the original implementation baseline.
- [x] Falcor GCC native tests passed 4/4 scene-policy assertions and 13/13 reflected-ABI,
  geometry-major, repeated-record, and exact-byte assertions.
- [x] Falcor configuration passed 17/17; Vulkan legacy/structural runtime parity passed for all
  four consumers and for both RPT visibility modes.
- [x] Final-checkout slang-rhi validation passed 17 focused Vulkan/CUDA cases and 956 assertions;
  its isolated GCC Release build completed 221/221 build steps against Slang `cdecb750...`.
- [x] Reproduce the CUDA failure at the `cdecb750...` implementation baseline: both unchanged legacy
  and structural SlangPy canaries segfault at dispatch. Classify it as an inherited backend/test-
  host baseline rather than a structural-only regression; backend resolution remains pending.
- [x] Record the Linux Vulkan adapter as NVIDIA RTX PRO 6000 Blackwell Workstation Edition.
- [x] Record compiler fallback: Clang built production libraries, but Clang 17 rejected existing
  alias-template deduction in unrelated test files; GCC linked and ran the native tests.

### Final `29969e72...` / `6502d2d...` validation tuple

- [x] At Slang source revision `29969e72...`, rerun the focused SGL bridge (121/121 assertions) and
  SlangPy configuration/runtime cases (21/21), plus the six Vulkan consumer cases for MiniTracer,
  ScenePicker, SelectionProbe, and ReferencePathTracer (6/6). The compiler version string remains
  generated from the earlier configure step, so the source revision and loaded library path are
  recorded instead of mislabeling that string.
- [x] After the SelectionProbe Metal record workaround, direct profile-free `-target metal`
  production generation passed after formatting (21,339 bytes, SHA-256
  `2f74bc18adfa464d42ce50c2533f15b217f98d351f674fc74d33f79fb83e5cae`), direct SPIR-V generation
  passed, the limiter-capped Linux `falcor2_ext` rebuild passed, and both layered-quad Vulkan parity
  and structural record-byte tests passed (1/1 each).
- [x] macOS run
  `falcor2-revised-schema-final-9f87e21-slang29969-20260914-r4-macos-clt-continuation`
  passed in 546.816 seconds. Its artifacts include the source tuple, logs, schema JSON, generated
  MSL, and SHA-256 manifests under the run's `artifacts/macos-arm64-metal-compile-materialize/`
  directory.
- [x] Final SelectionProbe macOS continuation
  `falcor2-selectionprobe-metal-64b195c-29969-20260914-r1` passed in 9.750 seconds against Falcor
  `64b195c...` and Slang `29969e72...`. The production shader emitted 21,339 bytes of MSL (SHA-256
  `2f74bc18adfa464d42ce50c2533f15b217f98d351f674fc74d33f79fb83e5cae`) with the expected SBT
  record load and `uint device*` dereference. Reflection/materialization/linking passed with 16
  bytes of application data, a 32-byte final hit stride, and six physical hit records.
- [x] Windows comprehensive run `f2-r4c3-win-9f87-cached` supplied the retained MiniTracer and
  ScenePicker evidence: MiniTracer 1/1 and ScenePicker 2/2 passed on both D3D12 and Vulkan. Those
  consumers were unchanged by the later SelectionProbe, ReferencePathTracer, environment-handle,
  and validator commits. The overall older run is not labeled passing because its pre-workaround
  environment RPT case and the generic D3D record canary failed.
- [x] Final Windows run `f2-final-win-6502d2d-29969-r8` completed functional validation
  successfully in 133.632 seconds against Falcor
  `6502d2d...`, SlangPy `fc9713b5...`, Slang `29969e72...`, and slang-rhi `5661193d...`. The
  worker used one CMake project, `--parallel 1`, and `/MP8`/`CL_MPCount=8`. Configuration passed
  19/19; SelectionProbe parity passed 1/1 on both D3D12 and Vulkan; ReferencePathTracer's
  environment and analytic fixtures passed 4/4 on each backend across inline and pipeline
  visibility; and Vulkan application-record transport passed 1/1. The run log, source tuple,
  GPU/driver data,
  XML results, expected-D3D-gap classification, and SHA-256 manifest are under local-build-farm run
  `f2-final-win-6502d2d-29969-r8` and the worker's `revised-schema-final-windows-results` directory.
- [x] Reproduce the generic D3D12 non-void-record failure in that final run and accept it only after
  matching the exact `CreateStateObject`/unbound `UINT_MAX` CBV diagnostic. This expected canary is
  not counted as D3D record-data support.
- [x] Record that Windows Vulkan output parity passed but the inline visibility runs emitted
  validation VUID 08740/08742. The pre-existing `RayQuerySceneIntersector` compiles stale
  hardware-LSS query helpers whose inline SPIR-V declares both LSS and sphere capabilities on the
  RTX 3500 Ada runner, which lacks those features. The final classifier recorded 16 expected
  driver diagnostics, `functional_parity_passed=true`, and `validation_clean=false`; its artifact
  SHA-256 is `26337696a1f364858829c78595b5273efc8ec0c2f65b0fbddd862f36dc4db42f`. This is classified
  below. The retained ScenePicker inline lane emitted the same inherited VUIDs; the count of 16 is
  specifically from the final RPT classifier.

## Cross-platform acceptance

- [x] Linux Vulkan: SGL/SlangPy tests and all four Falcor consumers.
- [x] Linux CUDA/OptiX attempted at the `cdecb750...` baseline: unchanged legacy and structural
  SlangPy canaries both crash at dispatch, so this is recorded as an inherited backend/host blocker
  rather than an API regression.
- [x] Windows D3D12: all four Falcor consumers have functional legacy/structural parity coverage.
  Generic non-void shader-record data remains unsupported and is excluded from this claim.
- [x] Windows Vulkan: all four Falcor consumers have functional legacy/structural parity coverage.
  Inline-visibility output passes, but the inherited LSS validation diagnostics mean that path is
  not validation-clean.
- [x] Keep Windows CUDA/OptiX outside this focused D3D12/Vulkan acceptance lane; the compiler and
  Cornell OptiX path have separate coverage.
- [x] macOS Metal: SGL adapter passed 123/123 assertions; all four real Falcor schema bindings were
  created, applicable standalone entry points were materialized, and the programs linked. Folded
  any-hit/intersection candidates were intentionally not materialized separately.
  ReferencePathTracer was explicitly composed with `ILight -> ConstantLight` and
  `IMaterial -> StandardMaterial`.
- [x] macOS Metal: direct Slang-to-MSL generation passed for 3/3 revised-schema compiler fixtures.
  The three test-harness invocations were ignored by their directives (0/0), so they are not
  counted as passes; the direct compiler outputs and hashes are the evidence.
- [x] macOS Metal: generate production SelectionProbe MSL from its final relevant code head
  `64b195c...` and verify its 16-byte application-data ABI, 32-byte hit stride, record-header
  access, bounds check, and bitmap device-pointer load. Later commits do not change those
  SelectionProbe sources; broader final-head Metal validation was not rerun.
- [ ] macOS Metal: emit complete production MSL for MiniTracer, ScenePicker, and ReferencePathTracer
  and compile all generated MSL to AIR. This is non-gating: Falcor has no Metal pipeline runtime and
  production codegen remains incomplete; MiniTracer/ReferencePathTracer also contain
  target-incompatible Falcor logic, and the runner has no licensed full-Xcode `metal` executable.
- [x] Metal runtime is explicitly non-gating because Falcor has no pipeline RT runtime there.
- [x] Update the local build-farm recipe to Slang `29969e72...`, Falcor `6502d2d...`, exact SlangPy
  and slang-rhi pins, source checksums, and native build caps of at most eight jobs. The tracked
  entry point is `tools/validate_revised_schema_windows.ps1`; the machine-local recipe only supplies
  host paths and exact revisions.
- [x] Run `git diff --check` in the outer and nested worktrees and confirm the current reports make
  no active claim based on the superseded shader-owned table contract.
- [x] The full outer pre-commit suite passed at `1ea1cf9...`; the complete applicable touched-file
  hook set also passed after the final PowerShell/report changes at `6502d2d...`/publication head.

## Gap and workaround classification

### Confirmed shader API design gaps

- [x] None identified for triangle pipeline tracing without SER.
- [x] The previous multiple-payload blocker is resolved: payload is selected per hit/miss context,
  and ReferencePathTracer uses two payload partitions in one schema.

### Intentional scope decisions

- [x] Keep SER out of scope. Current containment: map the SER option to the simple scheduler.
- [x] Keep hardware LSS out of scope. Current containment: reject LSS structural scenes and leave their host
  records empty.
- [x] Keep Falcor Metal pipeline runtime out of scope. Compile/materialize only; do not claim
  rendering parity. Future runtime work must consume reflected IFT/VFT, record-header offsets, and
  descriptor resource bindings.
- [x] Keep Falcor scene-helper callables out of scope. The generic SGL bridge supports them, but the current helper
  intentionally accepts none.

### Implementation/integration issues and responsibilities

- [x] OptiX exact payload register count fixed in Slang `f0ae84e7...`.
- [x] Bind the reflected synthesized `NoClosestHit` group name and cover it in the final focused
  bridge rerun.
- [x] Fix SGL Metal candidate-stage handling: finalized reflection clears standalone any-hit and
  intersection names because those stages are folded into candidate dispatchers.
- [x] Fix and validate portable/DXIL descriptor lowering through Slang `cdecb750...`: early
  descriptor erasure is D3D-only, while Vulkan/CUDA preserve the source shape for target lowering.
  This was an implementation bug, not a structural API design gap.
- [x] Fix structural generic checks that were activated for every module in one linkage. Scoping
  them to modules whose dependency closure imports the API removes the SlangPy import-order failure;
  this was a compiler integration bug, not an API design gap.
- [x] Classify standalone ReferencePathTracer reflection correctly: the raw module is an incomplete
  program because Falcor supplies dynamic `ILight` and `IMaterial` conformances at composition.
  Explicit composition and normal RPT runtime both pass; no shader workaround is required.
- [x] Defer high-level SlangPy pipeline/table cache separation. Host-only physical record changes
  currently relink an unchanged pipeline; this is non-blocking integration/performance work.
- [x] Classify D3D12 shader-record reads as a backend implementation gap. Slang currently emits
  the synthesized `ShaderRecord` cbuffer without a finite register/space, and slang-rhi creates no
  DXR local root signature or export association. Record bytes reach the shader table, but DXR
  rejects pipeline state creation for a live non-void `Record` binding. The current Falcor
  consumers avoid this path: their portable records are void/unused, and SelectionProbe reads
  application data only in its Metal branch. A complete fix needs coordinated compiler binding/
  reflection, per-export record ABI metadata, local root constants/signatures, hit-group/export
  associations, and D3D runtime regressions. This is not a shader source/API design gap.
- [x] Classify the D3D12 ReferencePathTracer environment-light failure as orthogonal to structural
  RT. The source pattern predates this port, and the first legacy render failed before structural
  dispatch because specialization of `DescriptorHandleWAR<Texture2D<float>>.unwrap()` produced a
  `Texture2D<float4>` call argument. Falcor now keeps the descriptor as ordinary bytes across the
  helper boundary and performs `.unwrap()` inside each helper, avoiding the mismatched
  typed-resource call. This is a compiler/codegen compatibility workaround, not a shader-API gap.
- [x] Classify the Windows Vulkan LSS validation diagnostics as inherited inline-ray integration,
  not structural pipeline behavior. `RayQuerySceneIntersector` and its hardware-LSS calls predate
  this port (`a1dd414...`) and are compiled for triangle-only scenes even when the device has no NV
  LSS feature. Both legacy and structural RPT modes emit VUID 08740/08742 when visibility uses
  `ray_query`; both `trace_ray` parametrizations are clean. Output parity still passes, but the
  inline result is not validation-clean. The current workaround is pipeline visibility. A proper
  Falcor fix should use a link-time/static specialization tied to the actual hardware-LSS scene
  mode; a runtime branch cannot remove illegal SPIR-V capabilities. Falcor's compatibility helpers
  should also migrate to Slang's now-built-in capability-annotated LSS accessors: the stale inline
  SPIR-V helper currently overdeclares the sphere capability for an LSS positions/radii query. None
  of this requires a change to the revised shader API.
- [x] Classify the observed CUDA dispatch crash as inherited: it reproduces in unchanged legacy and
  structural canaries at the `cdecb750...` baseline. Root-cause work remains a backend/test-host
  task.
- [x] Record the v1 Metal candidate-data limitation precisely. Generated _AnyHit_/_Intersection_
  functions cannot read ordinary globals. SelectionProbe uses 16 bytes of plain application data
  in a 32-byte hit record to carry a resident bitmap's GPU address and logical bit count; this emits
  real MSL and avoids shader-side SBT positions. The code retains and still binds the bitmap;
  slang-rhi normally tracks it through a Metal residency set, with per-encoder `useResources` on
  paths that do not use residency sets. No Metal pipeline dispatch validated this path.
  D3D12/Vulkan/CUDA continue to use the
  global resource and receive zeroed application data. Rebuilding the Metal pipeline/table after
  selection changes or buffer reallocation is an integration workaround, not an API gap. The
  supported/default Metal MiniTracer path remains inline `RayQuery`; its structural pipeline path is
  not validated or claimed.
  ReferencePathTracer's Metal branch currently omits opacity behavior. Schema reflection/
  materialization and compiler-fixture MSL generation are not Falcor Metal runtime evidence.
- [x] ScenePicker and SelectionProbe keep the pre-existing CUDA ray-generation parameter-block
  workaround for `shader-slang/slang#10188`.
- [x] The host owns payload/primitive compatibility of reachable records. The adapter validates
  reflected types and bytes, but cannot prove arbitrary TLAS contributions and runtime trace
  selectors. This is an explicit safety boundary, not a shader API gap.

## Reports and publication

- [x] Replace the long port plan with the concise current model and status.
- [x] Replace obsolete phase reproduction recipes with superseded notices.
- [x] Preserve verified branch and commit provenance in this ledger.
- [x] Record published SlangPy commit `fc9713b5d93501bded86d9082f4575573f50ef01`.
- [x] Record validated Falcor code head `6502d2d759e88bfced4af03a1a86423af8167a43`
  and dependency-integration commit `ed005961d49032432c5c0c6a90a52d509e87f79f`.
- [x] Add the exact local Linux test matrix and classifications after the final revision rerun.
- [x] Add a concise runnable multi-payload command:

  ```bash
  cd /home/zhangkai/Documents/slangwork/slang-core-ecosys/falcor2
  export PYTHONPATH="$PWD:$PWD/external/slangpy"
  .venv/bin/python examples/pathtracer/simple.py --device-type vulkan \
    --pipeline-api structural --visibility-mode trace-ray --frames 8 \
    --output output/pathtracer-structural.png
  ```

  Omit `--frames` for an interactive run; the viewport overlay reports frame rate.
- [x] Defer Falcor legacy-versus-structural runtime measurement until after correctness acceptance;
  that follow-up must use identical scene, backend, resolution, warm-up, sample count, compiler,
  and driver settings.
