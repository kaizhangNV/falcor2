# Falcor 2 Revised Structural Ray Tracing Port

**Updated:** 2026-09-14

**Outcome:** the scoped triangle pipeline port is complete. MiniTracer, ScenePicker,
SelectionProbe, and ReferencePathTracer run with the revised API on Linux Vulkan and Windows
D3D12/Vulkan. Metal is compile/materialization-only because Falcor has no Metal pipeline-RT
runtime. No shader-API design gap was found for this scope; one D3D12 backend gap remains for
non-void shader-record data.

## Revisions

| Component | Revision |
| --- | --- |
| Design | `kaizhangNV/slang:archive/structural-rt-with-design-docs-20260825` at `524aa279...` |
| Slang | `kaizhangNV/slang:draft/unified-pipeline-rt-api` at `29969e72...` ([PR #12691](https://github.com/shader-slang/slang/pull/12691)) |
| slang-rhi | `kaizhangNV/slang-rhi:codex/structural-rt-rhi-combined` at `5661193d...` |
| SlangPy | `kaizhangNV/slangpy:codex/dynamic-schema-host-bridge` at `fc9713b5...` |
| Falcor | `kaizhangNV/falcor2:codex/dynamic-schema-rt-port`; validation code head `6502d2d7...` |

The [change ledger](structural-rt-port-checklist.md) is the complete implementation and test
checklist.

## Ported scope

Shaders declare an `ITraceProgramSchema` containing programs, payload partitions, primitives, and
record types. The host owns physical SBT order, empty/repeated slots, and application bytes. Falcor
writes hit records in geometry-major order:

```text
hit record = geometry_row * ray_type_count + ray_type
```

Function indices identify schema programs, not SBT slots. The host must align TLAS contributions
and ray selectors with compatible record payload and primitive types.

Legacy and inline `RayQuery` paths remain. ReferencePathTracer puts `PathPayload` and
`VisibilityPayload` in one schema and supports inline or pipeline visibility.

## Validation

| Platform | Result |
| --- | --- |
| Linux | Slang RT 384/384, SGL 121/121, SlangPy 21/21, and six focused Vulkan consumer/parity cases passed. |
| Windows | Run `f2-r4c3-win-9f87-cached` covers unchanged MiniTracer/ScenePicker on D3D12/Vulkan. Final run `f2-final-win-6502d2d-29969-r8` completed functional validation in 133.632 s: SelectionProbe 1/1 and ReferencePathTracer 4/4 on each backend, plus Vulkan record-byte transport 1/1. |
| macOS | At the relevant `9f87e21...`/`64b195c...` heads, SGL Metal bridge 123/123 and all four Falcor schemas reflected/linked. Production SelectionProbe emitted 21,339 bytes of MSL with a 32-byte hit-record stride. |

The Windows D3D record-data canary is an intentional expected failure described below. Vulkan
image/output parity passed, but the inline visibility variant is not validation-clean: the shared
pre-existing `RayQuerySceneIntersector` compiles stale LSS helpers whose inline SPIR-V declares LSS
and sphere capabilities on a device without them. This affects both legacy and structural modes
when RPT visibility uses `ray_query`, as well as ScenePicker's inline path. The `trace-ray` RPT
sample below avoids it.

The macOS runner lacks a licensed full-Xcode Metal compiler, so MSL-to-AIR and Metal rendering were
not tested.

## Gaps and workarounds

| Item | Classification and current handling |
| --- | --- |
| D3D12 non-void `Context.Record` | Backend gap. Slang assigns no finite record-cbuffer binding; slang-rhi lacks a DXR local root signature/export association. DXR rejects state creation. Falcor's D3D consumers avoid this path. |
| Vulkan LSS diagnostics | Inherited inline-ray issue. Stale LSS helpers declare unsupported LSS/sphere capabilities in triangle-only SPIR-V. Use pipeline visibility; a future link-time scene-mode specialization should omit those helpers. |
| Metal candidate data | Metal any-hit/intersection candidates cannot read ordinary globals. SelectionProbe carries its bitmap address/count in host record data and rebuilds the Metal pipeline/table when it changes. |
| D3D environment texture | Pre-existing codegen issue. Passing the descriptor wrapper between helpers and unwrapping locally avoids a typed-resource mismatch that first failed in legacy. |
| Deferred features | SER uses the simple scheduler; structural LSS scenes are rejected; helper callables and richer RPT opacity remain future work. SlangPy relinking after host-only record edits is performance debt. |

## Run the sample

```bash
cd /home/zhangkai/Documents/slangwork/slang-core-ecosys/falcor2
export PYTHONPATH="$PWD:$PWD/external/slangpy"
.venv/bin/python examples/pathtracer/simple.py --device-type vulkan \
  --pipeline-api structural --visibility-mode trace-ray
```

The interactive viewport reports FPS; press Escape to exit.
