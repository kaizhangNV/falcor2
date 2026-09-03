# Phase 3 ScenePicker and SelectionProbe reproduction

This recipe reproduces the Phase 3 structural ray-tracing runtime proof for Falcor's production
`ScenePicker` and `SelectionOverlay` classes. The focused tests are headless. They are not an
interactive editor sample and do not open a window.

## Scope

The tests exercise the following production paths:

- `ScenePicker` creates a structural ray-tracing pipeline and shader table, links structural
  ray-generation/closest-hit plus a slot-zero miss stage, dispatches rays, and writes the complete
  geometry-instance ID texture.
- `SelectionOverlay::draw_overlay()` dispatches the structural SelectionProbe ray-generation,
  any-hit, and slot-zero miss configuration. The test proves that traversal ignores a non-selected
  front quad and accepts a selected rear quad behind it.
- Structural output is compared exactly with the legacy pipeline output. Vulkan and D3D12 also
  compare against the unchanged inline ray-query path.

The test scene contains two overlapping triangle quads. Each quad has two independently
addressable BLAS geometries, and the image also contains miss pixels. This covers four geometry IDs,
closest-hit output, miss-pixel output, `ignoreHit()`, and `acceptHitAndEndSearch()`. It does not use
an independent payload sentinel to prove miss-stage invocation in isolation.

This recipe does not prove interactive mouse picking in an editor window, one end-to-end
structural-ScenePicker-to-structural-SelectionOverlay chain, the final displayed selection-overlay
pixels, non-zero ray-type slots with distinct sentinels, callable shaders, LSS, or Metal runtime
behavior. The SelectionProbe parity test deliberately supplies the same legacy ScenePicker texture
to both probe implementations so it isolates the probe behavior. Metal structural pipeline runtime
is unavailable in this stack.

## Exact source revisions

Use these revisions to reproduce the recorded result:

```text
Falcor2:  890f6d87bf439a77e203381e43caa7552be36b08
          branch codex/structural-rt-port
SlangPy:  aa8840bc8ca644c45ea9d475f3f937b66faf8208
          branch codex/structural-rt-host-bridge
Slang:    036132fa8fbfbe2e9300a0e0edb46d0405d973d0
          branch draft/unified-pipeline-rt-api
```

The Falcor2 revision pins the SlangPy revision as the `external/slangpy` submodule.

## Fast path in an already-built Linux checkout

From the Falcor2 repository root:

```bash
export PYTHONPATH="$PWD:$PWD/external/slangpy"

SLANGPY_DEVICE=vulkan .venv/bin/python -m pytest -v -s \
  tests/python/ui/test_scene_picker.py::test_structural_pipeline_matches_legacy_complete_id_map \
  tests/python/ui/test_selection_overlay.py::test_structural_any_hit_matches_legacy_complete_mask
```

Expected final line:

```text
2 passed
```

Run the same two tests on CUDA/OptiX with:

```bash
SLANGPY_DEVICE=cuda .venv/bin/python -m pytest -v -s \
  tests/python/ui/test_scene_picker.py::test_structural_pipeline_matches_legacy_complete_id_map \
  tests/python/ui/test_selection_overlay.py::test_structural_any_hit_matches_legacy_complete_mask
```

## Clean Linux reproduction

### 1. Prerequisites

- Git
- Python 3.9 or newer; the recorded Linux run used Python 3.12
- CMake 3.25 or newer, Ninja, Clang, and Clang++
- Linux development packages `libxinerama-dev`, `libxcursor-dev`, `xorg-dev`, `libglu1-mesa-dev`,
  and `pkg-config`
- A Vulkan driver and GPU with acceleration-structure and ray-tracing-pipeline support
- An NVIDIA GPU/driver for the optional CUDA/OptiX run
- The `limit-cpp-build-parallelism` Codex skill installed at
  `~/.codex/skills/limit-cpp-build-parallelism`

On Debian/Ubuntu, the build prerequisites can be installed with:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential clang cmake ninja-build git python3 python3-venv pkg-config \
  libxinerama-dev libxcursor-dev xorg-dev libglu1-mesa-dev
```

The commands below use four jobs, below the hard maximum of eight, and run every native build
through the Linux CPU-affinity limiter. Four is intentional: it is the stable setting used after a
transient compiler allocator/ICE failure at eight jobs during validation.

### 2. Clone and build the matching Slang compiler

Choose a parent directory, then run:

```bash
git clone --recursive --branch draft/unified-pipeline-rt-api \
  https://github.com/kaizhangNV/slang.git slang-structural-rt
cd slang-structural-rt
git checkout 036132fa8fbfbe2e9300a0e0edb46d0405d973d0
git submodule sync --recursive
git submodule update --init --recursive

CMAKE_BUILD_PARALLEL_LEVEL=4 VCPKG_MAX_CONCURRENCY=4 MAX_JOBS=4 \
  ~/.codex/skills/limit-cpp-build-parallelism/scripts/run-limited-build.sh \
  cmake --preset default

CMAKE_BUILD_PARALLEL_LEVEL=4 VCPKG_MAX_CONCURRENCY=4 MAX_JOBS=4 \
  ~/.codex/skills/limit-cpp-build-parallelism/scripts/run-limited-build.sh \
  cmake --build --preset release --parallel 4 \
    --target slangc slang-glslang slang-glsl-module slang-raytracing-module
```

After the build, `build/Release/bin/slangc` should exist.

### 3. Clone Falcor2 and initialize the pinned SlangPy fork

Return to the parent directory containing `slang-structural-rt`, then run:

```bash
git clone --recursive --branch codex/structural-rt-port \
  https://github.com/kaizhangNV/falcor2.git falcor2
cd falcor2
git checkout 890f6d87bf439a77e203381e43caa7552be36b08
git submodule sync --recursive
git submodule update --init --recursive
```

Verify the source revisions:

```bash
git rev-parse HEAD
git -C external/slangpy rev-parse HEAD
git -C ../slang-structural-rt rev-parse HEAD
```

They must print the three revisions listed above.

### 4. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

NO_CMAKE_BUILD=1 python -m pip install -r requirements-dev.txt
NO_CMAKE_BUILD=1 python -m pip install --editable external/slangpy --editable .
```

`NO_CMAKE_BUILD=1` is intentional. It installs the editable Python packages without invoking the
repository's uncapped build wrapper; the native extensions are built explicitly in the next step.

### 5. Configure and build Falcor2 against the matching Slang compiler

The following directory layout is assumed:

```text
parent/
  slang-structural-rt/
  falcor2/
```

From `falcor2/`:

```bash
CMAKE_BUILD_PARALLEL_LEVEL=4 VCPKG_MAX_CONCURRENCY=4 MAX_JOBS=4 \
  ~/.codex/skills/limit-cpp-build-parallelism/scripts/run-limited-build.sh \
  cmake --preset linux-clang -S . -B build/linux-clang-structural \
    -DSGL_LOCAL_SLANG=ON \
    -DSGL_LOCAL_SLANG_DIR:PATH="$PWD/../slang-structural-rt" \
    -DSGL_LOCAL_SLANG_BUILD_DIR=build/Release \
    -DPython_ROOT_DIR:PATH="$PWD/.venv" \
    -DPython_FIND_REGISTRY:STRING=NEVER \
    -DFALCOR_ENABLE_NGX=OFF

CMAKE_BUILD_PARALLEL_LEVEL=4 VCPKG_MAX_CONCURRENCY=4 MAX_JOBS=4 \
  ~/.codex/skills/limit-cpp-build-parallelism/scripts/run-limited-build.sh \
  cmake --build build/linux-clang-structural --config Release --parallel 4 \
    --target slangpy_ext falcor2_ext
```

Verify that Python resolves both packages from this checkout:

```bash
export PYTHONPATH="$PWD:$PWD/external/slangpy"
.venv/bin/python -c \
  'import falcor2, slangpy; print(falcor2.__file__); print(slangpy.__file__)'
```

Both printed paths should be below the current Falcor2 checkout.

### 6. Run the focused structural tests

Vulkan:

```bash
SLANGPY_DEVICE=vulkan .venv/bin/python -m pytest -v -s \
  tests/python/ui/test_scene_picker.py::test_structural_pipeline_matches_legacy_complete_id_map \
  tests/python/ui/test_selection_overlay.py::test_structural_any_hit_matches_legacy_complete_mask
```

CUDA/OptiX:

```bash
SLANGPY_DEVICE=cuda .venv/bin/python -m pytest -v -s \
  tests/python/ui/test_scene_picker.py::test_structural_pipeline_matches_legacy_complete_id_map \
  tests/python/ui/test_selection_overlay.py::test_structural_any_hit_matches_legacy_complete_mask
```

The recorded and locally repeated Vulkan result is `2 passed`. Compiler warnings from existing
Falcor shader modules may be printed; the reproduction succeeds when pytest reports two passing
tests and exits with status zero.

### 7. Run the complete Phase 3 UI suite

The recorded five-test gate includes supporting ScenePicker lookup/render and structural host-policy
coverage in addition to the two image-parity tests:

```bash
SLANGPY_DEVICE=vulkan .venv/bin/python -m pytest -v -s \
  tests/python/ui/test_scene_picker.py \
  tests/python/ui/test_selection_overlay.py

SLANGPY_DEVICE=cuda .venv/bin/python -m pytest -v -s \
  tests/python/ui/test_scene_picker.py \
  tests/python/ui/test_selection_overlay.py
```

Expected result for each command:

```text
5 passed
```

## Windows runtime in an already-built checkout

The clean Windows native build has extra worker-specific dependency and MSVC `/MP` safeguards and
is not replaced by the short commands below. In particular, the repository contains bare `/MP`
options: the validated worker changed them to `/MP8` and ran the outer build with `--parallel 1` so
the complete compiler process tree stayed at or below eight jobs. Do not use an unbounded build or
assume that `cmake --parallel 8` alone caps `/MP` child processes.

After building the same three source revisions in a Visual Studio 2022 Developer PowerShell, select
one backend and run the focused tests:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\external\slangpy"
$env:SLANGPY_DEVICE = "d3d12" # or "vulkan" or "cuda"

.\.venv\Scripts\python.exe -m pytest -v -s `
  tests/python/ui/test_scene_picker.py::test_structural_pipeline_matches_legacy_complete_id_map `
  tests/python/ui/test_selection_overlay.py::test_structural_any_hit_matches_legacy_complete_mask
```

Expected result for the command above:

```text
2 passed
```

Run the complete five-test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest -v -s `
  tests/python/ui/test_scene_picker.py `
  tests/python/ui/test_selection_overlay.py
```

The recorded complete-suite result is `5 passed` on each of D3D12, Vulkan, and CUDA.

## macOS status

Do not expect these runtime commands to collect a Metal case. Metal structural pipeline runtime is
not available in the current Falcor/SGL stack. Phase 3 has compile/reflection/Metal-AIR validation
on Apple M4, but that is not runtime ScenePicker or SelectionProbe coverage.

## Current interactive-sample limitation

There is no standalone structural ScenePicker/SelectionProbe example in `examples/` yet. The
Falcor editor constructs these production services, but it does not enable experimental Slang
features or select the structural API. Therefore the supported Phase 3 reproduction today is the
headless runtime test above. The earlier colorized ID-map and selection-mask images were diagnostic
visualizations of those GPU buffers, not screenshots of a live editor session.
