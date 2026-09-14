# Falcor 2 Structural Ray Tracing Port

**Updated:** 2026-09-14

**Status:** port implemented; Linux passed; final Windows/macOS validation is pending.

## Pinned sources

| Component | Revision |
| --- | --- |
| Design | `kaizhangNV/slang:archive/structural-rt-with-design-docs-20260825` at `524aa279...` |
| Slang | `kaizhangNV/slang:draft/unified-pipeline-rt-api` at `29969e72bacd308672b37e23a1b2ad7ea88c5ee2` ([PR #12691](https://github.com/shader-slang/slang/pull/12691)) |
| slang-rhi | `kaizhangNV/slang-rhi:codex/structural-rt-rhi-combined` at `5661193d...` |
| SlangPy | `codex/dynamic-schema-host-bridge` at `fc9713b5...` |
| Falcor | `codex/dynamic-schema-rt-port`; validation snapshot `b71dce2e...`, implementation `ed005961...` |

The [change ledger](structural-rt-port-checklist.md) has the complete file and test checklist.

## Design used by the port

Shaders declare an `ITraceProgramSchema`: allowed hit groups, miss shaders, callables, payload
partitions, primitive types, and record types. The host owns SBT record count, order, empty slots,
repeated programs, and record bytes. A reflected function index selects compiler code inside a
payload partition; it is not a physical SBT index.

The host must keep trace selectors and TLAS contributions compatible with each record's payload and
primitive types. This is the proposal's runtime safety boundary.

SlangPy/SGL accepts `trace_program_schema`, ordered `structural_*_types`, and matching record data.
It validates the schema, materializes entry points, and forwards exact records to slang-rhi. Falcor
maps its scene policy to geometry-major records:

```text
hit record = geometry_type * ray_type_count + ray_type
```

MiniTracer, ScenePicker, SelectionProbe, and ReferencePathTracer are ported. Legacy pipeline and
inline `RayQuery` paths remain available. ReferencePathTracer uses `PathPayload` and
`VisibilityPayload` in one schema.

## Validation

On Linux:

- at Slang `29969e72...`, `ray-tracing-2` passed 384/384, including the new unrelated
  SlangPy-shaped-generics regression;
- at the same compiler revision, ReferencePathTracer Vulkan legacy/structural parity passed in both
  inline-visibility and pipeline-visibility modes (3/3 cases); and
- the earlier SGL, SlangPy, and Falcor lanes passed at Slang `cdecb750...`; SGL (121/121 assertions)
  and all four Falcor consumers (6/6 cases) were rerun at `29969e72...`.

Run the interactive multi-payload sample with:

```bash
cd /home/zhangkai/Documents/slangwork/slang-core-ecosys/falcor2
export PYTHONPATH="$PWD:$PWD/external/slangpy"
.venv/bin/python examples/pathtracer/simple.py --device-type vulkan \
  --pipeline-api structural --visibility-mode trace-ray
```

The viewport reports frame rate; press Escape to exit.

## Gaps and workarounds

No shader API design gap was found for triangle pipeline tracing without SER.

- **SER/LSS:** intentionally unsupported. SER selects the simple scheduler; structural scenes with
  hardware LSS are rejected.
- **Metal:** Falcor has no pipeline-RT runtime. Validation is compile/materialization only.
- **Dynamic conformances:** a standalone RPT module is incomplete. Falcor supplies
  `ILight`/`IMaterial` conformances during composition. Explicit composition and normal RPT runtime
  pass; this is not an API gap.
- **Compiler integration bug:** linkage-wide structural generic checks broke unrelated modules.
  Slang `29969e72...` scopes them to API importers and adds a regression. No workaround remains.
- **Caching:** changing only host records currently relinks the high-level SlangPy pipeline. This is
  deferred performance work; correctness is unaffected.
- **RPT opacity:** BLAS entries are opaque and `OpacityEvaluator` is `AcceptAll`. SelectionProbe
  validates ignore/accept behavior; RPT-specific opacity remains inherited Falcor work.
- **CUDA:** legacy and structural canaries both segfault on the current Linux host, so this remains
  an inherited backend/host issue rather than a structural-only regression.
