# Phase 3 ScenePicker and SelectionProbe samples and reproduction

This recipe starts with two real standalone samples under `examples/ui/`. Neither sample imports
pytest, Falcor's testing helpers, or code from `tests/`.

- `structural_scene_editor.py` opens the normal Falcor editor on the Cornell box. Mouse selection
  uses the production structural `ScenePicker`, and the displayed selection highlight uses the
  production structural SelectionProbe inside `SelectionOverlay`.
- `structural_scene_tools.py` is a deterministic headless example. It creates two overlapping
  quads, passes the exact GPU texture produced by a structural `ScenePicker` into a structural
  `SelectionOverlay`, verifies the selected rear quad was found behind the front occluder, and
  writes three viewable PNG files.

The focused pytest cases remain later in this document as optional regression validation.

## What the samples prove

The sample data flow is:

```text
structural ScenePicker
    -> geometry_instance_id_texture
    -> structural SelectionOverlay / SelectionProbe
    -> final highlighted RGBA texture
```

`ScenePicker` creates a structural ray-tracing pipeline and shader table, links structural
ray-generation/closest-hit and slot-zero miss stages, dispatches rays, and writes the
geometry-instance ID texture. `SelectionOverlay::draw_overlay()` dispatches structural
SelectionProbe ray-generation, any-hit, and slot-zero miss stages.

The deterministic sample's front and rear quads each contain two independently addressable BLAS
geometries, and the image includes miss pixels. It selects the rear geometry IDs directly, which
disables the optional selected-object AABB shortcut. Rays encounter and ignore the unselected front
quad before accepting the selected rear quad. This covers four geometry IDs, closest-hit output,
miss-pixel output, `ignoreHit()`, `acceptHitAndEndSearch()`, and the final overlay pixels in one
end-to-end run.

The interactive example additionally proves that Falcor's normal editor/controller bindings drive
the structural services. Its main PathTracer is intentionally unchanged; only editor picking and
selection tracing use the new pipeline API.

These samples do not cover non-zero ray-type slots with distinct sentinels, callable shaders, LSS,
or Metal runtime behavior. Metal structural pipeline runtime is unavailable in this stack.

## Run the actual samples in an already-built checkout

Run all commands below from the Falcor2 repository root. Ensure the checkout is built as described
later in this document, then expose both local Python packages:

```bash
export PYTHONPATH="$PWD:$PWD/external/slangpy"
```

### Interactive Cornell-box sample

On Linux with Vulkan:

```bash
.venv/bin/python examples/ui/structural_scene_editor.py --device vulkan
```

The window opens with `/cornell_box/tall_box_back/tall_box_back` selected. Its green highlight is
visible through the front of the tall box, demonstrating SelectionProbe. Left-click another object
in the viewport to exercise ScenePicker and change the selection. Press `F5` to toggle the editor
panels and `Escape` to exit.

For a bounded run that also saves the final post-overlay image:

```bash
.venv/bin/python examples/ui/structural_scene_editor.py \
  --device vulkan --width 640 --height 480 --spp 4 --frames 3 \
  --output output/structural-scene-tools/cornell-editor-structural.png
```

The program prints all three relevant choices explicitly:

```text
ScenePicker ray tracing: structural pipeline
SelectionProbe ray tracing: structural pipeline
Main PathTracer: unchanged (this demo only ports editor picking and selection tracing)
```

### Deterministic headless sample

On Linux with Vulkan:

```bash
.venv/bin/python examples/ui/structural_scene_tools.py \
  --device vulkan --pipeline-api structural --width 640 --height 480
```

The sample writes:

- `output/structural-scene-tools/scene-picker-structural.png`: pseudo-colored geometry IDs;
- `output/structural-scene-tools/selection-probe-structural.png`: the raw probe mask colorized green;
- `output/structural-scene-tools/selection-overlay-structural.png`: the final composited overlay.

The recorded Linux Vulkan run reported:

```text
Backend: vulkan
Pipeline API: structural
Front geometry IDs: [0, 1]
Rear geometry IDs: [2, 3]
Center pick: 0 (front geometry range)
Geometry-ID values: [0, 1, 2, 3, 4294967295]
Selected/occluded pixels: 174724
Selected pixels hidden behind the front quad: 53824
```

The final count must be greater than zero. It specifically counts pixels where ScenePicker sees a
front geometry ID while SelectionProbe reaches selected geometry behind it.

To run the same standalone example through the legacy pipeline for manual comparison:

```bash
.venv/bin/python examples/ui/structural_scene_tools.py \
  --device vulkan --pipeline-api legacy --width 640 --height 480
```

For the recorded run, all three legacy PNG files were byte-identical to their structural
counterparts.

## Exact source revisions

Use these revisions to reproduce the recorded result:

```text
Falcor2:  f4062580a80b9765567f10a7c4eff840d68ccc0a
          branch codex/structural-rt-port
SlangPy:  aa8840bc8ca644c45ea9d475f3f937b66faf8208
          branch codex/structural-rt-host-bridge
Slang:    036132fa8fbfbe2e9300a0e0edb46d0405d973d0
          branch draft/unified-pipeline-rt-api
```

The Falcor2 revision pins the SlangPy revision as the `external/slangpy` submodule.

## Optional focused regression tests in an already-built Linux checkout

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
git checkout f4062580a80b9765567f10a7c4eff840d68ccc0a
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

After building the same three source revisions in a Visual Studio 2022 Developer PowerShell, set
the local package path and launch the interactive sample on D3D12:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\external\slangpy"

.\.venv\Scripts\python.exe examples\ui\structural_scene_editor.py --device d3d12
```

Vulkan is also presentation-capable on Windows; replace `d3d12` with `vulkan` to use it. For a
headless D3D12 run that writes all three diagnostic images:

```powershell
.\.venv\Scripts\python.exe examples\ui\structural_scene_tools.py `
  --device d3d12 --pipeline-api structural --width 640 --height 480
```

CUDA/OptiX cannot present the interactive editor, but it can run the same headless sample:

```powershell
.\.venv\Scripts\python.exe examples\ui\structural_scene_tools.py `
  --device cuda --pipeline-api structural --width 640 --height 480
```

The focused regression tests remain available as a separate check. Select a backend and run:

```powershell
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

## Current sample limitations

The interactive sample needs a presentation-capable graphics backend, so use Vulkan on Linux and
Vulkan or D3D12 on Windows. CUDA/OptiX has no editor presentation surface; use the deterministic
headless sample with `--device cuda` instead. Metal structural pipeline runtime is unavailable, so
macOS remains compile/reflection/Metal-AIR coverage rather than a runnable Phase 3 sample.

The Cornell-box PathTracer in the interactive example is not yet ported to the structural API. It
only supplies the base image. The structural work demonstrated there is the production
ScenePicker-to-SelectionProbe editor interaction. The deterministic example provides the stricter
end-to-end proof, including a non-selected front hit that the structural any-hit stage ignores.
