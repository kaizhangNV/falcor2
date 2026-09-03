# Structural Ray Tracing Port Checklist and Change Ledger

**Created:** 2026-09-02

**Purpose:** Track every source, repository, ABI, test, and platform change made during the Falcor 2
structural pipeline ray tracing port.

**Rule:** An item is checked only when the corresponding commit and validation evidence are recorded
in this file.

## Current verified state

- [x] Falcor fork cloned from `kaizhangNV/falcor2`.
  - Baseline branch: `main`
  - Baseline commit: `046545b1d3dac23e9ba1a75498eb75f6c9280dfc`
- [x] SlangPy submodule inspected.
  - Path: `external/slangpy`
  - Baseline commit: `1c0dddde0b86419aca16cf6b179ac2c9f540aba7`
  - Current branch: `codex/structural-rt-host-bridge`
  - Writable repository: `kaizhangNV/slangpy`
  - Upstream repository: `shader-slang/slangpy`
- [x] Original structural Slang baseline selected and reproduced for planning.
  - Baseline commit: `b0f010593568239005df17c30ea875c0edf25049`
- [x] Record the final Phase 1 compiler dependency after all required compiler fixes are committed,
  published, and validated.
  - Final dependency: `b035d437be74e1ffb6c671c4e6630f07326e300b` on
    `kaizhangNV/slang:codex/structural-rt-cuda-hit-attributes`.
  - It includes `7b2bf16a65406ad4fc5973b78c05bc044e57dc24` (CUDA late inputs),
    `8bc787db46d61f3816528a5eb08709a379074d54` (target-safe stage names), and
    `b035d437be74e1ffb6c671c4e6630f07326e300b` (Release-Clang Metal termination).
- [x] Pipeline and inline tracing sites classified.
- [x] SER-to-non-SER feasibility reviewed.
- [x] Bounded Phase 1 host approach identified: structural stages require checked `(name, stage)`
  resolution against exactly one enumerable SGL source-module leaf.
- [x] Initial plan report written.
- [x] Previously missing top-level `data`, `external/MaterialX`, and `external/openpbr-bsdf`
  submodules initialized recursively at their pinned revisions.
- [ ] Begin the Falcor renderer source port in Phase 2. No Falcor renderer source has been ported.
- [x] Phase 1 SlangPy/SGL source implementation committed and pushed as
  `c2e73c0b1b0eed0577e544e6abdadfa1d32f7910`.
- [x] Final SlangPy validation/ExecPlan follow-ups committed and pushed; the Phase 0-1 submodule
  revision is `aa8840bc8ca644c45ea9d475f3f937b66faf8208`.
- [x] Native build and Phase 0-1 runtime validation completed on 2026-09-03.
  - Structural Slang planning baseline: `2026.16-90-gb0f010593` from the original local checkout.
  - SlangPy capped Debug build: 392/392 steps passed on Linux.
  - Unchanged device enumeration and legacy ray-tracing canaries: Vulkan and CUDA, 4/4 passed.
  - Unmodified Release build reaches nanobind LTO and then GCC 11.5 crashes in `lto1`; Debug is the
    Phase 1 development configuration until that baseline toolchain issue is addressed separately.
  - Final-SHA Linux farm run `20260902-185955`: 197/197 native tests, 9/9 configuration tests,
    and 4/4 legacy-plus-structural Vulkan/CUDA runtime cases passed.
  - Final-SHA macOS farm run `20260902-185145`: 197/197 native tests and 9/9 configuration tests
    passed; Slang's structural closest-hit, miss, and raygen fixture generated non-empty Metal AIR.
  - Final-SHA Windows farm run `20260902-191209`: 197/197 native tests, 9/9 configuration tests,
    and 6/6 legacy-plus-structural D3D12/Vulkan/CUDA runtime cases passed.
  - The Windows inline control passed compute RayQuery on D3D12/Vulkan, skipped CUDA because the
    device reports ray queries unsupported, and passed pipeline ray launch on all three backends.

**Scope decision (2026-09-02):** The multi-payload/single-physical-pipeline API question is deferred.
The initial ReferencePathTracer port covers structural scatter with inline `RayQuery` visibility;
nested structural pipeline visibility is not part of the initial implementation. Hardware LSS and
SER are intentionally unsupported in the initial port and may be added later as feature extensions;
they are not treated as architectural design gaps.

## Classification of known gaps and risks

This taxonomy records what kind of work each item requires; it does not mark the item as resolved.

- **Structural RT design and deferred extensions:**
  - Multiple payload-typed routes sharing one physical pipeline/SBT: open design question, deferred.
  - Native hardware LSS primitive/data support: intentionally deferred feature extension.
  - Structural SER trace/reorder/deferred-invoke support: intentionally deferred feature extension;
    avoided by selecting `SimpleScheduler`.
- **Compiler/standard-library target implementation:**
  - CUDA late structural stage-input canonicalization before target varying legalization.
  - Deterministic target-safe structural stage names that agree across reflection, default checked
    materialization, explicit `renameEntryPoint()`, and portable adapter synthesis.
  - CUDA/OptiX lowering for the existing `IntersectionInput.reportHit()` API.
  - CUDA/OptiX lowering for the existing structural `geometryIndex` property, plus validation of
    Falcor's null per-geometry SBT-offset-buffer invariant when mapping it to
    `optixGetSbtGASIndex()`.
- **Host/RHI integration:**
  - Proven bounded Phase 1 materialization approach: reflect a deterministic public stage name and
    source type, then use distinct checked `(name, stage)` lookup for a concrete, non-generic stage
    declared directly in exactly one enumerable SGL leaf. Nested compositions can be flattened and
    ambiguity rejected without a new public compiler API.
  - Imported-only stage ownership, generic structural stages, and hot-reload re-resolution remain
    explicit follow-ups outside that bounded Phase 1 contract.
  - Metal ray-tracing pipeline, function-table, shader-table, and dispatch implementation.
- **Correctness invariant, not an API gap:** exact numeric SBT slot preservation from Falcor's TLAS
  metadata through reflected structural slots and host shader-table arrays.
- **Test/build infrastructure:** private golden-image availability and compiler/SGL ABI pinning.

For initial triangle-only, non-SER phases 1-4, there is no unresolved structural shader-API design
decision. The multi-payload composition question is explicitly excluded from that scope; hardware
LSS and SER are intentional feature omissions. Direct concrete non-generic leaf materialization is
a proven bounded host solution for Phase 1, while imported-only ownership, generic stages, hot
reload, same-FQN cross-module identity, and multi-stage source types remain explicit limitations or
follow-ups. The checklist sections below track their containment and eventual resolution separately.

## Repository and branch setup

- [x] Confirm `kaizhangNV/slangpy` exists as a fork destination for `shader-slang/slangpy`.
- [x] In `external/slangpy`, configure:
  - [x] `origin` as the writable `kaizhangNV/slangpy` fork.
  - [x] `upstream` as `shader-slang/slangpy`.
- [x] Create SlangPy branch `codex/structural-rt-host-bridge` from
  `1c0dddde0b86419aca16cf6b179ac2c9f540aba7`.
- [x] Write the required living SlangPy ExecPlan following `external/slangpy/.agents/PLANS.md` before
  changing source code.
- [x] Create Falcor branch `codex/structural-rt-port` from
  `046545b1d3dac23e9ba1a75498eb75f6c9280dfc`.
- [x] Update Falcor `.gitmodules` to the writable SlangPy fork.
- [x] Commit and push SlangPy source changes before updating the Falcor submodule pointer.
  - Implementation commit: `c2e73c0b1b0eed0577e544e6abdadfa1d32f7910`.
  - Final Phase 0-1 submodule revision: `aa8840bc8ca644c45ea9d475f3f937b66faf8208`.
- [x] Record the Slang compiler, SlangPy implementation/final gitlink, and Falcor publication
  commits together in the change ledger.
- [ ] Verify a fresh recursive clone resolves the exact SlangPy commit without local-only state.
- [x] Enable Slang's experimental features only in the Phase 1 structural SlangPy test session.
- [ ] Enable Slang's experimental features in affected Falcor device/session creation paths when
  the first renderer is ported; no Falcor renderer source changes in Phase 0-1.

## Structural Slang compiler dependency

- [x] Base Phase 1 on the committed CUDA late-input-lowering repair at
  `7b2bf16a65406ad4fc5973b78c05bc044e57dc24`, rather than treating the original
  `b0f010593568239005df17c30ea875c0edf25049` planning baseline as the final dependency.
- [x] Canonicalize triangle and custom hit-attribute parameters synthesized by late portable
  structural lowering before CUDA/PTX varying legalization.
- [x] Add four focused PTX FileCheck regression lanes covering triangle and custom structural hit
  attributes; CUDA runtime dispatch is validated separately.
- [x] Give each structural stage a deterministic reflected public entry-point name that is legal on
  CUDA and other C-like targets; qualified, reserved, or otherwise unsafe source type names must not
  leak into physical symbols.
- [x] Keep ordinary safe unqualified source type names stable as their default public names.
- [x] Make default, unrenamed checked materialization emit the same physical name advertised by
  structural reflection.
- [x] Preserve an explicit `renameEntryPoint()` physical-name override when portable structural
  materialization replaces the selected stage function with an adapter.
- [x] Add a regression for a structural stage source type named `main`: its physical name must avoid
  the target-reserved spelling while ordinary non-structural `main` entry-point behavior remains
  unchanged.
- [x] Add reflection/code-generation regressions covering target-safe names, the unrenamed default,
  explicit rename, and `main` handling.
- [x] Commit and publish the naming repair, then record the resulting final compiler revision and
  validation evidence.
- [x] Make Metal structural candidate-operation inlining unconditional in Release builds instead of
  hiding the required mutation in `SLANG_ASSERT`.
  - Commit: `b035d437be74e1ffb6c671c4e6630f07326e300b`.
  - Evidence: focused 1/1 fixture, 18/18 structural Metal tests, and macOS ARM64 Release
    Metal-to-AIR generation.

## SlangPy repository: native SGL bridge

### Stage-aware entry-point resolution

- [x] Extend the internal `SlangEntryPointDesc` with an explicit optional requested `ShaderStage`.
- [x] Add the distinct public native C++ method
  `SlangModule::checked_entry_point(name, stage, type_conformances)`. Do not add a stage-taking
  `entry_point` overload; the distinct name avoids source ambiguity for existing calls such as
  `entry_point(name, {})`.
- [x] Use `IModule::findAndCheckEntryPoint(name, stage, ...)` for structural entries.
- [x] Retain `findEntryPointByName()` behavior for ordinary legacy entry points.
- [x] Preserve the requested stage through type conformance, specialization, rename, and program
  relinking.
- [x] Support concrete, non-generic stage types declared directly in exactly one enumerable SGL
  source-module leaf.
- [x] Flatten nested composed modules, deduplicate repeated leaf objects, and reject zero or multiple
  checked matches instead of silently choosing the first source module.
- [x] Retain the unique declaring leaf as the checked entry point's lookup component during the
  current build/link lifetime.
- [x] Report Slang diagnostics and reject a materialized entry whose actual native stage does not
  match the requested stage.
- [x] Deduplicate materialized entries by fully qualified source type and native stage only after the
  unique-leaf check has established that identity is unambiguous.

### Explicit Phase 1 materialization limits and follow-ups

Unchecked items in this subsection are accepted Phase 1 limitations or later extensions; they do
not imply that the bounded Phase 1 bridge is incomplete.

- [x] Document that a stage declaration reachable only through a Slang `import` is not supported
  unless its declaring module is also an enumerable SGL source-module leaf. Reflection does not
  currently identify that declaring module.
- [ ] Add a direct imported-only-stage diagnostic regression.
- [x] Keep generic structural stage types unsupported in Phase 1 and document generic-argument
  materialization as a separate follow-up.
- [ ] Add explicit generic-stage detection and a focused diagnostic regression.
- [x] Treat structural hot reload as a documented follow-up: re-reflect the layout, re-run unique-leaf
  resolution, and invalidate every dependent entry point, pipeline, and shader table before claiming
  support.
- [x] Document and reject the case where different SGL leaves declare the same fully qualified stage
  type spelling. The reflected type name omits module identity, so the Phase 1 bridge must diagnose
  the multiple checked matches rather than guess which leaf owns the layout's stage.
- [x] Document that one source stage type implementing more than one native structural stage is not
  supported by the Phase 1 physical-name model. Supporting it requires a stage-qualified symbol or
  another collision-free identity contract; until then, use distinct source types.
- [ ] Add explicit one-source-type/multiple-native-stage detection and a focused diagnostic
  regression.
- [ ] If Falcor later needs imported-only, generic, same-FQN, or multi-stage-type support, add direct
  declaration identity/materialization to compiler reflection instead of accumulating host lookup
  heuristics.

### Structural layout reflection

- [x] Wrap `ProgramLayout::findTraceProgramLayout()` in SGL.
- [x] Add lifetime-safe SGL reflection values for:
  - [x] trace program layout and trace context;
  - [x] hit groups and logical slots;
  - [x] miss groups and logical slots;
  - [x] callable groups and logical slots;
  - [x] stage type, synthesized entry-point name, and native stage;
  - [x] context, record, primitive, attribute, and callable-data types where present.
- [x] Reject negative slots.
- [x] Reject duplicate slots within each SBT section.
- [x] Preserve sparse slots with explicit empty entries.

### Reusable pipeline-layout adapter

- [x] Convert reflected hit groups to existing `sgl::HitGroupDesc` values.
- [x] Produce the exact miss, hit-group, and callable arrays consumed by `sgl::ShaderTableDesc`.
- [x] Populate shader-table arrays by each reflected group's explicit `.slot`, not reflection or
  declaration order.
- [x] Preserve internal holes and caller-requested trailing dummy records.
- [x] Produce the stage-aware `SlangEntryPoint` objects needed for linking.
- [x] Apply each compiler-reflected deterministic public entry-point name to the checked stage so
  target compilation, pipeline descriptors, and shader-table lookup use the same physical symbol.
- [x] Keep the current `RayTracingPipelineDesc` and `ShaderTableDesc` path for D3D12, Vulkan, and CUDA.
- [x] Assert or clearly diagnose unsupported non-empty shader-record data until record overwrite
  support is intentionally added.
- [x] Do not add a fake `TraceProgramDescriptor` shader binding on D3D12, Vulkan, or CUDA.
- [x] Keep Metal physical descriptor/table binding outside this initial adapter.

### Native and Python exposure

- [x] Expose stage-aware entry-point lookup through nanobind.
- [x] Expose trace-layout reflection and the shared adapter through nanobind.
- [x] Generate the nanobind API stub and verify the new symbols. The separate optional
  `slangpy_pydoc` extraction target remains unavailable because `pybind11_mkdoc` is not installed.
- [x] Compile and exercise the added native/nanobind symbols on Windows, Linux, and macOS.
- [ ] Add an explicit ABI regression if numeric enum-value stability becomes a published contract;
  cross-platform compilation alone does not lock numeric values.

## SlangPy repository: functional ray tracing API

- [x] Extend `FunctionNode.ray_tracing()` with a structural option:
  `trace_program_layout="ProgramLayout"`.
- [x] Keep the legacy `hit_groups`, `miss_entry_points`, `hit_group_names`, and
  `callable_entry_points` path working during migration.
- [x] Make legacy and structural configuration mutually exclusive with a clear diagnostic.
- [x] Include the layout name, structural/legacy mode, hit-group names, miss/callable lists,
  recursion, payload size, attribute size, flags, and the remaining represented pipeline options in
  the SlangPy signature and pipeline/shader-table cache key. Code inspection covers those fields;
  exhaustive independent field-separation testing remains below. The old legacy signature omitted
  `hit_group_names`, which this implementation corrects.
- [x] Populate `FunctionBuildInfo` from the native structural-layout adapter.
- [x] Update `calldata.py` to consume the native adapter's checked `(fully qualified source type,
  stage)` materialization and compiler-reflected public entry-point names.
- [x] Preserve generated `raygen_main` and its call-data/resource marshalling.
- [x] Preserve deterministic functional-call and pipeline signature construction for structural and
  legacy configurations.
- [ ] Validate actual cache separation and reuse when multiple structural layouts/pipelines are used
  in one process.
- [x] Treat structural hot-reload invalidation as the explicit documented follow-up described above;
  do not
  infer it from deterministic signature-only tests.
- [x] Add no reflection-based inference for recursion, payload size, attribute size, or pipeline
  flags; preserve caller-supplied values and existing defaults.

## SlangPy repository: tests

Runtime sparse-slot selection, exhaustive signature-field separation, imported/generic stages,
multi-pipeline caching, and hot reload are deliberately retained as non-blocking follow-up tests.

- [x] Keep the existing legacy ray tracing test unchanged and passing.
- [x] Add the Phase 1 SlangPy-owned structural triangle hit/miss canary under `external/slangpy`
  using generated `raygen_main`; do not describe it as Falcor-owned.
- [x] Verify the four specified corner values (`[0,0,0]`, `[1,0,0]`, `[0,1,0]`, and `[1,0,1]`)
  using the canary's `numpy.allclose(..., atol=0.01)` comparison with NumPy's default `rtol`.
- [x] In native host-adapter tests, verify sparse hit, miss, and callable arrays, internal holes,
  reversed declaration order, and requested trailing minimum counts without dispatching rays.
- [ ] Separately add runtime dispatch coverage that selects non-zero sparse hit and miss slots and
  verifies the expected shader outputs. Host-array assertions alone do not prove runtime indexing.
- [x] Test duplicate and negative slot diagnostics.
- [ ] Add a distinct missing-stage lookup diagnostic regression; wrong-stage rejection is covered.
- [x] Test a closest-hit and any-hit pair that share a group.
- [x] Test direct concrete non-generic stage discovery in one source-module leaf.
- [x] Test nested composed-module flattening, repeated-leaf deduplication, zero matches, and ambiguous
  duplicate stage type names.
- [ ] Test clear Phase 1 diagnostics for imported-only and generic stages.
- [x] Test and reject the same-FQN-across-leaves ambiguity.
- [ ] Test and diagnose the one-source-type/multiple-native-stage limitation.
- [x] Test legacy/structural option exclusivity.
- [x] Test legacy signature equivalence plus separation by legacy hit-group name and structural
  layout name.
- [ ] Add a parameterized test proving that every remaining size, flag, group, mode, and
  pipeline-affecting field independently separates signatures.
- [ ] Separately exercise actual multi-pipeline cache reuse/separation in one runtime process.
- [ ] Separately exercise structural hot reload and dependent pipeline/shader-table invalidation
  before removing the Phase 1 hot-reload limitation.
- [x] Run formatting, static checks, native SGL tests, and focused SlangPy Python tests.

## Falcor repository: host integration

This is Phase 3 renderer integration and has not started. Keep every item unchecked until its Falcor
commit and validation evidence are recorded.

- [ ] Add a structural-layout overload or companion API to `SceneRayTracingSetup`.
- [ ] Reuse the SGL adapter rather than reimplementing Slang reflection in Falcor or Python.
- [ ] Preserve Falcor's geometry-major SBT index rule:
  `geometry_type * ray_type_count + ray_type`.
- [ ] For the current scene policy, validate absolute hit slots `0..5` (three ray types for triangles,
  followed by three for LSS) and miss slots `0..2`; structural group declarations must use those
  physical indices rather than restarting at zero for each geometry type.
- [ ] Preserve dummy records for absent ray types, absent geometry types, and sparse slots.
- [ ] Assert the exact ReferencePathTracer legacy mapping: triangle scatter/visibility/reserved at
  hit slots `0/1/2`, LSS scatter/visibility/reserved at `3/4/5`, and scatter/visibility/reserved miss
  slots at `0/1/2`.
- [ ] Add sentinel stages that produce distinguishable results for every exercised hit and miss slot;
  cover triangle slots first and LSS slots when LSS structural support is enabled.
- [ ] Preserve the CUDA built-in LSS intersection patch until structural LSS support is implemented.
- [ ] Expose the structural setup path through `falcor2_ext` for Python consumers.
- [ ] Keep the legacy setup path available as an A/B control during the initial port.

## Falcor repository: shader and sample migration

The Falcor renderer source port begins in Phase 2 and has not started. The Phase 1 canary is owned by
SlangPy and is tracked in the SlangPy test section above.

### Phase 2: MiniTracer

- [ ] Compile structural variants separately from legacy pipeline stages; do not link both APIs into
  one program because mixed legacy/structural tracing is diagnosed.
- [ ] Define MiniTracer trace, hit, and miss contexts.
- [ ] Convert MiniTracer miss, closest-hit, and alpha any-hit functions to structural stage types.
- [ ] Define its hit group, miss group, and `ITraceProgramLayout`.
- [ ] Replace only MiniTracer's pipeline `TraceRay` path.
- [ ] Leave `RayQuerySceneIntersector` unchanged.

### Phase 3: ScenePicker and SelectionProbe

- [ ] Convert ScenePicker pipeline stages and define its structural layout.
- [ ] Route ScenePicker through structural `SceneRayTracingSetup`.
- [ ] Leave non-pipeline paths unchanged.
- [ ] Convert SelectionProbe miss and any-hit behavior.
- [ ] Verify `ignoreHit` and accept/end-search behavior.
- [ ] Leave SelectionProbe's inline `RayQuery` branch unchanged.

### Phase 4: ReferencePathTracer

- [ ] Remove structural use of `HitObject::TraceRay`, `ReorderThread`, and `HitObject::Invoke`.
- [ ] Use the existing non-SER `SimpleScheduler` implementation.
- [ ] Decide and document compatibility behavior for the public `SchedulingMode.ser` value.
- [ ] Add `ScatterTraceContext` and `ScatterProgramLayout` using `PathPayload`.
- [ ] Keep visibility on inline `RayQuery` for the initial structural port.
- [ ] Decide whether a request for structural pipeline visibility is rejected or mapped to inline
  visibility, and expose that behavior clearly to users and tests.

### Deferred: multi-payload pipeline visibility

- [ ] Revisit whether the public model keeps `ITraceProgramLayout` as a typed trace route or adds a
  physical pipeline aggregate plus typed routes.
- [ ] Revisit placing `Payload` on `RayTracer` only together with a route-to-compatible-groups
  contract; a payload-only generic is insufficient.
- [ ] Define stage identity, sparse-slot merge rules, collision diagnostics, maximum-payload sizing,
  and Metal table ownership for multiple typed routes in one physical pipeline.
- [ ] Add a single generated-raygen canary that invokes two different payload routes and assembles
  them into one native D3D12/Vulkan/CUDA pipeline/SBT.
- [ ] Add a nested-trace variant of that canary.
- [ ] Add structural pipeline visibility only after the API design and cross-backend composition
  contract are approved.
- [ ] Do not silently use a larger union payload; treat it only as a reviewed, measured fallback.

### Shared scene stages and geometry expansion

- [ ] Replace `scene_ray_tracing.slangh` only after triangle samples pass.
- [ ] Add the structural primitive/data representation for hardware linear swept spheres.
- [ ] Add or validate CUDA structural `reportHit` lowering for procedural LSS.
- [ ] Add or validate the CUDA geometry-index property used by Falcor's deferred hit helpers.
- [ ] Port procedural and hardware LSS only after those prerequisites pass.

## Runtime resource-binding audit

- [ ] Confirm existing scene, camera, material, output, and call-data bindings keep identical reflected
  paths and resource types.
- [ ] Confirm D3D12/Vulkan/CUDA erase `TraceProgramDescriptor<Layout>` to no shader-visible storage.
- [ ] Confirm no per-frame structural stage object is written through `ShaderCursor`.
- [ ] Prove a structural closest-hit or miss stage can read a normal module global that was written
  through the existing root cursor.
- [ ] Verify pipeline creation binds synthesized stages and shader-table slots exactly once per
  compiled/cached pipeline.
- [ ] Treat Metal separately: reflect and bind IFT, VFT, and generated record-buffer resources only
  when a Metal runtime path is implemented.

## Validation gates

### Per-change checks

- [x] Format changed C++, Python, and Slang files.
- [x] Run focused unit tests for the changed layer.
- [x] Record exact command, runner, backend, result, and log or artifact path in the Phase 0-1
  acceptance entry below.
- [x] Confirm legacy pipeline RT tests still pass.
- [x] Confirm the existing inline control on the final Windows worker: compute RayQuery passes on
  D3D12/Vulkan and skips on CUDA because the device reports it unsupported; pipeline ray launch
  passes on D3D12/Vulkan/CUDA. A separate bounded local Linux run also passed Vulkan RayQuery and
  Vulkan/CUDA pipeline launch with the same CUDA RayQuery skip.
- [x] Inspect `git diff --check` in the Slang and SlangPy source commits.
- [ ] Confirm both worktrees are clean after commits.

### Cross-platform checks

- [x] Linux Vulkan structural canary.
- [x] Linux CUDA structural canary.
- [x] Windows D3D12 structural canary.
- [x] Windows Vulkan structural canary.
- [x] Windows CUDA structural canary.
- [x] macOS structural closest-hit, miss, and raygen shader compile plus Metal AIR generation using
  Slang's compiler-owned fixture. This is not SlangPy runtime coverage.
- [x] Record Metal runtime as deferred until the required RHI/function-table path exists.
- [x] Enforce at most eight native build jobs and eight logical CPUs on every runner.

### Sample exit gates

- [x] SlangPy-owned Phase 1 canary: the four specified corner values match under
  `numpy.allclose(..., atol=0.01)` with NumPy's default `rtol` on every supported runtime backend.
- [ ] MiniTracer: legacy and structural images meet the existing MSE threshold.
- [ ] ScenePicker: complete picked-ID maps match.
- [ ] SelectionProbe: complete masks match legacy and inline controls.
- [ ] Reference scatter: finite, non-zero output agrees with legacy non-SER output.
- [ ] Deferred Reference visibility gate: pipeline and inline visibility agree at the existing
  tolerances after the multi-payload design is approved and implemented.
- [ ] Stop for design review after the Phase 1 canary and the MiniTracer, ScenePicker, and
  SelectionProbe renderer gates pass.

## Change ledger

For every implementation commit, append one entry in chronological order with all fields below.

### Entry template

- **Date:**
- **Repository:** `kaizhangNV/slang`, `kaizhangNV/slangpy`, or `kaizhangNV/falcor2`
- **Branch:**
- **Commit:**
- **Intent:**
- **Files changed:**
- **Public API/ABI change:**
- **Shader/SBT behavior change:**
- **Legacy compatibility impact:**
- **Tests run:**
- **Platforms/backends:**
- **Artifacts/logs:**
- **Known limitations or follow-up:**
- **Paired commit/submodule pin:**

### Planning entry - 2026-09-02

- **Repository:** `kaizhangNV/falcor2` local checkout (state at planning time)
- **Branch:** `main` at planning time
- **Commit:** no implementation commit at planning time; see the final Falcor publication entry
- **Intent:** Repository survey and port planning only
- **Files changed:**
  - `reports/structural-rt-port-plan.md`
  - `reports/structural-rt-port-checklist.md`
  - `output/pdf/falcor-structural-rt-port-plan.pdf` (ignored viewing artifact; generated before the
    checklist was added and therefore not the authoritative current plan)
- **Public API/ABI change:** None
- **Shader/SBT behavior change:** None
- **Legacy compatibility impact:** None
- **Tests run:** Read-only source inspection; no native build or runtime test
- **Platforms/backends:** None
- **Known limitations or follow-up:** At planning time, the SlangPy fork and implementation branches
  had not yet been created; the later entries record their completion.
- **Paired commit/submodule pin:** None

### Compiler CUDA lowering entry - 2026-09-03

- **Repository:** `kaizhangNV/slang`
- **Branch:** `codex/structural-rt-cuda-hit-attributes`
- **Commit:** `7b2bf16a65406ad4fc5973b78c05bc044e57dc24`
- **Intent:** Canonicalize native hit-attribute parameters synthesized after the normal entry-point
  input pass so CUDA varying legalization receives valid borrow-in forms.
- **Files changed:**
  - `source/slang/slang-emit.cpp`
  - `tests/ray-tracing-2/target/portable/stage-input-hit-attributes.slang`
  - `tests/ray-tracing-2/target/portable/stage-input-triangle-data.slang`
- **Public API/ABI change:** None.
- **Shader/SBT behavior change:** Structural triangle/custom hit inputs now lower correctly to PTX;
  SBT layout is unchanged.
- **Legacy compatibility impact:** None intended; the extra canonicalization is gated on structural
  stage-input lowering.
- **Tests run:** Four added PTX FileCheck lanes; portable structural suite and the SlangPy CUDA
  runtime canary.
- **Platforms/backends:** Linux PTX/CUDA; later final-SHA farm runs cover all Phase 1 platforms.
- **Artifacts/logs:** Included in the final Linux and Windows farm logs below.
- **Known limitations or follow-up:** Procedural `reportHit` and structural `geometryIndex` CUDA
  lowering remain later LSS work.
- **Paired commit/submodule pin:** Included by final compiler commit `b035d437...` and validated
  together with SlangPy implementation `c2e73c0b...`.

### Compiler stage-name entry - 2026-09-03

- **Repository:** `kaizhangNV/slang`
- **Branch:** `codex/structural-rt-cuda-hit-attributes`
- **Commit:** `8bc787db46d61f3816528a5eb08709a379074d54`
- **Intent:** Make reflected structural-stage exports deterministic and target-safe, and preserve
  explicit component renames through portable adapter synthesis.
- **Files changed:**
  - `include/slang.h`
  - `source/slang/slang-check-shader.cpp`
  - `source/slang/slang-entry-point.cpp`
  - `source/slang/slang-entry-point.h`
  - `source/slang/slang-ir-synthesize-structural-ray-tracing.cpp`
  - `source/slang/slang-reflection-structural-ray-tracing.cpp`
  - `source/slang/slang-structural-ray-tracing.cpp`
  - `source/slang/slang-structural-ray-tracing.h`
  - `tools/slang-unit-test/unit-test-structural-ray-tracing-reflection.cpp`
- **Public API/ABI change:** No function signature change; the existing reflection getter's return
  value is clarified as the target-safe physical export name.
- **Shader/SBT behavior change:** Qualified/reserved/unsafe source names are encoded; safe simple
  names remain stable; explicit export renames survive adapter replacement.
- **Legacy compatibility impact:** Ordinary legacy entry-point names are unchanged.
- **Tests run:** Two focused unit tests and 78/78 portable structural target tests.
- **Platforms/backends:** Direct/portable DXIL, SPIR-V, PTX, and source targets; exercised by the
  Linux, Windows, and macOS final farm builds.
- **Artifacts/logs:** Included in the final farm logs below.
- **Known limitations or follow-up:** The physical-name identity does not encode declaring-module
  identity or native stage; same-FQN leaves are rejected by the host and one type reused for several
  native stages remains unsupported.
- **Paired commit/submodule pin:** Included by final compiler commit `b035d437...`; validated
  together with SlangPy `c2e73c0b...`.

### SlangPy/SGL host-bridge implementation entry - 2026-09-03

- **Repository:** `kaizhangNV/slangpy`
- **Branch:** `codex/structural-rt-host-bridge`
- **Commit:** `c2e73c0b1b0eed0577e544e6abdadfa1d32f7910`
- **Intent:** Add reusable structural layout reflection/materialization, adapt it to existing RHI
  pipeline/SBT descriptors, expose it through nanobind and SlangPy, and add a generated-raygen
  canary without changing Falcor renderer code.
- **Files changed:**
  - `.agents/execplans/structural-rt-host-bridge.md`
  - `slangpy/core/calldata.py`
  - `slangpy/core/function.py`
  - `slangpy/tests/slangpy_tests/test_raytracing.py`
  - `slangpy/tests/slangpy_tests/test_raytracing_config.py`
  - `slangpy/tests/slangpy_tests/test_raytracing_structural.slang`
  - `src/sgl/device/fwd.h`
  - `src/sgl/device/raytracing.cpp`
  - `src/sgl/device/raytracing.h`
  - `src/sgl/device/reflection.cpp`
  - `src/sgl/device/reflection.h`
  - `src/sgl/device/shader.cpp`
  - `src/sgl/device/shader.h`
  - `src/slangpy_ext/device/raytracing.cpp`
  - `src/slangpy_ext/device/reflection.cpp`
  - `src/slangpy_ext/device/shader.cpp`
  - `tests/CMakeLists.txt`
  - `tests/sgl/device/test_structural_raytracing.cpp`
- **Public API/ABI change:** Additive native `checked_entry_point`, structural reflection/binding
  values, nanobind exposure, and Python `trace_program_layout` option. Legacy signatures now include
  hit-group names, fixing an omitted cache-identity input.
- **Shader/SBT behavior change:** Structural groups map to their declared numeric slots, including
  holes/trailing records. Generated hit-group names reserve every stage export and `raygen_main` to
  avoid slang-rhi's shared-name-map collision.
- **Legacy compatibility impact:** Legacy arguments and dispatch remain available and pass on all
  tested backends; legacy/structural arguments are intentionally mutually exclusive per program.
- **Tests run:** Focused native bridge 131 assertions; all 197 native SGL tests in three bounded
  shards; 9/9 configuration tests; legacy and structural runtime canaries; generated nanobind stub;
  pre-commit; pyright; `git diff --check`.
- **Platforms/backends:** Linux Vulkan/CUDA; Windows D3D12/Vulkan/CUDA; macOS native/configuration
  build coverage. Final exact logs are listed in the Phase 0-1 validation entry.
- **Artifacts/logs:** Implementation commit on the fork; final worker logs listed below.
- **Known limitations or follow-up:** One layout per call; imported-only and generic stages are
  unsupported; same FQN across leaves is rejected; one type/multiple native stages is unsupported;
  non-empty records are rejected; runtime nonzero sparse-slot selection, actual multi-pipeline cache
  behavior, and structural hot reload are not yet tested; Metal runtime is absent.
- **Paired commit/submodule pin:** Compiler `b035d437...`; final Falcor gitlink follows the SlangPy
  documentation update.

### Compiler Metal Release termination entry - 2026-09-03

- **Repository:** `kaizhangNV/slang`
- **Branch:** `codex/structural-rt-cuda-hit-attributes`
- **Commit:** `b035d437be74e1ffb6c671c4e6630f07326e300b`
- **Intent:** Prevent Release compilers from erasing the side-effecting structural Metal adapter
  inlining operation.
- **Files changed:** `source/slang/slang-ir-metal-structural-ray-tracing.cpp`.
- **Public API/ABI change:** None.
- **Shader/SBT behavior change:** None intended; Metal raygen compilation now terminates and emits
  the code already produced by Debug/GCC builds.
- **Legacy compatibility impact:** None.
- **Tests run:** Exact Metal raygen `slangc` command, 1/1 focused fixture, 18/18 structural Metal
  tests, Linux final-SHA gate, and macOS ARM64 Release Metal/AIR generation.
- **Platforms/backends:** Linux compiler tests and macOS ARM64 Metal compilation.
- **Artifacts/logs:** macOS final run `20260902-185145`; closest-hit AIR 3,312 bytes, miss AIR 3,296
  bytes, raygen AIR 7,184 bytes.
- **Known limitations or follow-up:** Metal runtime remains outside Phase 1 because the pinned RHI
  lacks pipeline, shader-table/function-table, and `dispatchRays` support.
- **Paired commit/submodule pin:** Compiler dependency for SlangPy `c2e73c0b...` and its final
  documentation commit.

### Phase 0-1 acceptance validation entry - 2026-09-03

- **Validated source:** Slang
  `b035d437be74e1ffb6c671c4e6630f07326e300b` together with the SlangPy/SGL implementation
  `c2e73c0b1b0eed0577e544e6abdadfa1d32f7910`. Each worker verified the full Slang SHA before
  configuring SlangPy against that checkout's source, headers, and Release libraries. Fresh-worker
  `slangc -version` was `2024.0.7-3799-gb035d437b`; the full SHA is authoritative because visible
  tag sets change the descriptive version.
- **Canonical recipe:** external local-build-farm recipe
  `~/.codex/local-build-farm/projects/falcor2-structural-rt-phase1.json`. It is intentionally outside
  the repository; the command contract is reproduced below so the uploaded report is self-contained.
- **Configure/build command contract:** Clone the Slang fork's
  `codex/structural-rt-cuda-hit-attributes` branch, detach at the full SHA above, initialize its
  submodules, and build targets `slangc slang-glslang slang-glsl-module slang-raytracing-module` in
  Release. Configure SlangPy with
  `-DSGL_LOCAL_SLANG=ON -DSGL_LOCAL_SLANG_DIR=<Slang checkout>
  -DSGL_LOCAL_SLANG_BUILD_DIR=build/Release -DSGL_BUILD_EXAMPLES=OFF -DSGL_BUILD_TESTS=ON`, then
  build `slangpy_ext sgl_tests` in Debug. Linux executes configure, build, and test processes through
  `run-limited-build.sh`; its successful compiler build used `--parallel 4` after a GCC 13 ICE at
  eight jobs, while the SlangPy build used `--parallel 8`. macOS used `--parallel 8`. Windows used
  `--parallel 1`/`/m:1` around `/MP8` compiler invocations so at most eight compiler processes could
  exist at once.
- **Exact native/Python test shapes:** With `SGL_TESTS` set to the built test executable and
  `PYTHON` set to the worker virtual-environment interpreter, the workers ran:

      $SGL_TESTS --test-suite=hot_reload --no-colors=true
      $SGL_TESTS --test-suite=persistent_cache --no-colors=true
      $SGL_TESTS --test-suite-exclude=hot_reload,persistent_cache --no-colors=true
      $PYTHON -m pytest slangpy/tests/slangpy_tests/test_raytracing_config.py -v --device-types nodevice
      $PYTHON -m pytest \
        slangpy/tests/slangpy_tests/test_raytracing.py::test_raytracing \
        slangpy/tests/slangpy_tests/test_raytracing.py::test_structural_raytracing \
        -v --device-types <linux: vulkan,cuda | windows: d3d12,vulkan,cuda>
      $PYTHON -m pytest slangpy/tests/device/test_pipeline.py::test_raytrace_simple \
        -v -rs --device-types d3d12,vulkan,cuda

  The last command is the preserved Windows inline/pipeline control. A separate bounded local Linux
  invocation used `--device-types vulkan,cuda` and obtained the same CUDA RayQuery capability skip.
- **Exact macOS compiler fixture shape:** For each tuple
  `(TestClosestHit, closesthit)`, `(TestMiss, miss)`, and `(main, raygeneration)`, the worker ran:

      slangc tests/ray-tracing-2/target/metal/trace-miss-closest-hit.slang \
        -experimental-feature -entry <entry> -stage <stage> -target metal -o <output>.metal
      xcrun -sdk macosx metal -std=metal3.1 -c <output>.metal -o <output>.air
      test -s <output>.air

- **Linux result:** Final run `20260902-185955` passed native shards 13/13 (43 assertions), 9/9
  (145), and 175/175 (14,243), for 197/197 tests. Python configuration passed 9/9. Legacy plus
  structural runtime passed 4/4 on Vulkan/CUDA. Log:
  `/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase1/20260902-185955/linux.log`
  (SHA-256 `d050241437365f83b776f194f791eebb523f6bc44e7542672d21fc37234718a6`).
- **Windows result:** Final run `20260902-191209` passed native shards 13/13 (86 assertions), 9/9
  (145), and 175/175 (14,843), for 197/197 tests. Python configuration passed 9/9. Legacy plus
  structural runtime passed 6/6 on D3D12/Vulkan/CUDA. The inline control passed five cases and
  skipped only compute CUDA RayQuery because the device reports it unsupported: compute D3D12 and
  Vulkan passed; pipeline ray launch passed on D3D12, Vulkan, and CUDA. Log:
  `/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase1/20260902-191209/windows.log`
  (SHA-256 `a49fd88837e064afcdd8b12d8f8a8a1116964cd2852c5de512654621b867a941`).
- **macOS ARM64 result:** Final run `20260902-185145` passed native shards 13/13 (43 assertions),
  9/9 (137), and 175/175 (13,470), for 197/197 tests. Python configuration passed 9/9. The three
  compiler-owned structural Metal fixtures produced non-empty AIR; separately inspected worker
  artifacts measured 3,312 bytes (closest-hit), 3,296 bytes (miss), and 7,184 bytes (raygen). This
  is compiler-only evidence, not SlangPy runtime evidence. Log:
  `/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase1/20260902-185145/macos.log`
  (SHA-256 `600edf24f2e798dc6adfe875e9b6135292b5d5475b6df80be6f31f2f02e21b10`).
- **Preserved infrastructure evidence:** Linux run `20260902-185518` failed during a clean eight-job
  compiler build with a GCC 13 internal compiler error in unchanged `slang-ir-inline.cpp`; the same
  final source passed at four jobs in the accepted run above. Windows preliminary run
  `20260902-184830` established Visual Studio/SDK initialization and the worker-only build recipe
  adjustments. The final Windows snapshot removed the unconditional Crashpad dependency only from
  its disposable copied manifest, configured `SGL_ENABLE_CRASHPAD=OFF`, and reported
  `SGL_HAS_CRASHPAD: OFF`; no repository dependency was changed. The macOS Release-Clang hang was
  the assertion-side-effect compiler defect fixed by `b035d437...`, after which the final run
  completed.
- **Metric definition:** The legacy and structural canaries each compare four selected corner
  values with `numpy.allclose(..., atol=0.01)` and NumPy's default `rtol`. These results establish
  functional Phase 1 parity on supported runtime backends; they are not bit-exact, full-image, or
  performance measurements.

### SlangPy validation-documentation entry - 2026-09-03

- **Repository:** `kaizhangNV/slangpy`
- **Branch:** `codex/structural-rt-host-bridge`
- **Commit:** `28ee791bc4cb58b071e4d6c873b214dbc2d6a98c`
- **Intent:** Record final Linux, Windows, and macOS validation in the living ExecPlan and normalize
  four long expressions in the native bridge test with the repository's clang-format hook.
- **Files changed:**
  - `.agents/execplans/structural-rt-host-bridge.md`
  - `tests/sgl/device/test_structural_raytracing.cpp` (formatting only)
- **Public API/ABI change:** None.
- **Shader/SBT behavior change:** None; the C++ edits only join formatter-selected line wraps.
- **Legacy compatibility impact:** None.
- **Tests run:** `pre-commit run --all-files` and `git diff --check`; the semantic source is the
  implementation already exercised by the final worker matrix above.
- **Platforms/backends:** Documentation records Linux Vulkan/CUDA, Windows D3D12/Vulkan/CUDA, and
  macOS compile-only Metal evidence.
- **Artifacts/logs:** The Phase 0-1 acceptance entry above.
- **Known limitations or follow-up:** The first version still contained stale command placeholders;
  the next documentation-only commit makes the ExecPlan self-contained.
- **Paired commit/submodule pin:** Superseded as the final pin by `07aefdac...` below.

### SlangPy reproducible-ExecPlan entry - 2026-09-03

- **Repository:** `kaizhangNV/slangpy`
- **Branch:** `codex/structural-rt-host-bridge`
- **Commit:** `07aefdac0d3a729d1fcf1271232843409708a4b7`
- **Intent:** Replace remaining future-tense placeholders with exact bounded Linux commands,
  cross-platform run evidence, and the complete list of accepted Phase 1 limitations.
- **Files changed:** `.agents/execplans/structural-rt-host-bridge.md`.
- **Public API/ABI change:** None.
- **Shader/SBT behavior change:** None.
- **Legacy compatibility impact:** None.
- **Tests run:** `pre-commit run --all-files`, `pyright` (0 errors), and `git diff --check`.
- **Platforms/backends:** Documentation-only; records the already completed final worker matrix.
- **Artifacts/logs:** The Phase 0-1 acceptance entry above.
- **Known limitations or follow-up:** Falcor renderer porting begins in Phase 2; the bounded bridge
  limitations listed above remain explicit follow-ups.
- **Paired commit/submodule pin:** Superseded as the final pin by `3a0454c4...` below.

### SlangPy clean-environment instructions entry - 2026-09-03

- **Repository:** `kaizhangNV/slangpy`
- **Branch:** `codex/structural-rt-host-bridge`
- **Commit:** `3a0454c4e101522d323bf8545d251d99abf9d901`
- **Intent:** Make the final ExecPlan runnable from a clean environment by installing the complete
  development requirements and constraining dependency installation with the Linux process-tree
  limiter.
- **Files changed:** `.agents/execplans/structural-rt-host-bridge.md`.
- **Public API/ABI change:** None.
- **Shader/SBT behavior change:** None.
- **Legacy compatibility impact:** None.
- **Tests run:** `pre-commit run --all-files`, `pyright` (0 errors), and `git diff --check`.
- **Platforms/backends:** Documentation-only.
- **Artifacts/logs:** The Phase 0-1 acceptance entry above.
- **Known limitations or follow-up:** Falcor renderer porting begins in Phase 2.
- **Paired commit/submodule pin:** Superseded as the final pin by `aa8840bc...` below.

### SlangPy ExecPlan-closure entry - 2026-09-03

- **Repository:** `kaizhangNV/slangpy`
- **Branch:** `codex/structural-rt-host-bridge`
- **Commit:** `aa8840bc8ca644c45ea9d475f3f937b66faf8208`
- **Intent:** Close the final living-ExecPlan progress item after the initial Falcor publication.
- **Files changed:** `.agents/execplans/structural-rt-host-bridge.md`.
- **Public API/ABI change:** None.
- **Shader/SBT behavior change:** None.
- **Legacy compatibility impact:** None.
- **Tests run:** `pre-commit run --all-files`, `pyright` (0 errors), and `git diff --check`.
- **Platforms/backends:** Documentation-only.
- **Artifacts/logs:** Initial Falcor publication commit `7a37064f0aa04b7863152c4f4954be3ba8df00ff`.
- **Known limitations or follow-up:** Falcor renderer porting begins in Phase 2.
- **Paired commit/submodule pin:** This is the final Phase 0-1 SlangPy gitlink recorded by Falcor.

### Falcor Phase 0-1 publication entry - 2026-09-03

- **Repository:** `kaizhangNV/falcor2`
- **Branch:** `codex/structural-rt-port`
- **Commit:** `7a37064f0aa04b7863152c4f4954be3ba8df00ff`
- **Intent:** Publish the Phase 0-1 plan and complete change/validation ledger, point the SlangPy
  submodule URL at the writable fork, and pin the validated host bridge without modifying Falcor
  renderer source.
- **Files changed:**
  - `.gitmodules`
  - `external/slangpy` (gitlink)
  - `reports/structural-rt-port-plan.md`
  - `reports/structural-rt-port-checklist.md`
- **Public API/ABI change:** No Falcor API/ABI change. The pinned SlangPy submodule contains the
  additive bridge described in its implementation entry.
- **Shader/SBT behavior change:** No Falcor shader behavior change. The pinned bridge can adapt one
  reflected structural layout into existing RHI pipeline/SBT descriptors.
- **Legacy compatibility impact:** No Falcor runtime path changed; legacy and structural SlangPy
  canaries pass in the acceptance matrix.
- **Tests run:** The Phase 0-1 acceptance matrix above; `git diff --cached --check` before commit.
- **Platforms/backends:** Linux Vulkan/CUDA, Windows D3D12/Vulkan/CUDA, and macOS compiler-only
  Metal coverage.
- **Artifacts/logs:** The Phase 0-1 acceptance entry above and both checked-in Markdown reports.
- **Known limitations or follow-up:** Renderer source porting starts with MiniTracer in Phase 2.
- **Paired commit/submodule pin:** Initial publication pinned SlangPy `3a0454c4...`; the subsequent
  report/gitlink-only outer commit advances it to final ExecPlan revision `aa8840bc...`. Both use
  Slang `b035d437...` as the validated compiler dependency.
