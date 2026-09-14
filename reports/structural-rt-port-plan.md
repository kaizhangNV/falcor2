# Falcor 2 Structural Pipeline Ray Tracing Port

**Updated:** 2026-09-14

**Status:** Linux Vulkan implementation and focused validation complete; publication and the
remaining platform matrix are pending.

## Revision tuple

| Component | Revision |
| --- | --- |
| Design | `kaizhangNV/slang:archive/structural-rt-with-design-docs-20260825` at `524aa27903d6ab7f46b3220466b1c7ed3415cce5` |
| Slang | `kaizhangNV/slang:draft/unified-pipeline-rt-api` at `cdecb75031c1ce125985e51032c00a11c1f85492` ([PR #12691](https://github.com/shader-slang/slang/pull/12691)) |
| slang-rhi | `kaizhangNV/slang-rhi:codex/structural-rt-rhi-combined` at `5661193d9415fb3c84c068afb149b85ea7fe2310` |
| SlangPy | `codex/dynamic-schema-host-bridge` at `53385859307f020d80410045548d2cdefc8ab2e8` (published) |
| Falcor | `codex/dynamic-schema-rt-port`; publication pending |

The old phase reports are historical baselines. They describe the superseded shader-owned SBT
position model and are not acceptance evidence for this revision.

## Current design

Shader code declares an `ITraceProgramSchema`: the permitted hit groups, miss shaders, callables,
payload partitions, primitive types, and record types. The host owns the physical SBT: record count,
order, empty records, repeated program selections, and per-record bytes.

A reflected function index identifies compiler code within a payload partition; it is not a
physical SBT index. Payload belongs to each hit or miss context, so one schema can contain both
`PathPayload` and `VisibilityPayload`.

The host remains responsible for making runtime trace selectors and TLAS contributions reach
records with compatible payload and primitive types. That is the proposal's native-runtime safety
boundary, not a missing shader feature.

## Implemented port

SlangPy/SGL now accepts `trace_program_schema` plus ordered `structural_*_types` and parallel
`structural_*_record_data` arrays. It:

- reflects payload partitions, program types, record layouts, native ABI sizes, and target names;
- preserves duplicates, empty records, order, and exact bytes in shader-table/cache identity;
- validates schema membership, section kind, data size, and stage identity;
- materializes generated stages after module composition; and
- keeps the legacy named-entry-point API as an exclusive mode.

slang-rhi owns and copies application bytes for hit, miss, and callable records.

Falcor's `SceneRayTracingSetup::create_structural()` converts per-ray/per-geometry selections to its
existing geometry-major policy:

```text
physical hit record = geometry_type * ray_type_count + ray_type
```

It forwards record bytes and reflected payload/attribute sizes. The current scene policy produces
six hit records and three miss records; missing combinations remain empty.

The following consumers are migrated while keeping legacy and existing inline modes:

- MiniTracer;
- ScenePicker;
- SelectionProbe; and
- ReferencePathTracer, with scatter `PathPayload` and visibility `VisibilityPayload` in one schema.

ReferencePathTracer can use inline `RayQuery` visibility or pipeline `TraceRay` visibility. The
latter selects ray type 1 and recursion depth 2. SER currently maps to the simple scheduler with a
warning.

## Linux validation

All results below use Slang `cdecb750...` and the eight-job build cap.

- Slang: trace-call 5/5 and portable 114/114; Cornell direct DXIL clean; Cornell Vulkan and OptiX
  legacy/structural output byte-identical.
- SlangPy/SGL: native bridge 121/121 assertions, configuration 19/19, pre-commit, pyright, and
  Vulkan legacy plus repeated-record/distinct-byte structural dispatch passed.
- Falcor native: scene policy 4/4 assertions and ABI/geometry-major/repeated-byte setup 13/13.
- Falcor Vulkan: legacy/structural parity passed for MiniTracer, ScenePicker, SelectionProbe, and
  ReferencePathTracer with both visibility modes; guide output and API switching also passed.
- Falcor configuration: 17/17 tests passed.

Clang built the production libraries, but Clang 17 rejected pre-existing alias-template deduction
in unrelated native test files. The GCC build linked the complete native test binary and ran the
focused tests above. The optional DamagedHelmet test was unavailable because its asset is absent
from this checkout.

To run the interactive multi-payload path:

```bash
cd /home/zhangkai/Documents/slangwork/slang-core-ecosys/falcor2
export PYTHONPATH="$PWD:$PWD/external/slangpy"
.venv/bin/python examples/pathtracer/simple.py --device-type vulkan \
  --pipeline-api structural --visibility-mode trace-ray --frames 8 \
  --output output/pathtracer-structural.png
```

The viewport shows frame rate. Omit `--frames` to run until Escape.

## Gaps and workarounds

No shader API design gap is confirmed for triangle pipeline tracing without SER.

- **SER and hardware LSS:** intentional omissions. SER maps to simple scheduling; structural Falcor
  rejects scenes containing LSS.
- **Metal:** Falcor/SGL has no pipeline RT runtime. Schema reflection, MSL generation, and cloned
  adapter metadata can be tested, but rendering parity cannot be claimed. The adapter preserves
  synthesized `NoClosestHit` names and treats folded any-hit/intersection names as Metal-only.
- **RPT opacity:** deferred inherited Falcor integration work. Triangle BLAS entries are opaque and
  `OpacityEvaluator` is currently `AcceptAll`; SelectionProbe's non-opaque layered-quad test does
  validate structural ignore/accept any-hit mechanics.
- **CUDA:** both unchanged legacy and structural SlangPy canaries segfault at dispatch on this host.
  This is an inherited backend/test-host baseline, not a structural-only regression.
- **Caching:** high-level SlangPy currently relinks when only physical records change. Low-level SGL
  can reuse the pipeline; splitting those cache identities is deferred performance work.

## Remaining work

Commit and push Falcor with its gitlink pinned to SlangPy `53385859...`. Then verify the tuple from a
clean recursive checkout and complete Windows D3D12/Vulkan, supported CUDA, and macOS compile-only
gates. Runtime performance comparison follows correctness and must use identical scenes, warm-up,
dimensions, samples, compiler, and driver settings.
