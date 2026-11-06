[English](REPRODUCE_NATIVE.md) | [简体中文](REPRODUCE_NATIVE.zh-CN.md)

<a id="reproduce-the-current-native-migration"></a>

# 重现当前本地迁移

使用已检出的主存储库及其在 Windows 上匹配的 `Demos` 修订版、经过审查的 UE5.8.1 引擎以及可工作的 Development 二进制文件、其 CPython3.11、Visual Studio C++ 工具和原始版本Lyra参考项目。此工作流程不会安装引擎或更改原始项目。接受的目标是Win64Development。其他平台，Shipping和物理输入是分开的。

从主存储库中，选择`.build`下未使用的阶段和证据路径：

```powershell
./Validation/Run-UEP58NativeReproduction.ps1 `
  -EngineRoot F:/UnrealEngine `
  -ReferenceProject F:/LyraStarterGame `
  -StageRoot F:/UnrealEnginePython5/.build/LyraValidation/CppGameplayExtended/FreshRun/Lyra `
  -OutputDirectory F:/UnrealEnginePython5/.build/LyraValidation/Hardening/FreshRun `
  -UsePrecompiledEngine `
  -MaxParallelActions 3
```

入口点制作独立的 source/content 副本，从 15 个版本化配方中组合所有 63 当前生产 C++ 输出，并暂存当前的 SDK、桥、Python、Blueprint 资产和本机验证装置。它将最终暂存文件与有序的 original/overlay/patch 组合进行比较。之前的`Binaries`、`Intermediate`、缓存和编译结果均被排除。拥有的描述符启用SDK/bridge并禁用AndroidFileServer以及仅供参考的RuntimeTests/ShooterTests插件，与可接受的生产阶段相匹配。这可以避免启用不相关的、不可用的引擎测试模块。它审查项目的 23 生产模块的 compile/link 操作，拒绝阶段外的任何输出，针对现有引擎构建这些模块，并使用未更改的引擎 BuildId 仅在其新 DLL 旁边写入加载程序清单。完整目标元数据刷新还将触及现有的引擎清单。明确的项目模块选择可以保护引擎。入口点在新阶段运行 13 个真实的原生exception/recovery案例。受保护的引擎指纹和所有冻结的构建输入在验收前都会经过检查。不执行操作系统桌面或键盘控制。

`-PrepareOnly` 在编译和运行时停止。它的 `prepare.json` 可以通过 `-PreparedStageReport` 传递给以后的调用。如果源在第一次构建之前发生变化，`Tools/prepare_native_reproduction.py --refresh-unbuilt` 将创建一个新的准备报告，同时保留其父证明。它拒绝已经包含编译器输出的阶段。

失败的构建保留其阶段和日志。当这些源和引擎指纹未更改时，将失败尝试的 `summary.json` 与 `-ResumeBuildFrom` 一起传递，并使用新的证据目录以增量方式继续相同的新阶段。这不会从另一个阶段导入结果。 `-UsePrecompiledEngine` 是installed/precompiled 引擎工作流程的显式选项。 `-NoEngineChanges` 保持启用状态。

对于在包含测试插件配置之前创建的准备工作，`--configure-production` 会生成一个新报告，保存之前的描述符并仅更改这两个启用的标志。恢复门接受准确记录的配置派生，同时仍然拒绝其他staged/source更改。

游戏交付通过以下单独的门使用相同的结果阶段：

1. `Run-UEP58PackagedNativeFixtureAuthoring.ps1` 创建三个仅阶段类型化消息观察器并验证生产资产是否未更改。
2. `Run-UEP58CurrentLyraGameBuild.ps1` 构建 Game 目标，它使用与 Editor 目标不同的编译设置。
3. `Tools/plan_native_hardening_package.py` 固定完整的原始246-资产迁移库存、当前overlay/scripts/maps 以及三个观察者。
4. `Run-UEP58MigrationCookPackage.ps1` 烹饪并归档这些准确的输入，并将实际的集装箱清单与库存进行比较。
5. `Run-UEP58PackagedNativeValidation.ps1` 直接执行包的内部`LyraGame.exe`，用于exception/recovery 和正常的离线前端流程。
6. `Run-UEP58PackagedNativeNetwork.ps1` 作为权威机构和两个真实客户端为每个 Damage 和 Pawn 保单系列执行相同的包。

在新的编辑器阶段通过后，接下来准备观察者和游戏构建，然后运行包交付入口点。使用未使用的证据路径。入口点拒绝替换已关闭的证据。

```powershell
$nativeStage = 'F:/UnrealEnginePython5/.build/LyraValidation/CppGameplayExtended/FreshRun/Lyra/LyraStarterGame.uproject'
$nativeEvidence = 'F:/UnrealEnginePython5/.build/LyraValidation/Hardening/FreshRun'
./Validation/Run-UEP58PackagedNativeFixtureAuthoring.ps1 `
  -StageProject $nativeStage -OutputDirectory "$nativeEvidence/H04-Fixtures01"
./Validation/Run-UEP58CurrentLyraGameBuild.ps1 `
  -StageProject $nativeStage -OutputDirectory "$nativeEvidence/H04-GameBuild01" `
  -MaxParallelActions 3
./Validation/Run-UEP58NativePackageDelivery.ps1 `
  -StageProject $nativeStage -OutputDirectory $nativeEvidence
```

第一个游戏配置在项目内编译其运行时库，与编辑器模块分开。随后的 package/runtime 检查该构建的重用。厨师明确选择经过审查的`UnrealEditor-Cmd.exe`，而不是要求来自仅模块复制版本的编辑器目标收据。失败的厨师可以保留其冻结的计划并使用新鲜的`-CookAttempt`和`-ReusePackagePlan`。成功的本机运行时叶不会重复修复，仅修复纯门。

打包的游戏可执行文件通过`?listen`支持监听权威。其`-server`开关不提供Editor专用进程。驱动程序使用本机 Development 命令删除主机 LocalPlayer 并保留两个真实的远程客户端。一个单独的纯检查器期望保留监听UI/local装饰性完成，同时保留所有其他重置、RPC、所有权、恢复和独立的客户端视图断言。这些结果不构成专用服务器目标声明。游戏传输使用本机 RPC。文件仅安排试验和ACKs。

打包的检查比较当前 Python 有效负载、游戏可执行文件和容器。他们还检查实际装载的 CPython DLL，其配置的主目录和暂存运行时接收文件以拒绝源引擎运行时回退。除了精确之外，每个依赖项哈希都是严格的 UTF-8 BOM/CRLF 等价于分阶段 INI 文本。当只有纯粹的契约需要单独审查时，原始失败摘要和原始本地报告保持不变。没有同行报告被重写。仅凭熟稔的表现并不能证明每个原始候选项的行为。 CPP09的独立实际桌面 Escape/Menu 接受已通过 2026-11-05。这些 headless/package 门保留其自己的范围。
