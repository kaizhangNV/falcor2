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
  `cdecb75031c1ce125985e51032c00a11c1f85492`.
- [x] Current implementation tracked by
  [`shader-slang/slang#12691`](https://github.com/shader-slang/slang/pull/12691).
- [x] slang-rhi branch `kaizhangNV/slang-rhi:codex/structural-rt-rhi-combined` pinned to
  `5661193d9415fb3c84c068afb149b85ea7fe2310`.
- [x] SlangPy branch `codex/dynamic-schema-host-bridge` is published at
  `53385859307f020d80410045548d2cdefc8ab2e8` (based on
  `77205c2f3a5313c772d2df6c3cd19600887e938d`).
- [x] Falcor work is on `codex/dynamic-schema-rt-port`, based on
  `b151bebcc5b7406ba9604e867569bdace6fe682a`.
- [x] Commit and push SlangPy; point the Falcor working tree at exact commit `53385859...`.
- [ ] Commit and push Falcor after the final validation record is complete.
- [ ] Verify the published tuple from a clean recursive clone.

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
- [x] Validate compiler head `cdecb750...`: trace-call 5/5 and portable 114/114.
- [x] Validate Cornell direct DXIL compilation and byte-identical legacy/structural output on
  Vulkan and OptiX.
- [x] Consume the reflected group-level name for synthesized `NoClosestHit`; restored focused
  coverage includes Metal name forwarding.
- [x] Add DXIL SIMPLE regression coverage with a live ordinary uniform in `c8fbc736...`.
- [x] Restrict early descriptor erasure to D3D in `cdecb750...`; Vulkan/CUDA retain the source shape
  until their target-specific lowering consumes it.

## slang-rhi

- [x] Add owned application bytes to native shader records.
- [x] Support application bytes for hit, miss, and callable records on D3D12, Vulkan, and OptiX.
- [x] Validate record counts, sizes, alignment/stride, and data ownership in the shared layer and
  backend implementations.
- [x] Add shader-table record-data coverage.
- [x] Fix OptiX callable program lookup and callable stack sizing.
- [x] Pin the SlangPy nested submodule to `5661193d...` and its writable fork URL.
- [ ] Re-run the focused RHI tests from the final SlangPy recursive checkout.

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
- [ ] Deferred optimization: split pipeline identity from shader-table instance identity so
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
- [x] Flatten hit records as `geometry_type * ray_type_count + ray_type`.
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
- `src/falcor2/ui/scene_picker.cpp` and `src/falcor2/ui/selection_overlay.cpp`.

## Sample checklist

### MiniTracer

- [x] Define `MiniTracerProgramSchema` with triangle closest-hit/any-hit and miss behavior.
- [x] Select schema mode from `Renderer.ray_tracing_pipeline_api`.
- [x] Supply one physical hit-group type and one miss-shader type from Python.
- [x] Keep legacy pipeline and inline intersector modes.
- [x] Re-run legacy/structural output parity on Vulkan at the final revision tuple.
- [ ] Re-run inline output parity. This path was not changed and is non-gating for the pipeline
  migration.

Files: `slang/falcor2/minitracer/renderers/simplepathtracer_structural.slang` and
`falcor2/minitracer/pathtracer.py`.

### ScenePicker

- [x] Define `ScenePickerProgramSchema` with triangle closest-hit and miss entries.
- [x] Build its physical table through `SceneRayTracingSetup::create_structural()`.
- [x] Preserve legacy pipeline and compute/inline selection.
- [x] Retain the CUDA ray-generation global parameter-block workaround.
- [x] Re-run exact picked-ID map parity on Vulkan at the final revision tuple.

Files: `slang/falcor2/ui/kernels/scene_picker_structural.slang` and
`src/falcor2/ui/scene_picker.cpp`.

### SelectionProbe

- [x] Define `SelectionProbeProgramSchema` with triangle any-hit and miss entries.
- [x] Preserve ignore-hit and accept/end-search behavior.
- [x] Build its physical table through `SceneRayTracingSetup::create_structural()`.
- [x] Leave its inline `RayQuery` path unchanged.
- [x] Retain the CUDA ray-generation global parameter-block workaround.
- [x] Re-run exact selection-mask parity on a layered non-opaque Vulkan scene. This exercises both
  `ignoreHit()` and accept/end-search in the structural any-hit stage.

Files: `slang/falcor2/ui/kernels/selection_probe_structural.slang` and
`src/falcor2/ui/selection_overlay.cpp`.

### ReferencePathTracer

- [x] Define one schema with `ScatterHitGroup`, `VisibilityHitGroup`, `ScatterMiss`, and
  `VisibilityMiss`.
- [x] Associate scatter with `PathPayload` and visibility with `VisibilityPayload`.
- [x] Build the six hit and three miss records in host-owned geometry-major order.
- [x] Keep the LSS record row empty and reject scenes that actually contain LSS.
- [x] Keep inline visibility selectable.
- [x] Add pipeline visibility at ray type `1` with recursion depth `2`.
- [x] Use recursion depth `1` when visibility remains inline.
- [x] Map `SchedulingMode.ser` to the simple scheduler with a warning.
- [x] Re-run legacy/structural Vulkan output parity for both inline `RayQuery` and pipeline
  `TraceRay` visibility.
- [ ] **Deferred inherited Falcor integration:** verify RPT opacity any-hit behavior after triangle
  BLAS geometry can be non-opaque and `OpacityEvaluator` does more than `AcceptAll`. Do not claim
  the current opaque test scene exercises RPT `ignoreHit()`.

Files: `slang/falcor2/rendernodes/reference_pathtracer_structural.slang` and
`falcor2/rendernodes/reference_pathtracer_node.py`.

## Current test record

- [x] At Slang `cdecb750...`, trace-call passed 5/5, portable passed 114/114, Cornell direct DXIL
  compiled cleanly, and Cornell legacy/structural output was byte-identical on Vulkan and OptiX.
- [x] At final compiler head, the focused SGL bridge passed 121/121 assertions, SlangPy
  configuration passed 19/19, and both Vulkan legacy and repeated-record/distinct-byte structural
  runtime canaries passed.
- [x] Rebuild SlangPy and Falcor against Slang `cdecb750...` (reported version
  `2026.17.1-156-gcdecb7503`) with the eight-job limiter.
- [x] Falcor GCC native tests passed 4/4 scene-policy assertions and 13/13 reflected-ABI,
  geometry-major, repeated-record, and exact-byte assertions.
- [x] Falcor configuration passed 17/17; Vulkan legacy/structural runtime parity passed for all
  four consumers and for both RPT visibility modes.
- [x] Reproduce the CUDA failure at the final tuple: both unchanged legacy and structural SlangPy
  canaries segfault at dispatch. Classify it as an inherited backend/test-host baseline rather
  than a structural-only regression; backend resolution remains pending.
- [x] Record the Linux Vulkan adapter as NVIDIA RTX PRO 6000 Blackwell Workstation Edition.
- [x] Record compiler fallback: Clang built production libraries, but Clang 17 rejected existing
  alias-template deduction in unrelated test files; GCC linked and ran the native tests.
- [ ] Record cross-platform worker run IDs, durations, and artifacts when those gates run.

## Cross-platform acceptance

- [x] Linux Vulkan: SGL/SlangPy tests and all four Falcor consumers.
- [ ] Linux CUDA/OptiX: SGL/SlangPy tests and supported Falcor consumers.
- [ ] Windows D3D12: SGL/SlangPy tests and all four Falcor consumers.
- [ ] Windows Vulkan: SGL/SlangPy tests and all four Falcor consumers.
- [ ] Windows CUDA/OptiX where supported by the runner.
- [ ] macOS Metal: raw Slang schema reflection and MSL generation.
- [ ] macOS Metal: SGL adapter tests plus supported Falcor compile/materialization checks; no
  runtime claim.
- [x] Metal runtime is explicitly non-gating because Falcor has no pipeline RT runtime there.
- [ ] Update local build-farm recipes to the exact final revision tuple and eight-job cap.
- [x] Run `git diff --check` in the outer and nested worktrees and confirm the current reports make
  no active claim based on the superseded shader-owned table contract.

## Gap and workaround classification

### Confirmed shader API design gaps

- [x] None identified for triangle pipeline tracing without SER.
- [x] The previous multiple-payload blocker is resolved: payload is selected per hit/miss context,
  and ReferencePathTracer uses two payload partitions in one schema.

### Intentional omissions

- [ ] SER support. Current containment: map the SER option to the simple scheduler.
- [ ] Hardware LSS support. Current containment: reject LSS structural scenes and leave their host
  records empty.
- [ ] Falcor Metal pipeline runtime. Current containment: compile/materialize only; do not claim
  rendering parity. Future runtime work must consume reflected IFT/VFT, record-header offsets, and
  descriptor resource bindings.
- [ ] Falcor scene-helper callables. The generic SGL bridge supports them, but the current helper
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
- [ ] Optimize high-level SlangPy pipeline/table caching so host-only physical record changes do not
  relink an unchanged pipeline. This is non-blocking integration/performance work.
- [x] Classify the observed CUDA dispatch crash as inherited: it reproduces in unchanged legacy and
  structural canaries at the final revision. Root-cause work remains a backend/test-host task.
- [x] Metal-only shader branches are deliberately incomplete Falcor hit-data implementations. Raw
  Slang schema/MSL codegen is compile evidence, not runtime correctness.
- [x] ScenePicker and SelectionProbe keep the pre-existing CUDA ray-generation parameter-block
  workaround for `shader-slang/slang#10188`.
- [x] The host owns payload/primitive compatibility of reachable records. The adapter validates
  reflected types and bytes, but cannot prove arbitrary TLAS contributions and runtime trace
  selectors. This is an explicit safety boundary, not a shader API gap.

## Reports and publication

- [x] Replace the long port plan with the concise current model and status.
- [x] Replace obsolete phase reproduction recipes with superseded notices.
- [x] Preserve verified branch and commit provenance in this ledger.
- [x] Record published SlangPy commit `53385859307f020d80410045548d2cdefc8ab2e8`.
- [ ] Add the final Falcor commit hash after publication.
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
- [ ] Measure legacy versus structural runtime only after correctness acceptance; use identical
  scene, backend, resolution, warm-up, sample count, compiler, and driver settings.
