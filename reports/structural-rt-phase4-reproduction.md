# Phase 4 Reproduction Guide — Superseded

The original Phase 4 recipe targeted the earlier structural pipeline contract and must not be used
with the revised schema plus host-owned SBT records.

ReferencePathTracer now declares scatter and visibility programs, with `PathPayload` and
`VisibilityPayload`, in one shader schema. The host creates the six hit and three miss records in
Falcor's geometry-major order. Inline visibility remains selectable; pipeline visibility uses the
second ray type and recursion depth two.

The migration is present in the current working tree, but final publication revisions and the new
cross-platform acceptance matrix are pending.

Use these current documents instead:

- [port plan](structural-rt-port-plan.md) — concise architecture, scope, status, and validation plan;
- [checklist](structural-rt-port-checklist.md) — exact dependency pins, change ledger, pending gates,
  and gap/workaround classification.

A new clean-clone recipe will be recorded after the final SlangPy submodule and Falcor commits are
published. Old Phase 4 hashes and test outcomes remain historical evidence only.
