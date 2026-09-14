# Phase 3 Reproduction Guide — Superseded

The original Phase 3 recipe targeted the earlier shader-owned SBT-position API and must not be used
with the revised structural ray tracing design.

The current design uses shader-declared program schemas and host-owned ordered physical records.
ScenePicker and SelectionProbe are published in Falcor `ed005961d49032432c5c0c6a90a52d509e87f79f`,
which pins SlangPy `fc9713b5d93501bded86d9082f4575573f50ef01`.

Use these current documents instead:

- [port plan](structural-rt-port-plan.md) — concise architecture, scope, status, and validation plan;
- [checklist](structural-rt-port-checklist.md) — exact dependency pins, change ledger, acceptance gates,
  and gap/workaround classification.

Old Phase 3 results remain historical evidence only and do not validate the revised migration.
