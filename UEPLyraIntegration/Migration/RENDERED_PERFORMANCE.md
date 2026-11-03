# Rendered frame rate and CPU comparison

[H05 acceptance](NativeGameplay/H05-acceptance.json) records the completed local
comparison: one actual packaged process, sixteen twenty-second sampling blocks,
and 38,274 analyzed GPU-rendered frames after boundary trimming. The native
process, independent profiler/CPU checks and restored selector all pass.

| Workload | Route | Average FPS | 1 percent low FPS | Whole-machine CPU | GameThread ms | GPU ms | Process CPU ms/frame |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed scene | Native | 120.56 | 79.36 | 36.92% | 3.30 | 7.57 | 49.04 |
| Fixed scene | Python | 120.39 | 78.52 | 36.72% | 3.32 | 7.58 | 48.83 |
| 200 queries/frame | Native | 120.23 | 71.29 | 37.28% | 4.54 | 7.57 | 49.66 |
| 200 queries/frame | Python | 118.26 | 66.44 | 39.85% | 8.25 | 7.60 | 53.97 |

The fixed scene's four-pair descriptive intervals include zero: FPS delta
-0.37% to +0.08%, CPU delta -1.90 to +1.30 percentage points and GameThread delta
-0.010 to +0.052 ms. This sample does not distinguish a performance difference
there. Its roughly 7.57 ms GPU / 8.29 ms RenderThread timing is substantially
larger than the roughly 3.3 ms GameThread timing, consistent with rendering
dominating this scene rather than world-policy execution.

The synthetic workload increases Python GameThread time by 3.71 ms, whole-machine
CPU by 2.57 percentage points, and per-frame total process CPU by about 4.31 ms.
Average FPS falls 1.64%. The corresponding paired descriptive intervals are
+3.47 to +3.97 ms, +1.66 to +3.35 CPU percentage points and -3.09% to -0.41% FPS.
The pressure result shows the cost of very frequent reflected/Python decisions;
it does not describe normal combat or prove that every game is unaffected.

This follow-up measures the current Win64 Development package on the local
Ryzen 7 5800X3D / RTX 3080. It reuses the accepted Game executable, cooked containers
and packaged Python. There is no C++ compilation, recook, desktop, keyboard or
mouse operation. D3D12 renders offscreen; this is separate from H02's NullRHI
timing and memory run and does not measure monitor presentation.

The comparison changes only the shared world-policy carrier between
`NativeGameplayFallback` and `Python`. This covers its native world decisions,
including damage/Pawn policies and camera selection. All other accepted Blueprint
and native mixin implementations stay fixed. It is not a comparison against an
unmodified Lyra build or a switch disabling every Python binding.

The fixed scene is Expanse, 1920x1080, screen percentage 100, Medium scalability,
VSync off and an uncapped frame limit. Three bots have their native brains stopped
to keep combat, respawns, owner and camera conditions stable. There are two separate
workloads: the fixed noncombat scene, and the same scene with 200 additional
reflected Damage/Pawn queries per frame. The second is synthetic pressure, not
ordinary player activity. Every query asserts its native result.

The actual game warms up for 45 seconds after readiness, alternating both routes.
Each workload then runs Native/Python/Python/Native/Python/Native/Native/Python,
four AB/BA pairs. Each block has a scheduled native GC and five-second settling
period outside sampling, twenty seconds of measurement, and a separate CSV flush.
Native game CSV files provide frame, GameThread, RenderThread and GPU milliseconds.
The profiler's final header includes counters discovered after recording began;
the parser verifies that existing column positions were preserved. It does not
discard early rows merely because they lack later optional counters.

Two boundary frames at each end are removed. Average FPS is 1000 divided by mean
frame time. The 1 percent low is 1000 divided by the mean of the slowest ceil(1
percent) frame times. This keeps actual stalls rather than deleting them as
outliers. Block pairs are the units for the descriptive paired bootstrap interval;
thousands of correlated frames do not become independent repetitions.

CPU is process user+kernel CPU time divided by wall time and sixteen logical
processors: 0-100 percent of the whole machine, matching the normalization used
by Windows Task Manager. Native process CPU snapshots collected independently
once per second must agree with the in-process measurement. GameThread time is
also reported separately; neither metric is inferred from memory usage or FPS.
Total process CPU milliseconds per frame are included as well, because lower
frame throughput can lower the CPU percentage even when each frame costs more.

Run the entry point with an unused owned evidence path:

```powershell
./Validation/Run-UEP58RenderedPerformance.ps1 `
  -OutputDirectory F:/UnrealEnginePython5/.build/LyraValidation/Hardening/FreshPerf `
  -CookEvidenceDirectory F:/UnrealEnginePython5/.build/LyraValidation/Hardening/20261103/H04-Cook02
& F:/UnrealEngine/Engine/Binaries/ThirdParty/Python3/Win64/python.exe -B -X utf8 `
  Demos/UEPLyraIntegration/Tools/analyze_rendered_performance.py `
  --directory .build/LyraValidation/Hardening/FreshPerf `
  --output .build/LyraValidation/Hardening/FreshPerf/analysis.json
```

`-Pilot -WarmupSeconds 10 -CaptureSeconds 5` validates the collector using four
short scene blocks. Pilot timings are not final performance conclusions. Native
process exit, selector restoration, three stopped bot brains, settings, viewport,
real GPU timing, callback routes, query counts, CSV/ticker frame agreement,
independent Windows CPU readings and frozen package inputs are all checked.

Initial pilots retained three harness API errors before measurement: an
unreflected controller command, a float getter applied to integer console values,
and an unavailable direct GC wrapper. The harness now uses the reflected Kismet
command/GC methods and the registered typed console getters. The first successful
pilot also exposed the CSV writer's expanding headers; only its pure parser was
corrected, without repeating that native process.

CPP09 actual physical Escape/Menu input remains user-deferred. This measurement
does not establish combat, another map, graphics preset, GPU, operating system,
Shipping, hardware audio or universal gameplay performance.
