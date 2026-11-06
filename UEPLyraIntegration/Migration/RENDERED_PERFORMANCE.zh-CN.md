[English](RENDERED_PERFORMANCE.md) | [简体中文](RENDERED_PERFORMANCE.zh-CN.md)

<a id="rendered-frame-rate-and-cpu-comparison"></a>

# 带渲染的帧率与 CPU 对比

[H05 验收](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H05-acceptance.json)记录了本机对比结果。使用 1 个实际打包游戏进程、16 个各 20 秒的采样区块，去除边界帧后分析了 38,274 个实际 GPU 渲染帧。原生进程、独立 profiler/CPU 核对及选择器恢复均通过检查。

| 负载 | 路径 | 平均 FPS | 1% Low FPS | 整机 CPU | GameThread 毫秒 | GPU 毫秒 | 进程 CPU 毫秒/帧 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 固定场景 | 原生 | 120.56 | 79.36 | 36.92% | 3.30 | 7.57 | 49.04 |
| 固定场景 | Python | 120.39 | 78.52 | 36.72% | 3.32 | 7.58 | 48.83 |
| 每帧额外 200 次查询 | 原生 | 120.23 | 71.29 | 37.28% | 4.54 | 7.57 | 49.66 |
| 每帧额外 200 次查询 | Python | 118.26 | 66.44 | 39.85% | 8.25 | 7.60 | 53.97 |

固定场景的 4 对样本中，描述性差异区间均跨过零。FPS 为 -0.37% 至 +0.08%，CPU 为 -1.90 至 +1.30 个百分点，GameThread 为 -0.010 至 +0.052 毫秒。本次采样未分辨出该场景中的性能差异。GPU 约 7.57 毫秒、RenderThread 约 8.29 毫秒，高于 GameThread 约 3.3 毫秒，与该场景主要受渲染限制的情况一致。

合成压力负载下，Python 的 GameThread 增加 3.71 毫秒，整机 CPU 增加 2.57 个百分点，总进程 CPU 每帧增加约 4.31 毫秒，平均 FPS 下降 1.64%。对应配对描述性区间分别为 +3.47 至 +3.97 毫秒、+1.66 至 +3.35 个 CPU 百分点，以及 -3.09% 至 -0.41% FPS。该结果反映极高频率的反射/Python 决策成本，适用范围限于此合成负载。

测量对象为本机 Ryzen 7 5800X3D / RTX 3080 上的 Win64 Development 游戏包，复用已验收的 Game 可执行文件、Cook 内容容器及包内 Python。此轮通过 D3D12 离屏渲染采集时序，与 H02 的 NullRHI 计时及内存运行分开记录。编译、重新 Cook、桌面及键鼠操作均有各自的执行范围，本轮测量的是离屏 GPU 渲染。

对比只将共用的 World 策略载体在 `NativeGameplayFallback` 与 `Python` 间切换，覆盖其 damage/Pawn 策略及相机选择。其他已验收的 Blueprint 和原生 Mixin 实现固定，因此结论适用于这个策略切换点。

固定场景为 Expanse、1920x1080、Screen Percentage 100、Medium 画质、关闭 VSync、帧率上限解除。3 个 bot 的原生 Brain 停止运行，以固定战斗、重生、所有者及相机条件。两组负载分别为固定非战斗场景，以及同一场景每帧额外执行 200 次反射 Damage/Pawn 查询的合成压力。每次查询都会断言原生结果。

游戏就绪后先预热 45 秒，并交替两条路径。每种负载随后按 Native/Python/Python/Native/Python/Native/Native/Python 运行，形成 4 对 AB/BA。每个区块先执行原生 GC，在采样外等待 5 秒稳定，再测量 20 秒，最后单独刷新 CSV。原生游戏 CSV 提供 Frame、GameThread、RenderThread 和 GPU 时序。profiler 的最终表头会加入开始记录后才发现的计数器，解析器核对已有列位置，并支持早期行缺少后续可选计数器的情况。

每个区块两端各去除 2 帧。平均 FPS 为 1000 除以平均帧时。1% Low 为 1000 除以最慢 ceil(1%) 帧的平均帧时，实际卡顿也参与计算。描述性配对 bootstrap 以区块对为单位，统计重复单元由采样设计决定。

CPU 使用进程用户态与内核态 CPU 时间之和，除以实际墙钟时间和 16 个逻辑处理器，得到占整机 0–100% 的占用率，与 Windows 任务管理器的归一化方式一致。每秒独立采集的原生进程 CPU 快照需与进程内测量一致。GameThread 时序另行报告。每帧总进程 CPU 毫秒也单独列出，用于观察帧吞吐下降时单帧成本的变化。

从主仓库使用新的专属证据目录运行。

```powershell
./Validation/Run-UEP58RenderedPerformance.ps1 `
  -OutputDirectory F:/UnrealEnginePython5/.build/LyraValidation/Hardening/FreshPerf `
  -CookEvidenceDirectory F:/UnrealEnginePython5/.build/LyraValidation/Hardening/20261103/H04-Cook02
& F:/UnrealEngine/Engine/Binaries/ThirdParty/Python3/Win64/python.exe -B -X utf8 `
  Demos/UEPLyraIntegration/Tools/analyze_rendered_performance.py `
  --directory .build/LyraValidation/Hardening/FreshPerf `
  --output .build/LyraValidation/Hardening/FreshPerf/analysis.json
```

`-Pilot -WarmupSeconds 10 -CaptureSeconds 5` 使用 4 个短场景区块验证采集器。最终性能结果来自正式采样。检查项包括原生进程退出、选择器恢复、3 个已停止的 bot Brain、设置、视口、真实 GPU 时序、回调路径、查询次数、CSV/ticker 帧数一致性、独立 Windows CPU 读数，以及固定的游戏包输入。

早期 Pilot 保留了测量前发现的 3 个夹具 API 错误，分别是未反射的 Controller 命令、用浮点 getter 读取整数控制台值，以及不存在的直接 GC 包装器。夹具已改用反射 Kismet 命令和 GC 方法，以及已注册的类型化控制台 getter。第一次成功 Pilot 还发现 CSV 动态扩展表头的问题，修正只涉及纯解析器，并复用了该次原生运行记录。

CPP09 的真实 Escape/Menu 输入于 2026-11-05 单独通过。此测量的适用边界为已记录的地图、画质、硬件、系统、Development 配置和非战斗负载。战斗、其他地图、其他画质及设备、Shipping、硬件音频和通用玩法性能需要各自的证据。
