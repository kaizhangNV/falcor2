# Phase 4 ReferencePathTracer scoped acceptance and local Linux reproduction

This document records the published Phase 4 ReferencePathTracer scatter implementation, exact local
Linux reproduction commands, and the completed scoped acceptance matrix. Linux Vulkan and Windows
D3D12/Vulkan provide runtime coverage; macOS provides Metal compile/materialization coverage. The
tested CUDA device reported no `Feature.ray_query`, so its two ReferencePathTracer cases skipped;
that device-specific runtime lane is explicitly non-gating for this scope.

The required compiler repair is commit
`0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617`, pushed to
`kaizhangNV/slang:draft/unified-pipeline-rt-api`. The final reproducible source tuple is:

- Slang: `0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617`;
- SlangPy and Falcor gitlink: `77205c2f3a5313c772d2df6c3cd19600887e938d`;
- Falcor2: `12448a57d16a53009973d3ff7b3a31eff2095d74`.

The Falcor revision pins the listed SlangPy revision. The commands below are the local Linux rerun
shape used with that exact tuple.

## Scope and expected behavior

Phase 4 compares the legacy and structural scatter pipelines while using the same non-SER simple
scheduler and the existing inline `RayQuery` visibility implementation. Legacy remains the default.
A retained `SchedulingMode.ser` request warns and maps to simple scheduling. A request for pipeline
visibility while structural scatter is selected warns and maps to inline visibility.

The structural layout is triangle-only. `SceneRayTracingSetup::create_structural()` rejects scenes
containing LSS. There is one real hit group at hit slot `0` and one real miss group at miss slot `0`.
The host still builds six hit records and three miss records to preserve Falcor's physical SBT
bounds: hit records `1..5` and miss records `1..2` are padding. Hit slot `3` is not a real LSS group
in Phase 4.

Falcor adds the public native `SceneRayTracingSetup::StructuralRequirements` value and exported
`get_structural_requirements()` query, plus its Python binding. This is an additive native API and
exported-symbol change, not an existing-object-layout change. It provides the minimum table counts
and flags without reflecting or materializing structural stages, allowing one adapter
materialization per built dispatch.

The following remain outside the scoped runtime acceptance:

- actual structural SER;
- hardware or procedural LSS;
- multi-payload physical-pipeline composition and structural pipeline visibility;
- CUDA ReferencePathTracer runtime on the tested device, which reports no `RayQuery` capability;
- Metal structural ray-tracing runtime;
- runtime performance benchmarking.

The sample's viewport frame-rate display is observational. It is not a benchmark result.

## Native-build safety

Run every configure, build, and potentially native-compiling test command through the Linux
descendant-process limiter. The commands use four jobs, below the hard maximum of eight, and also
pass the build tool's explicit limit. Do not use `tools/build.py`, `setup.py`, a bare
`cmake --build`, or another uncapped wrapper.

## Local paths and environment

Run this block first:

```bash
export PHASE4_FALCOR_ROOT=/home/zhangkai/Documents/slangwork/slang-core-ecosys/falcor2
export PHASE4_SLANG_ROOT=/home/zhangkai/Documents/slangwork/slang-core-ecosys/another-slang-rt-recovery
export PHASE4_FALCOR_BUILD="$PHASE4_FALCOR_ROOT/build/linux-clang-structural"
export PHASE4_SLANGPY_BUILD="$PHASE4_FALCOR_ROOT/external/slangpy/build/linux-gcc"
export PHASE4_LIMITER=/home/zhangkai/.codex/skills/limit-cpp-build-parallelism/scripts/run-limited-build.sh
export PHASE4_JOBS=4

cd "$PHASE4_FALCOR_ROOT"
export PYTHONPATH="$PHASE4_FALCOR_ROOT:$PHASE4_FALCOR_ROOT/external/slangpy"
export LD_LIBRARY_PATH="$PHASE4_SLANG_ROOT/build/Release/lib:$PHASE4_FALCOR_BUILD/Release${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

Record source identity before testing:

```bash
git -C "$PHASE4_SLANG_ROOT" rev-parse HEAD
git -C "$PHASE4_FALCOR_ROOT/external/slangpy" rev-parse HEAD
git -C "$PHASE4_FALCOR_ROOT" rev-parse HEAD
git -C "$PHASE4_FALCOR_ROOT/external/slangpy" status --short
git -C "$PHASE4_FALCOR_ROOT" status --short
test "$(git -C "$PHASE4_SLANG_ROOT" rev-parse HEAD)" = 0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617
test "$(git -C "$PHASE4_FALCOR_ROOT/external/slangpy" rev-parse HEAD)" = 77205c2f3a5313c772d2df6c3cd19600887e938d
test "$(git -C "$PHASE4_FALCOR_ROOT" rev-parse HEAD)" = 12448a57d16a53009973d3ff7b3a31eff2095d74
```

The commands must print the three revisions above. SlangPy was clean after generated native-test
`.test_temp` output was moved to trash. When rerunning from this documentation branch, Falcor may
show only the report edits; no implementation-file difference should be present.

## Build the matching compiler

From the Slang checkout:

```bash
cd "$PHASE4_SLANG_ROOT"
test "$(git rev-parse HEAD)" = 0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617
git submodule sync --recursive
git submodule update --init --recursive

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" \
MAX_JOBS="$PHASE4_JOBS" "$PHASE4_LIMITER" \
  cmake --preset default -S . --fresh

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" \
MAX_JOBS="$PHASE4_JOBS" "$PHASE4_LIMITER" \
  cmake --build --preset release --parallel "$PHASE4_JOBS" \
    --target slangc slang-test slang-glslang slang-glsl-module slang-raytracing-module

build/Release/bin/slangc -version
```

Run the two focused compiler regressions, each with a bounded timeout:

```bash
CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" build/Release/bin/slang-test \
    -use-test-server tests/ray-tracing-2/target/portable/stage-dynamic-dispatch.slang

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" build/Release/bin/slang-test \
    -use-test-server tests/ray-tracing-2/target/metal/entry-point-dynamic-dispatch.slang
```

The portable and Metal dynamic-dispatch fixtures passed 3/3, including the external-conformance
portable case. Git HEAD is authoritative: `slangc -version` printed stale generated metadata
`2026.16-95-g49facf2c3`. The loaded `libslang-compiler.so.0.2026.16` has SHA-256
`de654873133a2c6736554edd023ebb648a0eed9bfe2964e12e1fb24da35abc9e`.

## Create the Python environment

From the Falcor2 root:

```bash
cd "$PHASE4_FALCOR_ROOT"
python3 -m venv .venv
source .venv/bin/activate

"$PHASE4_LIMITER" python -m pip install --upgrade pip
NO_CMAKE_BUILD=1 "$PHASE4_LIMITER" python -m pip install -r requirements-dev.txt
NO_CMAKE_BUILD=1 "$PHASE4_LIMITER" python -m pip install \
  --editable external/slangpy --editable .
```

`NO_CMAKE_BUILD=1` prevents the Python installation from invoking the repository's uncapped native
build wrapper. Native extensions are built explicitly below.

## Build the SlangPy/SGL native regression target

The standalone SlangPy build supplies `sgl_tests`. Debug avoids the previously recorded GCC 11.5
Release/LTO compiler failure and is sufficient for these host-bridge regressions.

```bash
cd "$PHASE4_FALCOR_ROOT/external/slangpy"

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" \
MAX_JOBS="$PHASE4_JOBS" "$PHASE4_LIMITER" \
  cmake --preset linux-gcc -S . --fresh \
    -DSGL_LOCAL_SLANG=ON \
    -DSGL_LOCAL_SLANG_DIR:PATH="$PHASE4_SLANG_ROOT" \
    -DSGL_LOCAL_SLANG_BUILD_DIR=build/Release \
    -DPython_ROOT_DIR:PATH="$PHASE4_FALCOR_ROOT/.venv" \
    -DSGL_BUILD_EXAMPLES=OFF \
    -DSGL_BUILD_TESTS=ON

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" \
MAX_JOBS="$PHASE4_JOBS" "$PHASE4_LIMITER" \
  cmake --build "$PHASE4_SLANGPY_BUILD" --config Debug \
    --parallel "$PHASE4_JOBS" --target slangpy_ext slangpy_stub sgl_tests
```

Run the focused structural bridge and hot-reload shards in separate processes:

```bash
CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" "$PHASE4_SLANGPY_BUILD/Debug/sgl_tests" \
    --test-case='structural ray tracing native bridge' --no-colors=true

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" "$PHASE4_SLANGPY_BUILD/Debug/sgl_tests" \
    --test-case='native layout hot reload' --no-colors=true

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" "$PHASE4_SLANGPY_BUILD/Debug/sgl_tests" \
    --test-suite=hot_reload --no-colors=true

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" "$PHASE4_SLANGPY_BUILD/Debug/sgl_tests" \
    --test-suite=persistent_cache --no-colors=true
```

Run the SlangPy structural configuration and Vulkan generated-raygen regressions:

```bash
cd "$PHASE4_FALCOR_ROOT/external/slangpy"
export PYTHONPATH="$PHASE4_FALCOR_ROOT/external/slangpy"
export LD_LIBRARY_PATH="$PHASE4_SLANG_ROOT/build/Release/lib:$PHASE4_SLANGPY_BUILD/Debug${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" "$PHASE4_FALCOR_ROOT/.venv/bin/python" -m pytest -v -s \
    slangpy/tests/slangpy_tests/test_raytracing_config.py --device-types nodevice \
    --junitxml=/tmp/falcor2-phase4/linux-slangpy-config.xml

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
  timeout 60s "$PHASE4_LIMITER" "$PHASE4_FALCOR_ROOT/.venv/bin/python" -m pytest -v -s \
    slangpy/tests/slangpy_tests/test_raytracing.py::test_structural_raytracing \
    --device-types vulkan \
    --junitxml=/tmp/falcor2-phase4/linux-slangpy-structural.xml
```

The post-commit SlangPy build completed 119/119 steps. The combined structural bridge/layout-reload
native shard passed 2/2 cases with 164/164 assertions; the full hot-reload suite passed 13/13 cases
with 43/43 assertions; and the persistent-cache suite passed 9/9 with 145/145 assertions. Expected
negative-test compiler diagnostics appeared without changing the successful suite status.

The configuration suite passed 13/13 in 0.03 seconds; its 2,418-byte JUnit artifact has SHA-256
`5a50955059ab90af69180e9c192cba7b8ea53c59fea9b90b58957d918bb4e522`. The structural generated-
raygen/prelude/reload test passed 1/1 in 4.46 seconds; its 378-byte JUnit artifact has SHA-256
`069092a32b835a933b67748bffbfe3764e8952db429aa80c672f91b327cef339`. SlangPy pre-commit passed
all files.

## Build the integrated Falcor2 extensions

Build Falcor2 and its in-tree SlangPy dependency together so both Python extensions load the same
`libsgl` and compiler ABI:

```bash
cd "$PHASE4_FALCOR_ROOT"

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" \
MAX_JOBS="$PHASE4_JOBS" "$PHASE4_LIMITER" \
  cmake --preset linux-clang -S . -B "$PHASE4_FALCOR_BUILD" \
    -DSGL_LOCAL_SLANG=ON \
    -DSGL_LOCAL_SLANG_DIR:PATH="$PHASE4_SLANG_ROOT" \
    -DSGL_LOCAL_SLANG_BUILD_DIR=build/Release \
    -DPython_ROOT_DIR:PATH="$PHASE4_FALCOR_ROOT/.venv" \
    -DPython_FIND_REGISTRY:STRING=NEVER \
    -DFALCOR_ENABLE_NGX=OFF

CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" \
MAX_JOBS="$PHASE4_JOBS" "$PHASE4_LIMITER" \
  cmake --build "$PHASE4_FALCOR_BUILD" --config Release \
    --parallel "$PHASE4_JOBS" --target slangpy_ext falcor2_ext
```

Reset the runtime paths to the integrated build and verify package/library selection:

```bash
export PYTHONPATH="$PHASE4_FALCOR_ROOT:$PHASE4_FALCOR_ROOT/external/slangpy"
export LD_LIBRARY_PATH="$PHASE4_SLANG_ROOT/build/Release/lib:$PHASE4_FALCOR_BUILD/Release"

"$PHASE4_FALCOR_ROOT/.venv/bin/python" -c \
  'import falcor2, slangpy; print(falcor2.__file__); print(slangpy.__file__)'
ldd falcor2/falcor2_ext*.so | grep -E 'libfalcor2|libsgl|libslang-compiler|not found'
ldd external/slangpy/slangpy/slangpy_ext*.so | grep -E 'libsgl|libslang-compiler|not found'
```

Both Python package paths must be under this checkout, neither `ldd` command may report
`not found`, and the loaded `libsgl`/compiler must come from the intended integrated/compiler build
directories. The production Falcor build completed 158/158 steps. `/proc/self/maps` after import
resolved the intended compiler library above, integrated `libsgl.so` with SHA-256
`ce676d12fc6f241655b6a9be9e3cf7682a02e9315b589eba8572a09ee69c77b8`, and integrated
`libfalcor2.so` with SHA-256
`57bc225438b5db3c8cf9afd6472f905660c1f537eddbdad8a57556979a6e9a26`. Both package paths were
inside this checkout.

The optional broad `falcor2_tests` build still stops on the pre-existing alias-template CTAD errors
recorded in the main checklist. That blocker is not evidence against the Phase 4 production build,
but it means the broad native suite is not claimed here.

SlangPy `pre-commit run --all-files` passed, and Falcor pre-commit passed every Phase 4
implementation file.

## Run the focused Phase 4 Falcor suite on Vulkan

```bash
cd "$PHASE4_FALCOR_ROOT"
mkdir -p /tmp/falcor2-phase4

SLANGPY_DEVICE=vulkan CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" \
CTEST_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" timeout 60s "$PHASE4_LIMITER" \
  .venv/bin/python -m pytest -v -s \
    tests/python/pathtracer/test_reference_pathtracer_pipeline_api.py \
    tests/python/pathtracer/test_simple_sample.py \
    tests/python/pathtracer/test_pathtracer.py::test_pathtracer_structural_scatter_matches_legacy \
    tests/python/pathtracer/test_pathtracer.py::test_pathtracer_structural_guides_and_mode_switch_match_legacy \
    --junitxml=/tmp/falcor2-phase4/linux-vulkan.xml
```

This command passed 19/19 cases in 8.53 seconds. The 3,191-byte JUnit artifact has SHA-256
`54856989051f61932584d2d2ccf4edb8c7a5396c15039f7254beaffb305bf8b6`. It contains 17/17 API/sample
configuration cases and 2/2 runtime cases. Falcor pre-commit passed every Phase 4 file. The runtime cases require
`Feature.ray_query`; an unexpected Vulkan capability skip does not satisfy the Phase 4 runtime gate.

The two runtime cases compare finite, non-zero legacy and structural color at `rtol=1e-4` and
`atol=1e-5`. The API-switch case also compares enabled guide buffers and asserts the exact six-hit/
three-miss padding shape.

The post-commit UI regression command was:

```bash
SLANGPY_DEVICE=vulkan CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" \
CTEST_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" timeout 60s "$PHASE4_LIMITER" \
  .venv/bin/python -m pytest -v -s \
    tests/python/ui/test_scene_picker.py::test_structural_setup_pads_scene_policy_without_name_collision \
    tests/python/ui/test_scene_picker.py::test_structural_pipeline_matches_legacy_complete_id_map \
    tests/python/ui/test_selection_overlay.py::test_structural_any_hit_matches_legacy_complete_mask \
    --junitxml=/tmp/falcor2-phase4/linux-vulkan-ui.xml
```

It passed 3/3 in 4.74 seconds. The 712-byte JUnit artifact has SHA-256
`67e0dc6a9d6c781ca0345e2266ba9e4b7e3b2f46fa9993a09412ac4da79d3344`.

## Run bounded legacy and structural Cornell-box samples

These commands use the same scene, resolution, spp, depth, and frame count. They are correctness
captures, not timing benchmarks.

```bash
cd "$PHASE4_FALCOR_ROOT"

.venv/bin/python examples/pathtracer/simple.py \
  --device-type vulkan --pipeline-api legacy \
  --frames 1 --width 96 --height 64 --spp 1 --max-depth 1 \
  --output /tmp/falcor2-phase4/cornell-legacy.png

.venv/bin/python examples/pathtracer/simple.py \
  --device-type vulkan --pipeline-api structural \
  --frames 1 --width 96 --height 64 --spp 1 --max-depth 1 \
  --output /tmp/falcor2-phase4/cornell-structural.png

sha256sum \
  /tmp/falcor2-phase4/cornell-legacy.png \
  /tmp/falcor2-phase4/cornell-structural.png \
  /tmp/falcor2-phase4/linux-vulkan.xml
```

Both clean-working-directory depth-1 commands exited successfully and produced byte-identical PNGs
with SHA-256 `f814d20be00b53ca8d26f949a36996062a74a5ee6612bf4d366240de528adde3`.
Separate processes can consume different random samples, so the deterministic in-process float/guide
pytest comparisons remain the primary parity gate.

A richer local comparison used the default one sample per frame, depth 3, 64 frames, and requested
320x240 presentation size:

```bash
.venv/bin/python examples/pathtracer/simple.py \
  --device-type vulkan --pipeline-api legacy \
  --frames 64 --width 320 --height 240 --max-depth 3 \
  --output output/phase4/reference-legacy.png

.venv/bin/python examples/pathtracer/simple.py \
  --device-type vulkan --pipeline-api structural \
  --frames 64 --width 320 --height 240 --max-depth 3 \
  --output output/phase4/reference-structural.png
```

Both outputs are 238x154 RGBA PNGs after the window/client-area sizing applied by the sample, and
both have SHA-256 `6b222382afca4ccd1787ebb9e6874dd013342dd9f27306ce6d1546c862c61123`.

## CUDA/OptiX capability check

ReferencePathTracer structural scatter currently depends on inline RayQuery visibility. Use the same
focused runtime nodes to document the CUDA device's actual capability:

```bash
cd "$PHASE4_FALCOR_ROOT"

SLANGPY_DEVICE=cuda CMAKE_BUILD_PARALLEL_LEVEL="$PHASE4_JOBS" \
CTEST_PARALLEL_LEVEL="$PHASE4_JOBS" MAX_JOBS="$PHASE4_JOBS" \
VCPKG_MAX_CONCURRENCY="$PHASE4_JOBS" timeout 60s "$PHASE4_LIMITER" \
  .venv/bin/python -m pytest -v -s -rs \
    tests/python/pathtracer/test_pathtracer.py::test_pathtracer_structural_scatter_matches_legacy \
    tests/python/pathtracer/test_pathtracer.py::test_pathtracer_structural_guides_and_mode_switch_match_legacy \
    --junitxml=/tmp/falcor2-phase4/linux-cuda.xml
```

The local device reported no `Feature.ray_query`, so both tests skipped as expected in 0.32 seconds.
The 1,133-byte JUnit artifact has SHA-256
`a85f7eb40c22d3979d638f7ecfbe3a5fb47862ba8979f375953a73eb9ff5ed43`. This confirms containment
but is not a successful Phase 4 CUDA runtime comparison. CUDA is explicitly non-gating for the
scoped acceptance because this ReferencePathTracer port retains inline RayQuery visibility.

## Windows D3D12/Vulkan acceptance

The final Windows worker ran on `DESKTOP-GUULUMF` at the exact published tuple. Its compiler and
Falcor/SlangPy builds were capped at no more than eight jobs. All 46/46 selected cases passed:

- SlangPy configuration: 13/13;
- Falcor pipeline-API and sample configuration: 17/17;
- SlangPy structural generated-raygen/prelude/conformance/reload: 1/1 on D3D12 and 1/1 on Vulkan;
- ReferencePathTracer color/guide parity and API switching: 2/2 on D3D12 and 2/2 on Vulkan;
- Phase 3 ScenePicker/SelectionProbe UI non-regression: 5/5 on D3D12 and 5/5 on Vulkan.

Worker source validation reported 27 matching hashes. The initial Slang build and compiler-test
transcript is preserved at
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase4-windows/20260903-phase4-windows`;
the resumed Falcor/SlangPy build, test transcript, and artifacts are preserved at
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase4-windows-resume/20260903-phase4-windows-resume`.
`windows.log` is 159,673 bytes with SHA-256
`9275c19d4982be8df86ff344068d05a751e5d001a38a2b5a4b46bef503bf4e2f`. The JUnit artifacts are:

- `falcor-pathtracer-d3d12.xml`: 570 bytes,
  `f438aeacce4f0f317d34d00c5e4c5cb4093fc2bdcd9a2c30ed23db782e802953`;
- `falcor-pathtracer-vulkan.xml`: 572 bytes,
  `0d18ce5bc582f6a226b6794e00c666948815a112870f69d3cd78fc2bf1f6bbab`;
- `falcor-phase3-ui-d3d12.xml`: 961 bytes,
  `ebe785d5f482e08b8f2b1966da56d126936f30e41276bedf6c491a7ea0e5cea6`;
- `falcor-phase3-ui-vulkan.xml`: 966 bytes,
  `f46da1f96a9bc30dca49c551a524ee34695d57d26830d0a5a1133c1cda27e2e1`;
- `falcor-phase4-config-sample.xml`: 2,879 bytes,
  `5229caeb9c8595863a9e2af37b231474e8846335b2866b002d31dbad6ebe5133`;
- `slangpy-raytracing-config.xml`: 2,425 bytes,
  `9c0ecaa397a87a462ff62105bfc621cbd147371b455279642ee5a97f562da78c`;
- `slangpy-structural-d3d12.xml`: 384 bytes,
  `7c7cac6a82823bf4972291bee1ed0701b7c4a4e8957d59f6ff8907e4acbe411a`;
- `slangpy-structural-vulkan.xml`: 385 bytes,
  `1278aa74a4158dec355cbfa29eb3d6c05329269e6529871b970eb68fb3566cce`.

The Vulkan driver emitted pre-existing VUID 08740/08742 diagnostics because generated modules
declare NV sphere/LSS capabilities that this device does not expose. These diagnostics are
non-gating for the triangle-only Phase 4 route; every selected Vulkan test passed.

## macOS Metal compile/materialization acceptance

The final macOS worker built the matching compiler and SlangPy targets with no more than eight jobs.
The native structural/layout shard passed 2/2 cases with 164 assertions and the full hot-reload suite
passed 13/13 cases with 43 assertions. The actual ReferencePathTracer `ScatterProgramLayout`
materialized on Metal in the production node load order: one hit and one miss were reflected, six hit
and three miss slots were physically materialized, and callable count was zero. Its real entry points
were `ScatterClosestHit` and `ScatterMiss`.

The macOS `slang-test` wrapper discovered the three focused subtests but platform-ignored all three,
so it ran 0 tests. Separate direct invocations of those exact compiler configurations passed 3/3,
including local and external-conformance dynamic-dispatch forms, and three Metal sources compiled to
non-empty AIR. This is compile/materialization evidence; Falcor Metal ray-tracing runtime is
unavailable and no runtime result is claimed.

The complete artifact directory is
`/home/zhangkai/.codex/local-build-farm/runs/falcor2-structural-rt-phase4-macos-resume/20260903-122722`.
Its `artifacts/phase4-resume-results/SHA256SUMS.txt` manifest has SHA-256
`ac7ba68498b0b45fe0bc9523d67a60d2c5da796d067b8d3a153b9b8393c39366`. Key artifact hashes are:

- `reference-pathtracer-layout.json`:
  `987c6e8e182f7851c80e76b65173ef22ccf56dfd538ad45f7c9b3bad91e02343`;
- `entry-point-dynamic-dispatch.air`:
  `d5871a82b0398776ecf961696e659743add8458f805a79aadeea79c9d1a99e51`;
- `trace-miss-closest-hit.air`:
  `bc286d0b499923cbfae9134601edbd15fd5868540fb99d7b64ed4ed03000d32a`;
- `trace-triangle-any-hit.air`:
  `7f70315d8148aa8aa6d6250b6d0bc699513d99d719aec0a47a992686f22c8efd`.

## Scoped acceptance record

The fields below are verified at the exact published tuple:

- Falcor branch and full commit: `codex/structural-rt-port`,
  `12448a57d16a53009973d3ff7b3a31eff2095d74`
- SlangPy branch, full commit, and Falcor gitlink: `codex/structural-rt-host-bridge`,
  `77205c2f3a5313c772d2df6c3cd19600887e938d`
- Slang branch and full commit: `draft/unified-pipeline-rt-api`,
  `0dc2a4df7ae288aebcf2d3e9b2a8779177ccc617`
- local Linux `slangc -version`: stale generated metadata `2026.16-95-g49facf2c3`; Git SHA above is
  authoritative
- local Linux loaded library hashes: compiler
  `de654873133a2c6736554edd023ebb648a0eed9bfe2964e12e1fb24da35abc9e`, SGL
  `ce676d12fc6f241655b6a9be9e3cf7682a02e9315b589eba8572a09ee69c77b8`, Falcor
  `57bc225438b5db3c8cf9afd6472f905660c1f537eddbdad8a57556979a6e9a26`
- local Linux compiler focused regression results: 3/3 passed
- SGL structural/layout reload: 2/2 cases, 164/164 assertions
- SGL hot reload: 13/13 cases, 43/43 assertions
- SGL persistent cache: 9/9 cases, 145/145 assertions
- SlangPy configuration: 13/13 passed; generated-raygen/prelude reload: 1/1 passed
- Falcor production build: 158/158 steps
- Falcor Vulkan: 19/19 passed; JUnit SHA-256
  `54856989051f61932584d2d2ccf4edb8c7a5396c15039f7254beaffb305bf8b6`
- legacy/structural sample captures: both comparison pairs byte-identical; hashes recorded above
- tested local CUDA device's RayQuery capability and run/skip result: unavailable, 2/2 skipped as
  expected; not runtime coverage and non-gating for this scope
- Windows D3D12/Vulkan: 46/46 selected cases passed on `DESKTOP-GUULUMF`; all 27 recorded hashes
  matched
- macOS Metal compile/materialization: compiler and SlangPy builds passed; native structural and hot-
  reload suites passed; the actual layout materialized; direct compiler configurations passed 3/3;
  three non-empty AIR files were produced
- scoped Phase 4 acceptance: **COMPLETE** for Linux Vulkan runtime, Windows D3D12/Vulkan runtime, and
  macOS Metal compile/materialization
- runtime performance measurements: **DEFERRED; not part of Phase 4 acceptance**
