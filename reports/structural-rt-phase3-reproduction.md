# Phase 3 Reproduction Guide — Superseded

The original Phase 3 recipe targeted the earlier shader-owned SBT-position API and must not be used
with the revised structural ray tracing design.

The current design uses shader-declared program schemas and host-owned ordered physical records.
ScenePicker and SelectionProbe have been migrated in the current working tree, but the exact
SlangPy and Falcor publication commits and final cross-platform results are still pending.

Use these current documents instead:

- [port plan](structural-rt-port-plan.md) — concise architecture, scope, status, and validation plan;
- [checklist](structural-rt-port-checklist.md) — exact dependency pins, change ledger, pending gates,
  and gap/workaround classification.

A clean-clone command recipe will be added to the checklist after the final SlangPy submodule and
Falcor commits are published. Until then, old Phase 3 results are historical evidence only and do
not validate the revised migration.
