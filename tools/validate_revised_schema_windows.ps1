# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $true)]
    [string]$StagingRoot,

    [Parameter(Mandatory = $true)]
    [string]$ReuseBase,

    [Parameter(Mandatory = $true)]
    [string]$SlangDir,

    [Parameter(Mandatory = $true)]
    [string]$ResultDir,

    [Parameter(Mandatory = $true)]
    [string]$FinalFalcorCommit,

    [Parameter(Mandatory = $true)]
    [string]$BaselineFalcorCommit
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$SlangPyCommit = "fc9713b5d93501bded86d9082f4575573f50ef01"
$SlangCommit = "29969e72bacd308672b37e23a1b2ad7ea88c5ee2"
$SlangRhiCommit = "5661193d9415fb3c84c068afb149b85ea7fe2310"
$BuildDir = Join-Path $ReuseBase "build/windows-msvc"
$Python = Join-Path $ReuseBase ".revised-schema-venv/Scripts/python.exe"
$SlangBinDir = Join-Path $SlangDir "build/Release/bin"

function Assert-NativeSuccess([string]$Step)
{
    if ($LASTEXITCODE -ne 0)
    {
        throw "$Step failed with native exit code $LASTEXITCODE"
    }
}

function Assert-FileHash([string]$Root, [string]$RelativePath, [string]$ExpectedHash)
{
    $FullPath = Join-Path $Root $RelativePath
    if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf))
    {
        throw "Missing pinned file: $FullPath"
    }
    $ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $FullPath).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedHash)
    {
        throw "Hash mismatch for $FullPath expected=$ExpectedHash actual=$ActualHash"
    }
    Write-Output "SHA256 OK $ActualHash $FullPath"
}

if ($env:CMAKE_BUILD_PARALLEL_LEVEL -ne "1")
{
    throw "CMAKE_BUILD_PARALLEL_LEVEL must be 1"
}
if ($env:CL_MPCount -ne "8")
{
    throw "CL_MPCount must be 8"
}
if ($env:_CL_ -ne "/MP8")
{
    throw "_CL_ must be /MP8"
}
if ($env:VCPKG_MAX_CONCURRENCY -ne "1")
{
    throw "VCPKG_MAX_CONCURRENCY must be 1"
}

New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null
Get-CimInstance Win32_VideoController |
    Select-Object Name, DriverVersion, PNPDeviceID |
    ConvertTo-Json -Depth 3 |
    Set-Content (Join-Path $ResultDir "windows-gpu-driver.json")

Write-Output "Native cap: one CMake project; --parallel 1; CL_MPCount=8; _CL_=/MP8."
Write-Output "Final Falcor candidate: $FinalFalcorCommit"
Write-Output "Incremental baseline: $BaselineFalcorCommit"
Write-Output "SlangPy: $SlangPyCommit; Slang: $SlangCommit; slang-rhi: $SlangRhiCommit"

foreach ($RequiredDirectory in @($StagingRoot, $ReuseBase, $BuildDir, $SlangDir))
{
    if (-not (Test-Path -LiteralPath $RequiredDirectory -PathType Container))
    {
        throw "Missing required directory: $RequiredDirectory"
    }
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf))
{
    throw "Missing validation Python: $Python"
}

$CandidateFiles = [ordered]@{
    "slang/falcor2/ui/kernels/selection_probe_structural.slang" = "0e9d3e4cf585650b8b52fd231cff93e6aca9dcae076855918e7e2f1843414845"
    "slang/falcor2/render/lights/env_map_light.slang" = "ea6c95aa05b329aaa5981ea84b57cd5630f29f6cd42293fe69f9e9f4d4401686"
    "src/falcor2/ui/selection_overlay.cpp" = "395250097189ba3dca233c1eae2ba302b3274288932a81e76ac55dd8a054ddcf"
    "src/falcor2/ui/selection_overlay.h" = "b4e3f8fef567d523d28eac83136d14b4e7adc49e878ad0c3d1621d2048a01a67"
    "tests/python/pathtracer/test_pathtracer.py" = "1583fb432472e605129afbafcceb8ffd42c66d4ed4833e8ddefe4892814f1a20"
}
$BaselineFiles = [ordered]@{
    "slang/falcor2/ui/kernels/selection_probe_structural.slang" = "ad19617fe0b0c7d724a520d0050efe4a1b374fbf8811e17bf8035195b6e92dcb"
    "slang/falcor2/render/lights/env_map_light.slang" = "c1033214b0461e8558630d77c5541449165952e19cb1e250d459f9f169a93949"
    "src/falcor2/ui/selection_overlay.cpp" = "9fc14515698bdc2e7fc3b2f85c43e91b07331bb4d42db4becbf32eadae018f52"
    "src/falcor2/ui/selection_overlay.h" = "eb5cd7fc370d20f45fcc8ab17cc4e4343b3987563f4b1a6b9a3b19c329943ce0"
    "tests/python/pathtracer/test_pathtracer.py" = "5e0e754cdb43657f183ceeea5884bcb0366cbe5402dae82100fa28f4d87756e1"
}
$PriorCandidateHashes = @{
    "slang/falcor2/render/lights/env_map_light.slang" = @(
        "fa36e325c56928173e7d3cf21f7e179e919e99e8d82e9eccef9960bdc9c9f501"
        "c53e39309108df2d9edf80cd053a7c316656df299fd799388f2ddb508e86a4cf"
    )
}

foreach ($RelativePath in $CandidateFiles.Keys)
{
    Assert-FileHash $StagingRoot $RelativePath $CandidateFiles[$RelativePath]
    $CachedPath = Join-Path $ReuseBase $RelativePath
    if (-not (Test-Path -LiteralPath $CachedPath -PathType Leaf))
    {
        throw "Missing cached file: $CachedPath"
    }
    $CachedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $CachedPath).Hash.ToLowerInvariant()
    $AllowedCachedHashes = @($BaselineFiles[$RelativePath], $CandidateFiles[$RelativePath])
    if ($PriorCandidateHashes.ContainsKey($RelativePath))
    {
        $AllowedCachedHashes += $PriorCandidateHashes[$RelativePath]
    }
    if ($AllowedCachedHashes -notcontains $CachedHash)
    {
        throw "Unexpected cached hash for $CachedPath actual=$CachedHash"
    }
    Write-Output "Cached SHA256 OK $CachedHash $CachedPath"
}
Assert-FileHash $StagingRoot "tests/python/ui/test_selection_overlay.py" "93b8190a24cf4f09fc4ea6992e25f48c7f578535e0676474856241f1c6f8d67a"
Assert-FileHash $ReuseBase "external/slangpy/slangpy/tests/slangpy_tests/test_raytracing_config.py" "1479c2091801969bb11cb1ee7ac46a5d0b510d61130e10dcef24fe33c1a54635"
Assert-FileHash $ReuseBase "external/slangpy/slangpy/tests/slangpy_tests/test_raytracing.py" "756d01798820806a15b708d177bd85e9d939e01ace6d7571361e35e3df95bee9"

$ActualSlang = (& git.exe -C $SlangDir rev-parse HEAD).Trim()
Assert-NativeSuccess "Slang revision query"
if ($ActualSlang -ne $SlangCommit)
{
    throw "Slang mismatch expected=$SlangCommit actual=$ActualSlang"
}
$ActualSlangRhi = (& git.exe -C (Join-Path $SlangDir "external/slang-rhi") rev-parse HEAD).Trim()
Assert-NativeSuccess "slang-rhi revision query"
if ($ActualSlangRhi -ne $SlangRhiCommit)
{
    throw "slang-rhi mismatch expected=$SlangRhiCommit actual=$ActualSlangRhi"
}
$SlangVersion = (& (Join-Path $SlangBinDir "slangc.exe") -version 2>&1 | Out-String).Trim()
Assert-NativeSuccess "slangc version"
if ($SlangVersion -notmatch "g29969e72b")
{
    throw "Unexpected Slang version: $SlangVersion"
}

foreach ($RelativePath in $CandidateFiles.Keys)
{
    $Destination = Join-Path $ReuseBase $RelativePath
    Copy-Item -LiteralPath (Join-Path $StagingRoot $RelativePath) -Destination $Destination -Force
    (Get-Item -LiteralPath $Destination).LastWriteTime = Get-Date
    Assert-FileHash $ReuseBase $RelativePath $CandidateFiles[$RelativePath]
}

$CandidateFiles.GetEnumerator() |
    ForEach-Object { "$($_.Value)  $($_.Key)" } |
    Set-Content (Join-Path $ResultDir "source-canaries.sha256")
@(
    "final_falcor=$FinalFalcorCommit"
    "incremental_baseline=$BaselineFalcorCommit"
    "slangpy=$SlangPyCommit"
    "slang=$ActualSlang"
    "slang_rhi=$ActualSlangRhi"
    "slang_version=$SlangVersion"
) | Set-Content (Join-Path $ResultDir "source-tuple.txt")

$ProgramFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$VsWhere = Join-Path $ProgramFilesX86 "Microsoft Visual Studio/Installer/vswhere.exe"
if (-not (Test-Path -LiteralPath $VsWhere -PathType Leaf))
{
    throw "vswhere.exe was not found at $VsWhere"
}
$VsInstall = (& $VsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1).Trim()
Assert-NativeSuccess "Visual Studio discovery"
if (-not $VsInstall)
{
    throw "Visual Studio C++ toolchain was not found"
}
$VsDevCmd = Join-Path $VsInstall "Common7/Tools/VsDevCmd.bat"
$VsCommand = '"' + $VsDevCmd + '" -no_logo -arch=amd64 -host_arch=amd64 && set'
$VsEnvironment = & $env:ComSpec /d /s /c $VsCommand
Assert-NativeSuccess "Visual Studio environment initialization"
foreach ($Line in $VsEnvironment)
{
    $Parts = $Line -split "=", 2
    if ($Parts.Count -eq 2 -and $Parts[0])
    {
        [Environment]::SetEnvironmentVariable($Parts[0], $Parts[1], "Process")
    }
}
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue))
{
    throw "cl.exe unavailable after VsDevCmd"
}

$GeneratorLine = Get-Content (Join-Path $BuildDir "CMakeCache.txt") |
    Where-Object { $_ -like "CMAKE_GENERATOR:INTERNAL=*" } |
    Select-Object -First 1
if (-not $GeneratorLine)
{
    throw "CMAKE_GENERATOR was not found in the cached build"
}
$Generator = ($GeneratorLine -split "=", 2)[1]
$Generator | Set-Content (Join-Path $ResultDir "cmake-generator.txt")
if ($Generator -like "Ninja*")
{
    & cmake.exe --build $BuildDir --config Release --target falcor2_ext --parallel 1
}
elseif ($Generator -like "Visual Studio*")
{
    & cmake.exe --build $BuildDir --config Release --target falcor2_ext --parallel 1 -- /m:1 /p:CL_MPCount=8 /p:UseMultiToolTask=false
}
else
{
    throw "Unsupported CMake generator for capped build: $Generator"
}
Assert-NativeSuccess "incremental falcor2_ext build"

$env:PATH = "$ReuseBase/build/windows-msvc/Release;$SlangBinDir;$env:PATH"
$env:PYTHONPATH = "$ReuseBase;$ReuseBase/external/slangpy"
$env:FALCOR_REUSE_BASE = $ReuseBase
$env:RESULT_DIR = $ResultDir
Set-Location $ReuseBase
& $Python -c "import slangpy as spy; import falcor2 as f2; print(spy.SLANG_BUILD_TAG); assert 'g29969e72b' in spy.SLANG_BUILD_TAG; assert f2.RayTracingPipelineAPI.structural.name == 'structural'"
Assert-NativeSuccess "final extension/compiler identity"

$ConfigTest = Join-Path $ReuseBase "external/slangpy/slangpy/tests/slangpy_tests/test_raytracing_config.py"
& $Python -m pytest $ConfigTest -v -s --device-types=nodevice "--junitxml=$(Join-Path $ResultDir 'slangpy-record-config.xml')"
Assert-NativeSuccess "structural record configuration and cache-key tests"

$SchemaScript = @'
import json
import os
import struct
from pathlib import Path

import slangpy as spy

root = Path(os.environ["FALCOR_REUSE_BASE"])
result_dir = Path(os.environ["RESULT_DIR"])
device_name = os.environ["SCHEMA_DEVICE"]
record = struct.pack("<QII", 0x1122334455667788, 96, 0)
assert len(record) == 16
device = spy.Device(
    type=getattr(spy.DeviceType, device_name),
    compiler_options=spy.SlangCompilerOptions(
        {
            "include_paths": [spy.SHADER_PATH, root / "slang", root / "external"],
            "enable_experimental_features": True,
        }
    ),
)
module = device.load_module("falcor2.ui.kernels.selection_probe_structural")
schema = module.layout.find_trace_program_schema("SelectionProbeProgramSchema")
assert schema is not None and schema.is_valid
hit_types = ["SelectionProbeHitGroup", "", "", "", "", ""]
miss_types = ["SelectionProbeMiss", "", ""]
bindings = module.structural_ray_tracing_bindings(
    "SelectionProbeProgramSchema",
    hit_types,
    miss_types,
    [],
    [list(record), [], [], [], [], []],
    [[], [], []],
    [],
)
assert len(bindings.hit_group_names) == 6
assert len(bindings.miss_entry_points) == 3
assert bytes(bindings.hit_group_record_data[0]) == record
assert all(not bytes(item) for item in bindings.hit_group_record_data[1:])
program = device.link_program([module], list(bindings.entry_points))
assert program.layout is not None
result = {
    "device": device_name,
    "api_name": device.info.api_name,
    "adapter_name": device.info.adapter_name,
    "slang_build_tag": spy.SLANG_BUILD_TAG,
    "schema": schema.name,
    "hit_record_stride": schema.hit_record_stride,
    "record_size": len(record),
    "record_hex": record.hex(),
    "program_linked": True,
}
(result_dir / f"selectionprobe-schema-{device_name}.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(result, indent=2, sort_keys=True))
device.close()
'@

$SlangPyRayTracingTest = Join-Path $ReuseBase "external/slangpy/slangpy/tests/slangpy_tests/test_raytracing.py"
$SelectionTest = Join-Path $ReuseBase "tests/python/ui/test_selection_overlay.py"
$PathTracerTest = Join-Path $ReuseBase "tests/python/pathtracer/test_pathtracer.py"

foreach ($DeviceName in @("d3d12", "vulkan"))
{
    $env:SCHEMA_DEVICE = $DeviceName
    $SchemaScript | & $Python -
    Assert-NativeSuccess "SelectionProbe direct schema materialization/link ($DeviceName)"

    $env:SLANGPY_DEVICE = $DeviceName
    & $Python -m pytest "$($SelectionTest)::test_structural_any_hit_matches_legacy_complete_mask" -v -s "--junitxml=$(Join-Path $ResultDir "selectionprobe-parity-$DeviceName.xml")"
    Assert-NativeSuccess "SelectionProbe legacy/structural parity ($DeviceName)"

    $PathTracerLog = Join-Path $ResultDir "pathtracer-parity-$DeviceName.log"
    & $Python -m pytest "$($PathTracerTest)::test_pathtracer_structural_scatter_matches_legacy" "$($PathTracerTest)::test_pathtracer_structural_analytic_scatter_matches_legacy" -v -s "--junitxml=$(Join-Path $ResultDir "pathtracer-parity-$DeviceName.xml")" 2>&1 |
        Tee-Object -FilePath $PathTracerLog
    Assert-NativeSuccess "ReferencePathTracer environment and analytic legacy/structural parity ($DeviceName)"

    if ($DeviceName -eq "vulkan")
    {
        $DriverErrorLines = @(
            Get-Content -LiteralPath $PathTracerLog |
                Where-Object { $_ -match "^\[ERROR\] \(rhi\) driver:" }
        )
        $UnexpectedDriverErrors = @(
            $DriverErrorLines |
                Where-Object { $_ -notmatch "VUID-VkShaderModuleCreateInfo-pCode-087(40|42)" }
        )
        if ($UnexpectedDriverErrors.Count -ne 0)
        {
            throw "Vulkan path-tracer run emitted unexpected driver errors: $($UnexpectedDriverErrors -join '; ')"
        }

        $LssClassification = if ($DriverErrorLines.Count -eq 0) { "not-observed" } else { "known-inherited-inline-lss-diagnostic" }
        @{
            classification = $LssClassification
            driver_error_count = $DriverErrorLines.Count
            expected_vuids = @(
                "VUID-VkShaderModuleCreateInfo-pCode-08740"
                "VUID-VkShaderModuleCreateInfo-pCode-08742"
            )
            functional_parity_passed = $true
            validation_clean = ($DriverErrorLines.Count -eq 0)
        } |
            ConvertTo-Json -Depth 3 |
            Set-Content (Join-Path $ResultDir "pathtracer-vulkan-lss-classification.json")
    }
}

Remove-Item Env:SLANGPY_DEVICE -ErrorAction SilentlyContinue
& $Python -m pytest "$($SlangPyRayTracingTest)::test_structural_raytracing" -v -s --device-types=vulkan "--junitxml=$(Join-Path $ResultDir 'record-bytes-vulkan.xml')"
Assert-NativeSuccess "Vulkan record-byte pipeline test"

$D3DRecordLog = Join-Path $ResultDir "record-bytes-d3d12-known-gap.log"
& $Python -m pytest "$($SlangPyRayTracingTest)::test_structural_raytracing" -v -s --device-types=d3d12 "--junitxml=$(Join-Path $ResultDir 'record-bytes-d3d12-known-gap.xml')" 2>&1 |
    Tee-Object -FilePath $D3DRecordLog
$D3DRecordExitCode = $LASTEXITCODE
if ($D3DRecordExitCode -eq 0)
{
    throw "The pinned D3D record-data canary unexpectedly passed; reassess the recorded gap"
}
$D3DRecordFailure = Get-Content -LiteralPath $D3DRecordLog -Raw
if ($D3DRecordFailure -notmatch "CreateStateObject" -or $D3DRecordFailure -notmatch "BaseShaderRegister=4294967295")
{
    throw "D3D record-data canary failed for an unexpected reason"
}
@{
    classification = "known-d3d-backend-gap"
    expected_failure = $true
    pytest_exit_code = $D3DRecordExitCode
    required_diagnostic = "CreateStateObject / BaseShaderRegister=4294967295"
} |
    ConvertTo-Json -Depth 3 |
    Set-Content (Join-Path $ResultDir "record-bytes-d3d12-classification.json")

Remove-Item Env:SCHEMA_DEVICE -ErrorAction SilentlyContinue

Get-ChildItem $ResultDir -File | Sort-Object Name | ForEach-Object {
    $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    Write-Output "Artifact SHA256 $($_.Name): $Hash"
}
Write-Output "Final Windows functional validation passed. D3D12/Vulkan product parity passed; the exact known D3D12 local-root record-data failure and any known Vulkan inline-LSS diagnostics were classified."
exit 0
