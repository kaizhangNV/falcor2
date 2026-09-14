# Phase 4 Reproduction Guide — Superseded

The original Phase 4 recipe targeted the earlier structural pipeline contract and must not be used
with the revised schema plus host-owned SBT records.

ReferencePathTracer now declares scatter and visibility programs, with `PathPayload` and
`VisibilityPayload`, in one shader schema. The host creates the six hit and three miss records in
Falcor's geometry-major order. Inline visibility remains selectable; pipeline visibility uses the
second ray type and recursion depth two.

The migration is published in Falcor `ed005961d49032432c5c0c6a90a52d509e87f79f`, which pins
SlangPy `fc9713b5d93501bded86d9082f4575573f50ef01`. The current acceptance matrix is in the checklist.

Use these current documents instead:

- [port plan](structural-rt-port-plan.md) — concise architecture, scope, status, and validation plan;
- [checklist](structural-rt-port-checklist.md) — exact dependency pins, change ledger, acceptance gates,
  and gap/workaround classification.

Old Phase 4 hashes and test outcomes remain historical evidence only.
