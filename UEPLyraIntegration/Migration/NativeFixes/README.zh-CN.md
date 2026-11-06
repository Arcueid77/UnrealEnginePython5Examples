[English](README.md) | [简体中文](README.zh-CN.md)

<a id="isolated-lyra-simulated-proxy-initialization-guard"></a>

# 隔离的Lyra模拟代理初始化防护

用户在2026-10-26上批准了这款原生游戏-C++后续。它与原始的 246 Python 候选者是分开的。官方`F:/LyraStarterGame`保持不变。该补丁仅适用于标记的一次性验证阶段。

`LyraHeroComponent-simulated-proxy-owner.patch` 在 DataAvailable -> DataInitialized 转换之前添加八行。模拟代理会等到其PlayerState的本机Pawn指向它，然后再绑定持久能力系统。权威和自主初始化保留其现有路径。守卫从不写入生命值或手动初始化能力系统。

构建驱动程序检查原始源指纹，仅应用此插入，并重用该阶段生成的 MSVC 响应文件。它编译包含HeroComponent的一个统一单元并执行两个LyraGame链接步骤。引擎二进制文件、NetCoreobject/import库和UEP/bridgeDLL受指纹保护。没有引擎重建、Cook或打包。

从核心存储库中，使用带有 `Validation/Run-UEP58LyraPawnInitGuardBuild.ps1 -OutputDirectory <build-folder>` 的新私有输出文件夹，然后是 `Validation/Run-UEP58LyraPawnInitGuardValidation.ps1 -OutputDirectory <run-folder> -BuildEvidenceDirectory <build-folder>`。这两个文件夹必须位于工作区`.build`目录下。该阶段必须已经具有匹配的生成构建命令和接受的SDK。这是一个增量刷新驱动程序。

Batch246 记录了两次新的 dedicated-server/two-client 运行，第二个客户端在八秒后启动，并且两个客户端立即启动。每个都通过了20original/Python权威交互和40复制查看者检查。十二个捕获的模拟代理等待在规范初始化之前保持未绑定状态。没有观察到规范的GameplayReady/healthy-attribute/empty-binding行。旧的失败游戏记录仍然完好无损。

确切的较早退役的通道序列取决于时间并且没有确定性地重放。这些运行证明了观察到的初始状态行为和受影响的交互矩阵，而不是任意的网络稳定性。原始的官方来源问题仍被记录，而其来源未经修改。完整版本、包、演示和迁移验收保持独立。请参阅`../Acceptance/246-isolated-native-pawn-init-guard-and-network-regression.json`。
