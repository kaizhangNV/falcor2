# Falcor 2 Structural Pipeline Ray Tracing Port Plan

**Survey date:** 2026-09-02

**Last updated:** 2026-09-03 UTC

**Falcor fork:** `kaizhangNV/falcor2`, `main` at `046545b1d3dac23e9ba1a75498eb75f6c9280dfc`

**Original structural Slang baseline:** `b0f010593568239005df17c30ea875c0edf25049`

**Current compiler dependency through Phase 3:**
`036132fa8fbfbe2e9300a0e0edb46d0405d973d0` on
`kaizhangNV/slang:draft/unified-pipeline-rt-api`. It includes the CUDA late-input repair at
`7b2bf16a65406ad4fc5973b78c05bc044e57dc24`, target-safe stage names at
`8bc787db46d61f3816528a5eb08709a379074d54`, the Release-Clang Metal termination repair and its
regression at `b035d437be74e1ffb6c671c4e6630f07326e300b`/`e95ef5fbd549e43ef4a93502917975baf6a87848`,
generic structural stage-name consistency at `49facf2c3639d84dded49f4dfcc8d983adab904e`, and the
CUDA structural `geometryIndex` implementation and strengthened regression at
`6bf10cd992ba0e00233f67f8652b49b1fbba4e31`/`036132fa8fbfbe2e9300a0e0edb46d0405d973d0`.

**Phase 4 compiler dependency:**
`0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617`, pushed to
`kaizhangNV/slang:draft/unified-pipeline-rt-api`. It specializes functions referenced by structural
hit, miss, and callable group metadata as executable type-flow roots, including cases that use
external type conformances. The published paired revisions are SlangPy
`77205c2f3a5313c772d2df6c3cd19600887e938d` and Falcor
`12448a57d16a53009973d3ff7b3a31eff2095d74`.

**Status:** Phases 0-4 are implemented. The reusable SlangPy/SGL bridge passed its published
Linux/Windows runtime matrix and macOS compile matrix. MiniTracer runs legacy, structural, and
unchanged inline paths. At Falcor commit `bb92a32c09c26322a0eb474bd5031c0d4f65cd0f`, ScenePicker
and SelectionProbe also expose legacy/structural pipeline selection while preserving their inline
paths. The focused Phase 3 UI suite, including exact ID-map and mask gates, passes 5/5 on Linux
Vulkan and 5/5 on Linux CUDA/OptiX; the MiniTracer regression remains 2/2. The actual Phase 3 UI
shaders also reflect/materialize on Apple M4 Metal, and compiler-owned closest-hit/miss and any-hit
fixtures compile to AIR. The same UI suite passes 5/5 on Windows D3D12, Vulkan, and CUDA, and the
MiniTracer regression passes 3/3 there. The planned Phase 3 cross-platform gate and stop-for-review
boundary are satisfied. Phase 4 ReferencePathTracer is published at the paired revisions above and
passes its scoped acceptance matrix: Linux Vulkan runtime, Windows D3D12/Vulkan runtime, and macOS
Metal compile-only validation. The tested CUDA/OptiX device reported no inline RayQuery support, so
its ReferencePathTracer runtime cases skipped and were explicitly non-gating for this scope.

The living, cross-repository implementation and validation ledger is
[`structural-rt-port-checklist.md`](structural-rt-port-checklist.md). Checklist items are only marked
complete after their implementation commit and validation evidence have been recorded.

## Executive recommendation

Proceed in narrow renderer slices. MiniTracer, ScenePicker, SelectionProbe, and the bounded
ReferencePathTracer scatter port are implemented, published, and accepted across the scoped Phase 4
matrix. Keep legacy as the A/B control, and do not broaden this completed correctness slice into LSS,
SER, multi-payload pipeline visibility, Metal runtime, or performance benchmarking.

The structural pipeline portion is feasible for D3D12, Vulkan, and CUDA without redesigning the
low-level slang-rhi ray tracing pipeline or shader-table APIs. This ReferencePathTracer slice also
retains inline `RayQuery`, so its current CUDA runtime lane remains capability-constrained. SER can be
converted to the existing ordinary `TraceRay` scheduler, with an expected performance loss on
SER-capable hardware but no intended rendering-semantic change.

Metal runtime and full LSS support should be separate later workstreams because this Falcor snapshot
and the current stack intentionally lack those target/runtime extensions, as classified below.

## Phase 2 MiniTracer outcome

MiniTracer's shared renderer is now composed with exactly one pipeline implementation: the original
legacy stages or a structural `MiniTracerProgramLayout`. The inline `RayQuerySceneIntersector`
remains untouched. Selection is lazy and public through `Renderer.ray_tracing_pipeline_api`; plugin
modules are linked against that one selected root to avoid duplicate-component composition.

Precondition: a fresh checkout must first build Slang at
`49facf2c3639d84dded49f4dfcc8d983adab904e` and configure Falcor/SlangPy against that checkout; the
Falcor commits do not vendor a compiler binary. After building the four Slang Release targets
(`slangc`, `slang-glslang`, `slang-glsl-module`, and `slang-raytracing-module`), the Linux Falcor
configure/build shape is:

```text
LIMITER="/absolute/path/to/run-limited-build.sh"
SLANG_RT_DIR="/absolute/path/to/slang"

CMAKE_BUILD_PARALLEL_LEVEL=8 VCPKG_MAX_CONCURRENCY=8 MAX_JOBS=8 "$LIMITER" \
  cmake --preset linux-clang -S . -B build/linux-clang-structural \
  -DSGL_LOCAL_SLANG=ON -DSGL_LOCAL_SLANG_DIR:PATH="$SLANG_RT_DIR" \
  -DSGL_LOCAL_SLANG_BUILD_DIR=build/Release -DPython_ROOT_DIR:PATH="$PWD/.venv" \
  -DFALCOR_ENABLE_NGX=OFF

CMAKE_BUILD_PARALLEL_LEVEL=8 VCPKG_MAX_CONCURRENCY=8 MAX_JOBS=8 "$LIMITER" \
  cmake --build build/linux-clang-structural --config Release --parallel 8 \
  --target slangpy_ext falcor2_ext
```

The public sample can now be run headlessly for a direct A/B comparison from the repository root:

```text
PYTHONPATH="$PWD:$PWD/external/slangpy" .venv/bin/python examples/minitracer/basic.py \
  data/assets/kronos/Box/glTF-Binary/Box.glb --device vulkan \
  --pipeline-api legacy --headless --width 128 --height 128 --spp 4 \
  --output output/minitracer-legacy.png

PYTHONPATH="$PWD:$PWD/external/slangpy" .venv/bin/python examples/minitracer/basic.py \
  data/assets/kronos/Box/glTF-Binary/Box.glb --device vulkan \
  --pipeline-api structural --headless --width 128 --height 128 --spp 4 \
  --output output/minitracer-structural.png
```

Both commands completed locally and produced byte-identical RGBA PNGs. Replacing the selector with
`--pipeline-api inline` produced the same hash as an unchanged-control run. The regression test uses
a transparent blend occluder to exercise any-hit rejection as well as closest-hit and miss behavior;
legacy and structural float images had MSE `0.0` and maximum absolute difference `0.0` on Linux
Vulkan and CUDA/OptiX.

The final focused Linux parity rerun used the same capped test shape as the implementation gate:

```text
PYTHONPATH="$PWD:$PWD/external/slangpy" CMAKE_BUILD_PARALLEL_LEVEL=8 \
  CTEST_PARALLEL_LEVEL=8 MAX_JOBS=8 VCPKG_MAX_CONCURRENCY=8 "$LIMITER" \
  .venv/bin/python -m pytest tests/python/minitracer/test_structural_raytracing.py \
  -v -s --junitxml=/tmp/falcor2-phase2-linux-minitracer.xml
```

It passed 2/2 cases in 8.73 seconds. The JUnit artifact has SHA-256
`86f02ac9ff863f17373a28f856ef93ae2547e141133fc150cc84cdc4988a87af`.

Local-build-farm invocation `20260902-220241` created the Windows worker snapshot but stopped during
configuration because the snapshot omitted vcpkg Git metadata; its farm summary therefore records
a failure. The failed farm `windows.log` has SHA-256
`7d2cf25cb49f52ef34ae3c8bd6435d4b58696398ee6513329f5db6e7315fe344`. The same disposable checkout
was resumed manually, with the metadata restored at the exact pinned baseline and the unchanged
snapshot mapped to a short `R:` drive to stay within MSVC object-path limits. That continuation
built Falcor and SlangPy against compiler revision
`49facf2c3639d84dded49f4dfcc8d983adab904e`, then passed the focused test 3/3 on D3D12, Vulkan, and
CUDA in 23.27 seconds. The preserved successful-test console log
`/tmp/falcor2-phase2-windows-test.log` has SHA-256
`9185a273e763c8c44421ee3ccc8a636d20d97e972ed2137cdce48d9eeb5c6db4`; the JUnit XML has SHA-256
`c4ba9c603f0ff7e52c62cbf723924f35f06ac52582f7d9eba94e091823ecbeb5`. Neither worker accommodation
changed repository source. The build used `--parallel 8` and `/MP8`, and an independent process
monitor observed a peak of eight concurrent compiler/linker processes.

One compiler limitation is contained in the structural shader: compiling it as an explicit/modern
module currently triggers E36119 because the stage `invoke()` methods are diagnosed as lacking Metal
support even for Vulkan/CUDA. Both default-internal and explicitly public declarations fail in an
explicit module. The working form omits the explicit `module` declaration; legacy-module visibility
still preserves reflection and composition, and real dispatch passes. This is a compiler
capability-checking follow-up, not a MiniTracer payload/layout design gap.

## Phase 3 ScenePicker and SelectionProbe outcome

Falcor commit `bb92a32c09c26322a0eb474bd5031c0d4f65cd0f` adds
`SceneRayTracingSetup::create_structural()` as the scene-owned companion to the legacy constructor.
It reuses the SGL adapter, preserves Falcor's geometry-major slot convention, pads the current scene
policy to six hit-group and three miss records, and gives padding groups a collision-free synthesized
name. Structural setup rejects callable groups and scenes containing LSS because neither is supported
by this bounded triangle-only slice; the legacy path and its CUDA built-in LSS patch remain intact.
The new enum, structural factory, and UI selectors are exposed through `falcor2_ext`; the existing
setup inspection fields remain exposed, while the retained entry-point state is private. Adding that
private state changes the C++ object layout and the class is no longer usable as an aggregate, so
source/ABI consumers must rebuild even though the legacy factory remains available.

ScenePicker now has a structural closest-hit/miss layout and preserves legacy pipeline and, where
supported, inline controls. On Vulkan and CUDA, its structural closest-hit stage creates the same
complete `HitInfo` fields used by the legacy shader. Metal has no structural pipeline runtime in
this stack, and the full `make_triangle_hit_info()` helper currently fails its structural Metal
capability check, so the Metal compile-only branch populates only geometry type, geometry-instance
ID, and primitive index. That fallback is not claimed as full runtime parity. SelectionProbe now
has structural any-hit/miss stages that preserve ignore and accept/end-search behavior; its inline
`RayQuery` branch is unchanged.

The Linux Phase 3 gate rebuilt `falcor2_ext` against Slang
`036132fa8fbfbe2e9300a0e0edb46d0405d973d0`. One first Clang build attempt crashed transiently in
the allocator; retrying the same source with four jobs completed. The exact ScenePicker ID-map and
SelectionProbe binary-mask suite passed 5/5 on Vulkan and 5/5 on CUDA/OptiX. The unchanged MiniTracer
legacy/structural regression then passed 2/2. JUnit artifacts are
`/tmp/falcor2-phase3-linux-vulkan.xml` (SHA-256
`7f35e771c1a16a7b97813ad3b208b843e6ee83780b8a30df6515815c79f29a44`),
`/tmp/falcor2-phase3-linux-cuda.xml` (SHA-256
`b44a73d193a8b5099086954e142326417b018a88866f6838076e556248314999`), and
`/tmp/falcor2-phase3-linux-minitracer-regression.xml` (SHA-256
`56a88f4445f4d854ee8601436a7f47052984dc247170913d72edfaa95881fd32`). The optional broad
`falcor2_tests` target was also attempted, but pre-existing Clang alias-template CTAD errors in the
unchanged `test_scene.cpp`, `test_animation.cpp`, and `test_materials.cpp` prevent that target from
building; this is non-gating for the focused Phase 3 runtime proof.

On Apple M4, local-build-farm run `20260903-004845` built the underlying native Slang and SlangPy
stack, and focused retry `20260903-010242` validated the checksum-matched Phase 3 shader files.
After preloading `falcor2.render` to reproduce real Scene initialization order, both
`ScenePickerProgramLayout` and `SelectionProbeProgramLayout` reflected and materialized on Metal as
six hit records, three miss records, and two stages. Separate compiler-owned closest-hit/miss and
any-hit fixtures generated Metal and compiled through `xcrun` to AIR, with SHA-256
`6461897b54445a1b9abfc0f5e4ac4baa56ed88552b656f980d0247640f997eb1` and
`5609bceb8e4b6473eaa027d702c1439fe3399061b8ef9fa2d51b9b796eee5a4a`, respectively. The retry log
is
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase3-macos-retry/20260903-010242/macos-metal-validation-retry.log`
(SHA-256 `ff30e31f043091581bb869b709242e9348eca515a9dd8d1d950a170296b0bc3b`). An initial E40002 raw-load
failure was specific to the harness's module load order and disappeared with the production-order
preload. The full Falcor macOS build remains blocked by a pre-existing OpenUSD ARM64 failure, and no
Metal ray-tracing runtime result is claimed.

On Windows, capped native build run `20260903-004418` completed both extensions against Slang
`036132fa8fbfbe2e9300a0e0edb46d0405d973d0`; its disconnected wrapper ended before testing.
Checksum-verified test-only run `20260903-011707` then exercised the exact implementation snapshot.
The focused UI suite passed 5/5 on D3D12 in 12.53 seconds, 5/5 on Vulkan in 8.67 seconds, and 5/5
on CUDA in 11.71 seconds. The MiniTracer regression passed 3/3 across D3D12, Vulkan, and CUDA in
23.96 seconds. The preserved test log is
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase3-windows-tests2/20260903-011707/windows-tests2.log`
(SHA-256 `05117dc10a92ff7742d33f897ef9941269c45ac80ac247be1927773d661a4473`). The four JUnit hashes are
recorded in the checklist ledger.

The CUDA `geometryIndex` prerequisite is supplied by Slang commits
`6bf10cd992ba0e00233f67f8652b49b1fbba4e31` and
`036132fa8fbfbe2e9300a0e0edb46d0405d973d0`. It maps to `optixGetSbtGASIndex()`, which is equivalent
to the required Falcor geometry index only under the current Falcor/SGL invariant of one SBT record
per acceleration-structure build input and a null per-primitive SBT-offset buffer. This is not a
universal semantic equivalence for arbitrary OptiX host layouts.

## Phase 4 ReferencePathTracer implementation and scoped acceptance status

The published implementation keeps the common path-state, shading, guide-output, and render logic in
`reference_pathtracer.slang`, and moves pipeline-specific code into mutually exclusive
`reference_pathtracer_legacy.slang` and `reference_pathtracer_structural.slang` companions. The host
selects one companion lazily through `ReferencePathTracerNode.ray_tracing_pipeline_api`; legacy is
the default and remains the A/B control. The public sample gains the same legacy/structural selector
plus bounded frame, size, sample-count, depth, and output controls.

The structural companion defines `ScatterTraceContext` with `PathPayload`, a triangle closest-hit
group at real hit slot `0`, a miss group at real miss slot `0`, and no callable groups. The shared
simple scheduling loop invokes either a legacy or structural tracer implementation. Structural mode
does not use `HitObject::TraceRay`, `ReorderThread`, or `HitObject::Invoke`. A retained
`SchedulingMode.ser` request warns and maps to simple scheduling; actual SER is deferred.

Visibility remains the existing inline `RayQuery` route. A structural selection therefore requires
both experimental Slang features and the runtime RayQuery capability. A pipeline-visibility request
while structural scatter is selected warns and maps to inline visibility. This avoids composing the
scatter `PathPayload` and visibility `VisibilityPayload` routes into one physical structural
pipeline before that API design is approved. In particular, CUDA/OptiX Phase 4 runtime is not
covered on a device that reports RayQuery unavailable, even if its pipeline ray tracing works.

Phase 4 is triangle-only. `SceneRayTracingSetup::create_structural()` rejects scenes containing LSS,
so the six-entry hit array contains one real hit group at slot `0` and padding at slots `1..5`.
The three-entry miss array contains one real miss at slot `0` and empty padding at slots `1..2`.
There is no real structural LSS group at hit slot `3` in this phase.

SlangPy commit `77205c2f3a5313c772d2df6c3cd19600887e938d` adds the required structural minimum
SBT counts, one canonical composition containing generated prelude code, the selected base module,
and external conformances, composed-module type lookup, and two-phase hot reload that rebuilds
modules before registered entry points and linked programs. Falcor commit
`12448a57d16a53009973d3ff7b3a31eff2095d74` preserves separate scene-specialization cache state for
the two APIs and queries additive `StructuralRequirements` before dispatch, so the structural
adapter is materialized only once.

The first structural stage using local interface dynamic dispatch exposed a compiler pass-order
defect. Structural group-info decorations exist before the first specialization/type-flow pass, but
their invoke operands were not treated as executable roots. Unspecialized existential/witness work
then reached type legalization. Compiler commit
`0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617` on
`kaizhangNV/slang:draft/unified-pipeline-rt-api` roots entry-point-info and structural hit, miss, and
callable invoke functions for that pass and includes portable/external-conformance and Metal stage
regressions. The exact local compiler rerun passed all 3/3 portable and Metal cases.

The exact local Linux commands and results are in
[`structural-rt-phase4-reproduction.md`](structural-rt-phase4-reproduction.md). The Phase 4 Vulkan
suite passed 19/19, including color/guide/API-switch/padding coverage, and the published sample
produced matching legacy/structural captures. No Phase 4 runtime performance result is claimed here.

Falcor's host addition is a public `SceneRayTracingSetup::StructuralRequirements` value plus the
exported `get_structural_requirements()` query and its Python binding. This is an additive native
API/exported-symbol change; it does not alter the existing `SceneRayTracingSetup` object layout. The
query validates the scene policy and returns the minimum table counts and flags without reflecting or
materializing stages.

At the exact published tuple, the local Slang compiler regressions passed 3/3. SlangPy built 119/119;
the structural/layout-reload native shard passed 2/2 with 164 assertions, hot reload passed 13/13
with 43 assertions, persistent cache passed 9/9 with 145 assertions, configuration passed 13/13,
and generated-raygen/prelude reload passed 1/1. Falcor's production build completed 158/158 steps,
the Phase 4 Vulkan suite passed 19/19 in 8.53 seconds, and the focused UI regression passed 3/3 in
4.74 seconds. The optional broad `falcor2_tests` target remains blocked by the previously recorded
alias-template CTAD errors. The CUDA Phase 4 lane skipped 2/2 because this device reports RayQuery
unavailable; that is expected containment, not CUDA runtime coverage.

The Windows worker `DESKTOP-GUULUMF` built with no more than eight jobs and passed all 46/46 selected
tests at the exact tuple: 13 SlangPy configuration cases; 17 Falcor API/sample configuration cases;
one SlangPy structural generated-raygen/conformance/reload case on each of D3D12 and Vulkan; two
ReferencePathTracer parity/API-switch cases on each backend; and five Phase 3 UI non-regression cases
on each backend. Worker source validation reported 27 matching hashes. Vulkan emitted pre-existing,
non-gating VUID 08740/08742 diagnostics for unavailable NV sphere/LSS capabilities while all selected
tests passed.

The capped macOS worker built the matching compiler and SlangPy targets, passed the structural/layout
native shard (2/2 cases, 164 assertions) and full hot-reload suite (13/13 cases, 43 assertions), and
materialized the actual `ScatterProgramLayout` on Metal with one reflected hit, one reflected miss,
six physical hit slots, three physical miss slots, and zero callable slots. Direct compiler checks
passed 3/3 and produced three non-empty AIR files. This is compile/materialization evidence only; no
Metal runtime result is claimed.

Preserved worker evidence is under
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase4-windows-resume/20260903-phase4-windows-resume`
and
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase4-macos-resume/20260903-122722`.
The Windows log SHA-256 is
`9275c19d4982be8df86ff344068d05a751e5d001a38a2b5a4b46bef503bf4e2f`. The macOS layout JSON
SHA-256 is `987c6e8e182f7851c80e76b65173ef22ccf56dfd538ad45f7c9b3bad91e02343`; the dynamic-dispatch,
miss/closest-hit, and triangle/any-hit AIR hashes are respectively
`d5871a82b0398776ecf961696e659743add8458f805a79aadeea79c9d1a99e51`,
`bc286d0b499923cbfae9134601edbd15fd5868540fb99d7b64ed4ed03000d32a`, and
`7f70315d8148aa8aa6d6250b6d0bc699513d99d719aec0a47a992686f22c8efd`.

## Surveyed scope

Application-owned pipeline ray tracing is concentrated in four shader sites and one shared wrapper header:

| Area | Existing pipeline behavior | Initial disposition |
| --- | --- | --- |
| MiniTracer | One triangle hit group; miss, closest-hit, alpha any-hit; one `HitInfo` payload | First full renderer; port pipeline mode and retain its inline mode |
| ScenePicker | One ray type; miss and closest-hit; explicit raygen; pipeline currently used on CUDA | First `SceneRayTracingSetup` integration |
| SelectionProbe | One ray type; miss and any-hit with ignore/accept-and-end-search | Port after ScenePicker to exercise candidate control |
| ReferencePathTracer | Scatter pipeline, optional nested visibility pipeline, two payload types, and an SER path | Published Phase 4 ports scatter with simple scheduling and inline visibility; nested pipeline visibility remains deferred |
| `scene_ray_tracing.slangh` | Generates triangle, hardware-LSS, and procedural-LSS native stage wrappers | Replace only after triangle paths pass |

There are no application callable shaders, motion-ray paths, or non-empty shader-record payloads.

### Inline tracing to leave unchanged

- `slang/falcor2/render/intersector.slang`
- `slang/falcor2/minitracer/scene/intersector.slang`
- The compute/RayQuery branch of `slang/falcor2/ui/kernels/selection_probe.slang`

These paths should continue compiling and running as regression controls.

## SER conversion assessment

Converting SER to non-SER is possible.

All application SER is confined to `ReferencePathTracer`:

- `HitObject::TraceRay`
- the material coherence hint
- `ReorderThread`
- `HitObject::Invoke`

The same shader already contains a complete `SimpleScheduler` using ordinary `TraceRay`, and it is the default. Existing tests compare simple and SER output with `rtol=1e-4` and `atol=1e-5`.

Recommended migration:

- Remove the `ReorderingScheduler` from the structural variant.
- Route rendering through `SimpleScheduler` only.
- Temporarily retain the public numeric `SchedulingMode.ser` value as a deprecated alias to `simple`, with a clear warning, so saved configurations do not fail unexpectedly.
- Replace the SER-specific test with a compatibility test proving the deprecated setting selects the simple path.

Expected impact: material-coherence reordering disappears, so performance may regress on supported NVIDIA GPUs. No wave-dependent rendering semantics or cross-thread atomics were found in this path.

## Legacy and Phase 1 host architecture

### Legacy path

```text
host RayDesc strings
    -> name-generating [shader] macros
    -> findEntryPointByName plus manual hit/miss lists
    -> RayTracingPipeline and ShaderTable
```

### Phase 1 structural path (implemented and published)

```text
ITraceProgramLayout plus typed stages and declared slots
    -> Slang structural reflection
    -> one SGL stage-aware layout adapter
    -> existing RayTracingPipeline and ShaderTable
```

The original host gap was entry-point discovery, not slang-rhi. Legacy SGL resolves declared
`[shader]` functions with `IModule::findEntryPointByName()`, whereas structural stage structs must
be resolved using `findAndCheckEntryPoint(name, stage)`. The Phase 1 bridge snapshots
`findTraceProgramLayout()` reflection and materializes structural stages through a distinct checked
lookup path.

## Reusable host bridge

The published Phase 1 implementation provides the reusable bridge in SGL/SlangPy as follows:

1. **SGL structural reflection model**
   - Expose trace-layout type and context.
   - Copy each hit, miss, and callable group into lifetime-safe SGL-owned values instead of retaining
     raw Slang reflection handles.
   - Include the logical slot, fully qualified source type identity, deterministic reflected public
     entry-point name, and native stage for every synthesized stage.

2. **Stage-aware checked entry-point lookup**
   - Add the distinct native C++ method `SlangModule::checked_entry_point(name, stage,
     conformances)`. This is not an overload of `entry_point`, avoiding ambiguous source calls such
     as `entry_point(name, {})`.
   - Implement it using `IModule::findAndCheckEntryPoint()` and verify the materialized native stage.
   - Support concrete, non-generic stage types declared directly in exactly one enumerable SGL
     source-module leaf. Nested composed modules are flattened and duplicate leaves are ignored;
     zero matches fail with checked diagnostics, and multiple matching leaves are rejected as
     ambiguous.
   - Stage declarations reachable only through a Slang `import` are not supported unless their
     declaring module is also present as an enumerable SGL source-module leaf. Current reflection
     does not expose the declaring module. Generic structural stage types are also outside the
     Phase 1 materialization contract.

3. **Shared structural-layout adapter**
   - Validate negative and duplicate slots, preserve sparse slots, and reject non-empty shader-record
     types in the initial implementation.
   - Resolve by fully qualified reflected source type and stage, then rename the selected entry point
     to the compiler-reflected public name. This keeps materialization unambiguous while ensuring
     target compilation and shader-table lookup use the same deterministic symbol.
   - Produce existing `SlangEntryPoint`, `HitGroupDesc`, and sparse shader-table name arrays, with
     deterministic internal hit-group names derived from their numeric slots.
   - Support one structural layout per call. Multi-layout physical-pipeline composition remains
     deferred with the payload/layout design review.

4. **SlangPy integration**
   - Add `.ray_tracing(trace_program_layout="...")`, mutually exclusive with the retained legacy
     hit-group arguments and included in functional and pipeline cache identity.
   - Phase 4 extends the published structural form with `min_hit_group_count`, `min_miss_count`, and
     `min_callable_count` so a typed route can retain host-required trailing SBT records; all three
     values participate in cache identity.
   - Reuse the native adapter rather than reimplementing reflection in Python.
   - Keep existing generated `raygen_main`, parameter-block call data, pipeline caching, and
     `ShaderObject` binding.

Falcor C++ integration was not part of the Phase 1 bridge. Phase 2 composes structural MiniTracer
through that bridge without a new C++ API. Phase 3 adds a Falcor-owned
`SceneRayTracingSetup::create_structural()` companion which delegates structural materialization to
the same SGL adapter, then applies Falcor's geometry-major bounds and dummy-record policy. The CUDA
built-in LSS compatibility path remains legacy-only and unchanged; structural setup rejects LSS
until the later geometry workstream.

No fundamental slang-rhi API change is needed for the first D3D12, Vulkan, or CUDA ports. Its
existing pipeline and shader-table descriptors already consume the names and groups produced by
the Phase 1 adapter.

### SlangPy submodule ownership

The SGL/SlangPy implementation lives in the `external/slangpy` submodule on branch
`codex/structural-rt-host-bridge`. Its `origin` is `kaizhangNV/slangpy`, and
`shader-slang/slangpy` is retained as `upstream`. The source implementation is committed and
published as `c2e73c0b1b0eed0577e544e6abdadfa1d32f7910`. Validation documentation and a formatting-only
native-test normalization are in `28ee791bc4cb58b071e4d6c873b214dbc2d6a98c`; reproducible command
details were completed by `07aefdac0d3a729d1fcf1271232843409708a4b7` and
`3a0454c4e101522d323bf8545d251d99abf9d901`. Commit
`aa8840bc8ca644c45ea9d475f3f937b66faf8208` closes the ExecPlan after the first Falcor publication;
it is the final Falcor submodule revision for Phase 0-1.

SlangPy's repository instructions require a living ExecPlan for this feature. It is maintained at
`external/slangpy/.agents/execplans/structural-rt-host-bridge.md`; final commits, runner evidence,
and outcomes are recorded there and in Falcor's implementation ledger.

This is a pipeline-assembly change, not a new D3D12/Vulkan/CUDA dispatch-time resource binding.
The Phase 1 SlangPy path reflects the structural layout and resolves synthesized stages by
`(name, stage)` before linking. Existing generated `raygen_main`, call-data marshalling, root
`ShaderObject` writes, pipeline creation, and shader-table binding remain in place. Metal eventually
requires physical `TraceProgramDescriptor` resource binding, but that belongs to the separate Metal
runtime workstream.

### Required compiler implementation fixes

Phases 1-3 exposed five fixed compiler implementation defects, and Phase 4 exposed a sixth compiler
specialization-root defect with a pushed repair. One explicit-module capability-checking defect
remains contained and unresolved. None changes the structural shader API:

- Commit `7b2bf16a65406ad4fc5973b78c05bc044e57dc24` fixes CUDA/PTX lowering for late-synthesized
  structural stage inputs. Portable structural materialization could introduce triangle or custom
  hit-attribute parameters after normal entry-point input canonicalization, leaving CUDA varying
  legalization with invalid pointer forms. The fix reruns the canonical input translation after
  structural lowering.
- Commit `8bc787db46d61f3816528a5eb08709a379074d54` gives every structural stage a deterministic reflected public
  entry-point name that is also a legal target symbol. Simple source identifiers remain unchanged;
  qualified or otherwise target-unsafe names are encoded under a compiler-reserved prefix. Portable
  adapter synthesis also preserves a selected entry point's `renameEntryPoint()` physical-name
  decoration instead of reconstructing it from the qualified source type name. This prevents
  namespaced stages from leaking dotted names into CUDA and other C-like target symbols.
- Commit `b035d437be74e1ffb6c671c4e6630f07326e300b` fixes a Release-Clang non-termination in Metal
  structural raygen lowering. `inlineCall()` was inside `SLANG_ASSERT`, so Clang's Release
  `__builtin_assume` erased the required mutation and the fixed-point loop rediscovered the same
  call indefinitely. The fix evaluates `inlineCall()` unconditionally and asserts its result;
  `e95ef5fbd549e43ef4a93502917975baf6a87848` adds the Release regression.
- Commit `49facf2c3639d84dded49f4dfcc8d983adab904e` makes generic structural stage names consistent.
  AST type strings included substitutions such as `<uint>`, while IR name hints used the source
  declaration identity. A shared substitution-free declaration path now drives reflection and
  synthesized target symbols.
- Commit `6bf10cd992ba0e00233f67f8652b49b1fbba4e31` implements structural `geometryIndex` on CUDA by
  mapping it to `optixGetSbtGASIndex()`; `036132fa8fbfbe2e9300a0e0edb46d0405d973d0` strengthens
  the CUDA/PTX regression. The mapping is correct for Falcor/SGL's current one-SBT-record-per-build-
  input and null-offset-buffer layout, but is not a general equivalence for arbitrary OptiX SBT
  offset arrangements.
- Commit `0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617` treats functions referenced by entry-point-info and
  structural hit, miss, and callable group decorations as executable roots during the first
  specialization/type-flow pass. This specializes interface/existential dispatch inside synthesized
  structural stages while retaining the final linked program and its external conformances as the
  lookup context. The commit is pushed to `kaizhangNV/slang:draft/unified-pipeline-rt-api`; exact
  paired-pin validation passes across the scoped Linux, Windows, and macOS matrix.

## Deferred design issue: ReferencePathTracer pipeline visibility

ReferencePathTracer uses `PathPayload` for scatter rays and `VisibilityPayload` for visibility rays
inside one physical native pipeline. The current structural API assigns one payload type to each
`ITraceProgramLayout`. Whether one physical layout should instead contain several typed routes, or
whether several typed layouts should compose into one physical pipeline, is an API-design decision.

**Decision for the initial port:** defer that design issue. Do not add a union payload, multi-layout
host merge, payload-only `RayTracer` generic, or new route/aggregate API as part of the first port.
Port only the scatter path with `PathPayload` and `SimpleScheduler`, and keep visibility on the
existing inline `RayQuery` path. Nested pipeline visibility remains out of scope until the API model
is revisited. Any public configuration that requests structural pipeline visibility must either be
rejected clearly or deliberately mapped to inline visibility; record that compatibility choice in
the implementation ledger.

The investigation so far remains useful for that later review. A temporary shader with one raygen
invoking two differently typed layouts compiled successfully to DXIL and directly emitted SPIR-V,
so basic shader-language expressiveness is present. The unresolved questions are the public model,
host/reflection aggregation, runtime SBT composition, and Metal's payload-typed tables.

## Correctness invariant: preservation of Falcor's numeric SBT indices

Structural `HitGroupSlot<N>`, `MissSlot<N>`, and `CallableSlot<N>` values are actual logical dispatch
indices, not labels or positions in declaration order. Falcor's current scene policy reserves three
ray types across two geometry types and computes each hit slot as:

```text
slot = geometry_type * 3 + ray_type
```

The full legacy ReferencePathTracer mapping is:

```text
Hit slots                         Miss slots
0 = triangle / scatter           0 = scatter
1 = triangle / visibility        1 = visibility
2 = triangle / reserved          2 = reserved
3 = LSS / scatter
4 = LSS / visibility
5 = LSS / reserved
```

The full mapping above documents the legacy ABI, not the implemented Phase 4 structural group set.
Phase 4 deliberately rejects every scene containing LSS. Its structural scatter route therefore has
one real hit group at slot `0` and one real miss at slot `0`; hit records `1..5` and miss records
`1..2` are padding. Slot `3` must not be described or tested as a real LSS scatter group until
structural LSS support is implemented and the scene rejection is removed.

The SGL adapter must place every reflected real group at its explicit numeric `.slot`, preserve holes
and requested trailing records, and never use reflection enumeration order as the SBT index. For
the triangle-only Phase 4 layout, minimum counts retain the six-hit/three-miss physical bounds while
collision-free dummy hit names fill hit slots `1..5` and empty miss names fill miss slots `1..2`.
A later LSS implementation must restore its real groups at legacy-compatible slots `3..5`, not
compact them into earlier padding slots.

Slang diagnoses negative and duplicate slots inside one structural layout. It cannot verify the
end-to-end agreement among Falcor's TLAS instance contribution, runtime `sbtOffset`/`sbtStride`/
`missIndex`, and the host-created shader-table arrays. A mismatch can therefore compile successfully
but invoke the wrong group, select a dummy/out-of-range record, or fail only on one geometry type.

This is an inherited host/shader ABI invariant, not a new structural ray-tracing API design gap.
Validate it with exact array assertions, reversed declaration-order tests, and sentinel shaders that
uniquely identify every exercised ray-type/geometry-type and miss slot.

## Phased implementation plan

### Phase 0 - Reproducible baseline

- **Completed:** initialized the remaining top-level submodules and established the original
  structural Slang baseline at `b0f010593568239005df17c30ea875c0edf25049`.
- **Completed:** configured SGL/SlangPy against matching compiler source, headers, and
  libraries, enabled Slang experimental features for affected device sessions, and preserved the
  unchanged legacy ray-tracing path as the baseline.
- **Completed:** validated the exact effective compiler dependency on Linux, Windows, and macOS
  workers and recorded the compiler identity, bounded build/test commands, outcomes, and log paths.
- **Phase 2+ precondition:** capture legacy images or ID buffers before changing each Falcor sample.
- Compile exactly one pipeline RT API variant per program because legacy and structural API mixing
  is diagnosed.

Exit gate: compiler identity is logged on each worker and unchanged device/import smoke tests pass.

### Phase 1 - Host bridge and minimal canary

- **Implemented and published:** lifetime-safe reflection snapshots; the distinct native
  `checked_entry_point` method; concrete, non-generic, direct-leaf stage materialization with nested
  composition and ambiguity handling; and one-layout sparse-slot conversion.
- **Implemented and published:** SlangPy's `trace_program_layout` option, cache identity, focused native
  and Python coverage, and a SlangPy-owned generated-raygen triangle canary under
  `external/slangpy`.
- **Implemented and published in the compiler fork:** CUDA late-input lowering, target-safe
  deterministic public symbols for structural stages, and Release-Clang Metal termination.
- **Validated:** final-SHA Linux Vulkan/CUDA and Windows D3D12/Vulkan/CUDA runtime gates pass.
  macOS passes native/configuration coverage and the separate compiler-owned Metal-to-AIR fixture;
  Metal runtime remains unavailable in the pinned RHI.

Exit gate: compile/link succeeds and the four specified corner values match under
`numpy.allclose(..., atol=0.01)` with NumPy's default `rtol` on D3D12, Vulkan, and CUDA where
available. Compile-only Metal coverage uses Slang's compiler-owned structural
raygen/closest-hit/miss fixture and is recorded separately; it is not a SlangPy runtime result.

### Phase 0-1 validation report

Every acceptance worker checked out and built Slang
`b035d437be74e1ffb6c671c4e6630f07326e300b`, then configured SlangPy against that checkout's
matching source, headers, and Release libraries. Fresh-worker `slangc -version` reported
`2024.0.7-3799-gb035d437b`. Native tests were deliberately split into hot-reload,
persistent-cache, and remaining-suite processes to isolate the pre-existing cache-test stall. The
canonical commands and platform-specific build clamps are recorded in the external local-build-farm
recipe `~/.codex/local-build-farm/projects/falcor2-structural-rt-phase1.json`; the checked-in
checklist records the reproducible command shapes and preserved log hashes.

- **Linux, final run `20260902-185955`:** 197/197 native tests passed in three shards (13, 9, 175),
  9/9 Python configuration tests passed, and 4/4 legacy-plus-structural canary cases passed on
  Vulkan and CUDA. A separate bounded local inline control passed Vulkan compute RayQuery and
  Vulkan/CUDA pipeline launch; CUDA compute RayQuery skipped because the device reports it
  unsupported. A clean eight-job compiler attempt (`20260902-185518`) hit a GCC 13 internal
  compiler error in unchanged `slang-ir-inline.cpp`; the identical source passed when the compiler
  build was retried at four jobs, while all other native work remained capped at eight.
- **Windows, final run `20260902-191209`:** 197/197 native tests passed in the same three shards,
  9/9 configuration tests passed, and 6/6 legacy-plus-structural canary cases passed on D3D12,
  Vulkan, and CUDA. The inline control passed compute RayQuery on D3D12/Vulkan, skipped CUDA as
  unsupported, and passed pipeline launch on all three backends. The worker used one outer MSBuild
  project with `/MP8`; Crashpad was disabled and removed only from the disposable worker manifest.
- **macOS ARM64, final run `20260902-185145`:** 197/197 native tests and 9/9 configuration tests
  passed. Slang's compiler-owned structural closest-hit, miss, and raygen fixture generated Metal
  and compiled to non-empty AIR (3,312, 3,296, and 7,184 bytes respectively). This is compiler
  coverage, not SlangPy runtime coverage; the pinned Metal RHI has no ray-tracing pipeline/SBT/
  dispatch path.

The Phase 1 canary metric is functional agreement at four selected pixels under
`numpy.allclose(..., atol=0.01)` with NumPy's default relative tolerance. It is not a bit-exact image
comparison, a full-frame image metric, or a performance measurement. Phase 2 adds the full-frame
MiniTracer comparison recorded below.

### Phase 2 - MiniTracer pipeline

- **Status:** complete at Falcor commit `cb73af277afdca68ac082871bfcdb5ceb6800ae8`.
- Ported its single `HitInfo` trace context and slot-zero hit/miss groups.
- Converted miss, closest-hit, and alpha any-hit stages while retaining the legacy stages as an
  explicit A/B control.
- Kept `RayQuerySceneIntersector` unchanged and ran the inline sample as a control.
- Exercised SlangPy-generated raygen linking, reflection, plugin composition, and dispatch.

Exit gate: passed on Linux Vulkan and CUDA/OptiX and Windows D3D12/Vulkan/CUDA. The Linux same-run
complete 32x32 float images measured MSE `0.0` and maximum absolute difference `0.0`; all three
Windows cases passed the same `0.001` MSE threshold. Public Vulkan sample PNGs were byte-identical.

### Phase 3 - Falcor scene binding

- **Status:** implemented at Falcor commit `bb92a32c09c26322a0eb474bd5031c0d4f65cd0f`;
  Linux and Windows runtime gates plus the macOS compile-only gate pass.
- Added the structural `SceneRayTracingSetup` companion while retaining the legacy setup path.
- Ported ScenePicker on a triangle-only two-geometry scene and compared the complete picked-ID map.
- Ported SelectionProbe and compared complete masks for ignore and accept/end-search behavior
  against legacy on Linux Vulkan/CUDA and Windows D3D12/Vulkan/CUDA, and against the unchanged
  inline control on Vulkan and D3D12 (CUDA RayQuery is unavailable).
- Retained six-hit/three-miss geometry-major padding, rejected structural callables and LSS, and left
  all-slot sentinel coverage for the later full scene-stage migration.

Linux runtime exit gate: passed 5/5 on Vulkan and 5/5 on CUDA/OptiX. The macOS compile-only gate
also passes for both real layouts and compiler-owned Metal-to-AIR fixtures. Windows runtime passes
5/5 on each of D3D12, Vulkan, and CUDA, with the MiniTracer regression passing 3/3.

**Review boundary:** the planned Phase 3 cross-platform gate is complete and the review was
satisfied. Phase 4 is published and its scoped Linux Vulkan, Windows D3D12/Vulkan, and macOS
compile-only acceptance matrix is also complete.

### Phase 4 - Reference scatter path

- **Status:** published at Falcor `12448a57d16a53009973d3ff7b3a31eff2095d74`, SlangPy
  `77205c2f3a5313c772d2df6c3cd19600887e938d`, and Slang
  `0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617`; the scoped acceptance matrix passes on Linux Vulkan,
  Windows D3D12/Vulkan, and macOS Metal compile/materialization.
- Split legacy and structural stage companions while sharing path-state, shading, guide, and render
  logic.
- Port triangle scatter handlers and `ScatterProgramLayout` with `PathPayload`, real hit slot `0`,
  real miss slot `0`, and six-hit/three-miss padded host bounds.
- Use `SimpleScheduler` only. Retain `SchedulingMode.ser` as a warning compatibility alias to simple,
  but do not claim SER execution.
- Keep visibility on the existing inline RayQuery path. Map a structural pipeline-visibility request
  to inline with a warning and reject structural selection when RayQuery is unavailable.
- Add and pin SlangPy/SGL support for minimum physical table counts, canonical generated/base-module
  composition, external conformances, and two-phase hot reload.
- Preserve separate per-API scene-specialization caches and materialize the structural adapter once
  per built dispatch.
- Validate finite, non-zero color, legacy/structural color and guide parity, mode switching, exact
  padding, sample arguments, conformance resolution, and hot reload.

Exit gate: output is finite/non-zero and agrees with the legacy simple scheduler.
The runtime gate passes on Linux Vulkan and Windows D3D12/Vulkan. The macOS compile/materialization
gate also passes. CUDA ReferencePathTracer runtime is not covered because inline RayQuery is
unavailable there; that capability-constrained lane is non-gating for this scoped acceptance.

### Deferred phase - Second payload and nested pipeline visibility

- Revisit whether payload belongs to a typed logical layout, a trace route, or `RayTracer`.
- Define how several payload-typed routes map to one physical pipeline/SBT and to Metal tables.
- Only after design approval, add structural pipeline visibility and its host/runtime support.

Re-entry gate: approve the API design and explicit cross-backend composition contract before
implementation. The later runtime exit gate remains agreement between inline and pipeline
visibility at `rtol=1e-4`, `atol=1e-5`.

### Later phase - Geometry and backend expansion

- Add first-class hardware-LSS primitive support.
- Add a structural CUDA implementation for procedural `reportHit`.
- Retain the existing CUDA-compatible geometry-index implementation under its documented
  one-record-per-build-input/null-offset-buffer invariant; revisit semantics if that host layout
  changes.
- Port procedural and hardware LSS.
- Design and implement Metal runtime binding.
- Run targeted native and Python tests, then the broad suites.

### Deferred performance benchmarking

Phase 4 is a correctness port, not a runtime performance result. The interactive sample's live frame
rate is observational and must not be used as the benchmark metric. After exact compiler, SlangPy,
Falcor, driver, device, scene, resolution, sample count, and depth are pinned, benchmark legacy and
structural scatter with identical settings, warm-up, repeated runs, and GPU-side frame timing. Keep
shader compilation, native pipeline/SBT creation, first-frame warm-up, and steady-state frame time as
separate metrics. Report distributions rather than a single frame and retain the raw data. SER, LSS,
pipeline visibility, and Metal runtime comparisons remain separate experiments.

## Cross-platform validation matrix

| Runner | Initial lanes | Initial scope |
| --- | --- | --- |
| Windows | D3D12 primary; Vulkan secondary; CUDA/OptiX when supported | Runtime phases 1-3; Phase 4 D3D12/Vulkan |
| Linux | Vulkan primary; CUDA/OptiX secondary | Runtime phases 1-3; Phase 4 Vulkan, plus CUDA capability probe |
| macOS | Structural shader compilation and Metal code generation | Compile-only initially |

Metal runtime is not an immediate Falcor target: the pinned slang-rhi Metal backend does not implement ray tracing pipeline creation, shader tables, or `dispatchRays`. The structural compiler can still be validated for Metal code generation. Runtime support requires a separate function-table and dispatch integration.

ReferencePathTracer Phase 4 additionally requires inline `RayQuery` visibility. On CUDA/OptiX, a
reported lack of `Feature.ray_query` means the structural ReferencePathTracer lane must skip or fail
with its documented capability diagnostic; successful CUDA pipeline-ray canaries from earlier phases
do not establish Phase 4 runtime support. This unavailable-capability lane is explicitly non-gating
for the completed Phase 4 scope.

## Gap and risk classification

Not every port risk indicates a problem in the new ray-tracing API. The classification below is the
authoritative taxonomy for this plan.

### Structural ray-tracing design questions and intentionally deferred extensions

- **Multiple payload types in one physical pipeline:** this is an open API-design question. One
  `ITraceProgramLayout` has one trace context and therefore one payload type. Two typed layouts can
  compile in one shader, but there is no approved public contract for combining their routes, slots,
  reflection, and Metal tables into one physical pipeline/SBT. This is explicitly deferred; the
  initial ReferencePathTracer port uses structural scatter and inline visibility.
- **Native hardware LSS support:** this is an intentionally deferred primitive extension, not an
  architectural design gap for this port. The sealed structural primitive set currently contains
  triangle, Metal curve, and custom bounding-box primitives. Hardware LSS can be added later in the
  same general manner as another built-in primitive, together with its data interface, capability,
  reflection classification, and target lowering. Use triangle-only initial scenes and do not claim
  native-LSS coverage until that extension is implemented.
- **Structural SER:** this is an intentionally deferred version-one feature extension, not an active blocker
  for this port. Legacy `HitObject` operations can coexist with structural tracing, but there is no
  typed structural model for the complete trace, reorder, and deferred-invoke flow. The initial port
  deliberately uses `SimpleScheduler`; preserving SER would be a later API-design workstream.
- **Host-facing stage materialization scope:** the Phase 1 host bridge supports concrete,
  non-generic stages declared directly in one enumerable SGL source-module leaf. It recursively
  flattens nested compositions, deduplicates repeated leaves, and rejects multiple matching leaves
  as ambiguous. This is sufficient for the controlled initial module graph without a new public
  compiler API. Imported-only declarations remain unsupported because structural reflection does
  not expose their declaring module, and generic structural stage types remain unsupported. If a
  later Falcor port requires either case, revisit direct compiler materialization or declaration-
  identity reflection instead of broadening host lookup heuristics.

For the initial triangle, non-SER phases, no unresolved structural shader-API decision blocks
implementation. Multi-payload physical composition is the one known shader-model design question
and is outside that initial scope. Hardware LSS and SER are intentionally unsupported extensions.
Imported-only and generic stage materialization are known host/compiler integration limitations,
not blockers for the direct concrete stage declarations used by the Phase 1 canary.

The design also lists `intersection_function_buffer` and its `user_data` as future version-one
exclusions. The surveyed Falcor shaders do not use them, so they are not risks for this port.

### Compiler, standard-library, or target-lowering gaps

- **Late structural stage inputs on CUDA:** the required target-lowering repair is present in
  `7b2bf16a65406ad4fc5973b78c05bc044e57dc24`. It reruns canonical entry-point input translation
  after portable structural lowering so late triangle and custom hit-attribute parameters reach
  CUDA varying legalization in the expected form.
- **Namespaced structural target symbols:** the target-safe naming repair is published as
  `8bc787db46d61f3816528a5eb08709a379074d54`. Reflection and automatic trace-discovered synthesis derive the same
  deterministic legal public symbol from a source stage type, and selected adapter synthesis
  preserves explicit `renameEntryPoint()` names. This is a compiler materialization defect, not a
  shader API design gap.
- **Metal Release adapter inlining:** the side-effecting assertion bug described above is fixed in
  `b035d437be74e1ffb6c671c4e6630f07326e300b`, covered by `e95ef5fbd...`, and validated by ARM64
  Release Metal/AIR generation. This was a compiler implementation defect, not inefficient
  generated code or an API-design gap.
- **Generic structural target symbols:** reflection and IR previously disagreed because only the AST
  spelling included generic substitutions. `49facf2c3639d84dded49f4dfcc8d983adab904e` unifies them on
  a substitution-free declaration path and adds regression coverage. This fixes target symbol
  consistency; it does not broaden Phase 1 SlangPy's intentionally bounded non-generic host
  materialization contract.
- **Structural-stage dynamic-dispatch specialization:** structural group-info decorations are present
  before the first specialization/type-flow pass, but their invoke functions were not previously
  treated as executable roots. Interface existential/witness operations could consequently survive
  until type legalization. Pushed compiler commit
  `0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617` roots entry-point-info and structural hit, miss, and
  callable invoke operands and covers portable external-conformance and Metal stage cases. This is a
  compiler pass-root defect, not a payload or layout design gap. The exact published tuple passes the
  scoped Linux/Windows runtime and macOS compile/materialization gates.
- **Explicit-module structural capability check:** MiniTracer and the Phase 3 UI stages diagnose
  E36119 (`invoke` missing Metal support) during raw load as explicit/modern modules, even for
  Vulkan/CUDA. Both default-internal and explicitly public declarations fail in an explicit module.
  Omitting the explicit `module` declaration works because legacy-module visibility keeps the
  declarations available to structural reflection; composition and dispatch succeed. Keep that
  form until the compiler's cross-target checking is narrowed or the stage capability inference is
  corrected.

- **Procedural LSS `reportHit` on CUDA:** `IntersectionInput.reportHit()` already supplies the public
  shader API, but its target switch has no CUDA/OptiX lowering. Keep Falcor's direct
  `ReportHitOptix` compatibility path until the CUDA implementation and tests exist.
- **Geometry index on CUDA:** commits `6bf10cd992ba0e00233f67f8652b49b1fbba4e31` and
  `036132fa8fbfbe2e9300a0e0edb46d0405d973d0` implement and test structural `geometryIndex` through
  `optixGetSbtGASIndex()`. This supplies the Phase 3 triangle path under Falcor/SGL's invariant that
  each acceleration-structure build input has one SBT record and the per-primitive SBT-offset buffer
  is null. It is not a universal semantic equivalence for arbitrary OptiX host layouts; changing that
  invariant requires a separate semantics review.

### Host integration and RHI/runtime gaps

- **SlangPy generated raygen:** the one-layout SGL reflection adapter, structural cache identity,
  generated-module link, and SlangPy-owned `raygen_main` canary are published. The supported
  stage-materialization scope is the direct concrete non-generic leaf case described above. The
  Phase 4 implementation additionally composes generated prelude code with the base program before
  reflection/materialization and rebuilds composed entry points in a second hot-reload phase; that
  extension is published in SlangPy `77205c2f3a5313c772d2df6c3cd19600887e938d` and validated across
  the scoped acceptance matrix through generated-raygen/prelude reload and native hot-reload tests.
- **Metal pipeline ray tracing:** structural Metal code generation can be tested, but the pinned
  Metal RHI does not implement ray-tracing pipeline creation, shader tables, or `dispatchRays`.
  Treat runtime support as a separate RHI/function-table integration workstream.

### Correctness, test-infrastructure, and dependency risks

- **Exact SBT slot identity:** this is the inherited host/shader ABI invariant documented above, not
  an API gap. Enforce it with sparse-array assertions and sentinel shaders.
- **Private golden-image storage:** local runners may not be able to fetch the S3 references. Capture
  same-run legacy and structural image pairs as the fallback.
- **Experimental compiler ABI drift:** Slang headers, SGL, and the loaded library can diverge. Pin and
  log one compiler commit and rebuild SGL against it.
- **Descriptive version drift:** the fork's tag set and the local upstream tag set describe the same
  Phase 0-1 acceptance SHA differently (`2024.0.7-3799-gb035d437b` from fresh-worker
  `slangc -version` versus `v2026.16-93-gb035d437b` from local `git describe`). The full commit SHA
  is authoritative; every worker validates it before building SGL against the matching source,
  headers, and libraries.
- **GCC 11.5 Release LTO failure:** the local optimized SlangPy build encounters a baseline GCC
  internal compiler error in `lto1`/`sched2`; the Phase 1 local implementation build therefore uses
  Debug. Treat this as a toolchain/build-configuration issue, not evidence of a structural
  ray-tracing defect, and do not claim GCC 11.5 Release/LTO validation until a separate workaround
  or compiler version is used.
- **GCC 13 clean-build ICE:** one eight-job Linux worker build crashed in GCC while compiling the
  unchanged `slang-ir-inline.cpp`. The preserved failed run is `20260902-185518`; the same Phase 0-1
  acceptance SHA rebuilt cleanly at four jobs in run `20260902-185955`. This is treated as host
  compiler pressure, not source-test evidence.

## Build safety

Falcor's current `tools/build.py` and `setup.py` issue uncapped `cmake --build` commands and must not be run unchanged.

Every native configure, build, rebuild, or test will use no more than eight jobs:

- `CMAKE_BUILD_PARALLEL_LEVEL=8`
- the build tool's explicit cap, such as `--parallel 8`, `-j8`, or a lower platform equivalent
- the Linux descendant-process limiter
- the same hard maximum of eight total compiler jobs on Windows and macOS workers

## Primary source anchors

- Structural compiler PR: <https://github.com/shader-slang/slang/pull/12691>
- Structural design proposal: <https://github.com/shader-slang/spec/pull/59>
- Falcor fork: <https://github.com/kaizhangNV/falcor2>
- `src/falcor2/render/ray_tracing_setup.cpp`
- `src/falcor2/render/ray_tracing_setup.h`
- `src/falcor2_ext/render/ray_tracing_setup.cpp`
- `tests/native/render/test_scene.cpp`
- `external/slangpy/slangpy/core/calldata.py`
- `external/slangpy/src/sgl/device/shader.cpp`
- `slang/falcor2/ui/kernels/scene_picker_structural.slang`
- `slang/falcor2/ui/kernels/selection_probe_structural.slang`
- `tests/python/ui/test_scene_picker.py`
- `tests/python/ui/test_selection_overlay.py`
- `slang/falcor2/minitracer/renderers/simplepathtracer.slang`
- `slang/falcor2/rendernodes/reference_pathtracer.slang`
- `slang/falcor2/rendernodes/reference_pathtracer_legacy.slang`
- `slang/falcor2/rendernodes/reference_pathtracer_structural.slang`
- `tests/python/minitracer/test_render_scenes.py`
- `tests/python/pathtracer/test_pathtracer.py`
- `tests/python/pathtracer/test_reference_pathtracer_pipeline_api.py`
- `tests/python/pathtracer/test_simple_sample.py`
- `reports/structural-rt-phase4-reproduction.md`
