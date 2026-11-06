[English](README.md) | [简体中文](README.zh-CN.md)

<a id="uep-lyra-integration"></a>

# UEP Lyra 集成

> 当前版本 — **1.0.0**、UE**5.8.1**、引擎CPython **3.11.8**、Win64**Development/Shipping**。 [发布记录](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-1.0.0/docs/Release_1.0.0.zh-CN.md)和[支持的API](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-1.0.0/docs/Supported_API_Inventory.zh-CN.md)定义了发布范围。
> 下面标注日期的部分保留了其捕获时间证据和限制。

已接受批准的Blueprint和游戏-C++ 迁移。 【完成指标】(Migration/completion_status.json)、【进度历史】(Migration/PROGRESS.md)和每批次验收台账记录验收范围和实际运行时出处。

<a id="historical-integration-milestones"></a>

## 历史整合里程碑

此集成被分阶段写入一次性的Lyra副本。 Lyra 和 Unreal Engine 源均未编辑。 `UEPLyraBridge` 将少数本机 Lyra 生命周期观察结果和 Python 无法安全绑定到反射的、仅游戏线程的 APIs 中的一个有界写入操作：

- 体验准备就绪成为动态多播事件。
- 游戏功能状态、增强输入准备状态、能力System/Health准备状态、伤害免疫、权威、网络模式、local/remote控制器、PlayerState和典当角色以只读快照形式公开。
- 子系统及其侦听器遵循 `UWorld` 生命周期，并且 Python 探针在关闭或重新加载之前显式解除绑定其回调。在绑定体验管理器之前观察到迟到的客户端`GameState`分配。
- `ApplyAuthorityHealthDelta`仅接受游戏线程服务器权威、一个明确的local/remote玩家目标、简短的安全命令ID、不大于25的有限非零增量、非致命伤害和非过度治疗恢复。
- 接受的命令通过目标ASC调度Lyra现有的SetByCallerDamage/Heal游戏效果。桥接器不会直接写入 Health 属性，而是尊重 Lyra 的 `Gameplay.DamageImmunity`。和
- 命令IDs被消耗一次，客户端接收`RejectedNotAuthority`，并且没有网桥API默默地将客户端调用作为RPC转发。

0.8覆盖层还为已声明的UEPMixin集配置Lyra的现有`W_Healthbar_C`。 CommonUI 和 ShooterCore `Add Widgets` 操作保留小部件所有权。 Python仅替换呈现行为：它处理小部件生命周期，遵循所拥有的Pawn，订阅健康组件委托，计算标准化健康状况并调用Blueprint保留的视觉助手。专用服务器必须记录零个HUD对象或订阅。

0.8 是未发布的候选者。健康数据更新、damage/heal/death/respawn动画选择和数字插值通过真实的UMG隔离夹具。恰好一个活动演示者和关闭后零拥有的回调具有主机测试检查和当前脚本虚幻独立通道。当前源组合network/package接受仍然开放。现有清理paths/logs未发现观察到的泄漏。

<a id="09-first-runtime-bp-batch-in-development"></a>

## 0.9 第一个运行时 BP 批次（正在开发中）

[`Migration/batches.json`](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/batches.json)处的库存将246运行时候选业务分配给0.9–0.14，分别保留动画、editor/test工具和182configuration/layoutshell。这些是静态候选者，而不是迁移的或可到达的资产计数。第 1A 批是生命条加上四个武器小部件。其有界UI/native-network证据记录在批次账本中。完整版release/package门保持独立。

`Overlay/Content/Scripts/uep_lyra_hud/ammo_mixin.py`实现了武器面板Tick和触摸重装输入事件，以及三个弹药计数器的Tick、OnWeaponInitialized和SetWeaponSpecificImages。 `Overlay/Plugins/GameFeatures/ ShooterCore/Content` 包含四个示例拥有的 BP 副本。它们的接口和`PythonMixinProfile`CDO默认引用`Overlay/Content/UEPMixins`下的四个Mixin集。 Lyra/CommonUI仍然实例化原来的`W_*_C`类。没有 Python 子类替代它们。创作工具永远不会保存官方项目，这需要标记的阶段和在修改之前匹配的当前虚幻项目。

Python读取所属控制器的本机QuickBar/inventory标签计数并调用本机UMG、材料、FText和增强输入功能。库存、设备、firing/reload能力、GAS和复制仍然是原生的。 UMG layouts/materials 保留。原BP中武器名称设置器是断开的。它的占位符是有意保留的，而不是在迁移过程中引入行为更改。当前端口还保留了 BP 的 Tick 轮询。路线图的事件驱动弹药订阅工作仍然开放。

对于无需任何编译或资产保存的可重复的第一批 UI 比较，请针对已匹配的完整内容阶段运行此核心签出条目：使用 PowerShell 7。

```powershell
.\Validation\Run-UEP58FocusedWeaponHUDValidation.ps1 `
    -StageProject F:\UnrealEnginePython5\.build\LyraValidation\Full\Stage\Lyra\LyraStarterGame.uproject `
    -OutputDirectory F:\UnrealEnginePython5\.build\LyraValidation\WeaponHUD-NewRun `
    -CheckPlayableStartup
```

2026-10-13运行通过42真实-UMGoriginal-BP/Python使用持久的Interface/CDO默认值进行比较，加上严格的日志，未更改的类，四个路由器恢复，input/reference哈希值和渲染的两列帧（BP左， Python右）。重新加载按钮案例检查本机输入调度，**不是**成功的GAS重新加载。隔离的入口地图库存是确定性的固定输入，而不是真实equipment/firing或复制有效的证据。 `-CheckPlayableStartup` 启动正常的 Lyra，不带 UEP 探测标志，在本机体验加载后观察其活动状态 20 秒，然后有意仅停止该拥有的进程。它是NullRHI，不测试正常关闭或交互式控制。正常`ue_site.py`不再导入自动退出探针。验证仍然是明确的和选择加入的。

首批验收还需要真武器fire/reload、双客户端ammo/UI所有权、Pawn/weapon替换以及事件驱动的订阅清理。单独的健康网络车道无法验证这些新的弹药场景。重点武器摘要总是让full/network接受错误。

<a id="existing-validation-lanes"></a>

## 现有验证通道

仅源烟雾通道在一次性阶段禁用Lyra的内容支持启动系统，因此它可以证明UE5.8编译、模块加载、CPython3.11所有权和桥梁生命周期，而无需假装游戏有效。 `F:\LyraStarterGame\LyraStarterGame.uproject`的完整外部项目通过了严格的准备、真实体验游戏、同步多人游戏、cook/package和打包的CPython验证，而无需修改参考树。

从核心检出中，针对引擎树外部的完整项目运行现有的组合runtime/package通道：

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode All
```

`All` 执行完整的 cook/package，现在在启用 HUD 切片时调用 `HUDAudit`，并且需要预编译的交叉Actor 和渲染的 UMG 检查。当前源组合发布验收仍在等待中。使用`Standalone`或`Network`进行迭代。单独审核相关official/staged资产，无需运行时游戏：

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode HUDAudit
```

仅在声明更改后重新生成示例拥有的健康栏和 Mixin 设置资产：

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode GenerateHUDAssets `
    -Incremental
```

生成发生在一次性阶段，并且SHA-256检查证明参考`W_Healthbar.uasset`未更改。

每个完整驱动程序模式首先运行`Tests`中的主机端Python测试和核心端PowerShell合约检查。他们使用假反射对象来证明纯源资产缺失、精确回调身份、仅事件更新、旧Pawn分离、Blueprint回退、销毁和注册表清理，而无需启动虚幻引擎。运行时通道练习真实的Lyra对象。增强的精确单演示者和最终退出后检查具有主机覆盖范围，包括实际的仅CPython子进程完成，以及当前脚本的虚幻独立通道。重复完整的电流源验收。仅凭主机假货无法证明这一点。

为了在没有构建的情况下集中自我接受，请从核心检出目录运行：

```powershell
.\Validation\Run-UEP58FocusedHUDValidation.ps1 `
    -StageProject F:\UnrealEnginePython5\.build\LyraValidation\Full\Stage\Lyra\LyraStarterGame.uproject `
    -OutputDirectory F:\UnrealEnginePython5\.build\LyraValidation\Focused-NewRun
```

该脚本需要一个新的输出目录，验证标记阶段的本机source/module奇偶校验并同步当前示例脚本。它不编译C++，cook/package，保存BP或修复模块BuildIds。 `Callsite`模式在Mixin注册之前编译两个临时内存BP，并通过另一个BP的字节码验证两个同类的Actor目标。 `Visual` 打开一个隔离的真实UMG 测试窗口并记录八帧以及退出后清理。仅测试健康读取器永远不会附加到LyraPawn/ASC。死亡保险并不会扩大桥梁的权威。着色器缓存可能会被填充。专注的`All`运行两项检查并始终离开`full_acceptance: false`。

对于真正的双客户端环回网络，请使用核心检出目录的 no-build `Validation/Run-UEP58FocusedNetworkValidation.ps1` 与 `-StageProject`、新的 `-OutputDirectory` 和 `-ClientCount 2`。它运行专用服务器A和B0。然后 B0 退出，B1 重新加入。 `uep_lyra_network.py` 是选择加入的，不会在正常游戏或 commandlet 中运行。原始的单客户端探针仍然可以通过核心驱动程序的`NetworkPrecheck`使用。 `Network/All` 现在使用双客户端门。

`CapturePlayerSnapshots`公开WorldToken、PlayerToken、PlayerState身份和Controller/Pawn/HealthComponent路径。 `ApplyAuthorityHealthDeltaToPlayer` 和 `RequestPlayerRestart` 仅解析当前相同的World 弱控制器引用。 expired/foreign 代币永远不会落回给其他玩家。现有的仅角色定位保留`RejectedAmbiguousTarget`，权威、有界非致命GAS写入和命令重复数据删除保持不变。令牌是 process/World-local 测试目标句柄，而不是身份验证或 RPC API。

20阶段探针交叉检查独立读取本机快照和新拥有的运行状况委托事件。仅文件坐标ACKs。健康状况仍然通过Lyra的本机复制到达客户端。三个原生机器人满足热身，其AI大脑逻辑仅在此选择加入测试模式下停止，以避免随机枪击。每个进程必须退出，没有演示者拥有 callbacks/references. NullRHI 不建立可视化网络接受或打包网络。它还使用`-SwitchDuringAnimation`重复渲染的情况，证明在新的伤害动画后立即切换到`BlueprintFallback`会关闭Python演示器，而无需完成重新进入。 Native UMG 拥有其暂停的动画状态。后续原始 `Destruct` 调用需要核心插件的零大小原生事件回退修复。

Python 探针拥有游戏序列。在单机和打包游戏中，它等待Lyra伤害免疫结束，施加10伤害，证明相同的命令ID不能应用两次，观察90健康状况，治愈10并观察原始状态100 健康。在网络通道中：

1. 客户端调用相同的反射API并证明`RejectedNotAuthority`没有健康变化。
2. 专用服务器Python进程将损害应用于真实远程玩家的ASC并证明重复拒绝。
3. 客户端Python进程在确认服务器之前观察90处的复制运行状况。和
4. 服务器Python仅在确认后恢复健康状态，然后等待客户端Python观察到100处的复制值。

然后，两个节点都会发布一个就绪标记，并在驾驶员拥有的释放信号后面等待。只有当两个标记都存在后，任一进程才能关闭。

在运行状况序列之后，0.8生命周期阶段将替换权威的Pawn，并验证客户端呈现器在绑定新的运行状况组件之前是否删除了旧的运行状况组件。然后，它执行一次相同地图体验替换以执行真正的`LAS_ShooterGame_StandardHUD` `Add Widgets`操作teardown/recreation，然后进行第二次独立的相同地图切图。客户必须完成至少三个构造、两个破坏和一个平衡的主动演示者。更新后的验证器会拒绝多个活跃的演示者，即使计算余额也是如此。架构5写入`awaiting_shutdown`，将活动快照保留在`hud`中，并在Mixin清理后从Python`atexit`最终确定`shutdown.hud`。驱动程序需要零拥有的callbacks/references，并在进程退出后订购最终标记。该路径具有主机测试和当前脚本虚幻独立通道。新的network/package出口大门仍未得到验证。服务器参与权威/同步路径，但从不创建HUD。

每个进程在等待释放信号时都会锁存产生其就绪标记的快照。因此，提前退出一个时钟周期的客户端无法擦除服务器已经证明的远程Pawn/PlayerState/ASC状态。

游戏合约要求 `ShooterCore` 处于活动状态，并且纯内容 `ShooterMaps` 插件至少已注册，与其 `ExplicitlyLoaded`/`BuiltInInitialFeatureState=Registered` 描述符相匹配。它不会强制从Python激活功能。运行时URLs请求三个LyraAI机器人来推进真正的预热阶段。机器人使用`AModularAIController`，并且不是远程`APlayerController`目标选择器的候选者。

有关所有权表、拒绝契约和机器可读证据，请参阅[`docs/Lyra_Gameplay_Slice_0.5.0.md`](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Lyra_Gameplay_Slice_0.5.0.md)。正式结果`20260812-234501`通过了完整的`All`通道，包括打包的游戏，并报告了`full_acceptance: true`。在选择器经过强化以拒绝不明确的人类目标后，精确源结果`20260813-005436`通过了网络通道，`20260813-005835`通过了独立通道。在那次小的强化更改之后没有重建任何包。前一个结果仍然是历史包证据，后两个结果是0.5选择器更改的确切源运行时证据，而不是今天的树。

历史0.8支持记录包括HUD审核结果`20260903-032632`、干净基础生成结果`20260903-033001`和`20260903-033049`以及正式`All`结果`20260903-033426`。后者在每个UI角色上通过独立、同步server/client、BuildCookRun和打包运行时`full_acceptance: true`、CPython3.11.8、`100 -> 90 -> 100`， 3 构造 / 2 在两个体验生命周期后销毁，并且零专用服务器HUD 状态。它是与`hud_audit: null`一起运行的Win64Development、NullRHI：上面的audit/generation是单独的调用，而不是`All`中的步骤。它早于最终引导程序fix/seventh主机测试，既不是当前源版本批准，也不是渲染动画、DebugGame或Shipping证据。

第一次 2026-09-07 编辑器尝试在不匹配的模块 BuildIds 上失败。然后，官方UBT修复了两个仅元数据操作中生成的记录，无需手动 GUID 覆盖、C++ 编译、Cook或资产保存。新的严格HUD审核和当前脚本NullRHI独立通过：恰好有一个活动presenter/reference，然后在实际Python退出后，两者都为零，控制器绑定3/3和运行状况绑定6/6.保留核心验证历史记录`20260907-hud-closeout/standalone-shutdown-summary.json` 带有 script/native 哈希值和显式 `full_acceptance: false`。集成的`All`、同步网络和包检查仍然悬而未决。在2026-09-10上，`20260910-hud-closeout-integrated`集中运行通过了跨Actor路由、damage/heal/death/respawn渲染、实数插值和最终零拥有的widget/callback状态。这是presentation/routing证据，而不是原生的GAS、同步多人游戏或打包运行时替代品。

0.8 清仓仍保留在生命条上。 0.9专注于Mixin工程加上一条weapon/ammoHUD链和有界消息订阅面。剩余的运行时BP业务分配给核心路线图中的0.10–0.14，通常分5到10个BP批次，original-BP/Python差别接受。初始清单和版本分配位于`Migration/batches.json`。动画、editor/test实用程序和data/layout外壳仍然存在。 game-project C++ 业务迁移是一个单独的后续范围。死亡验证必须使用原生的Lyra游戏玩法或独立的固定装置，而不扩展桥的非致命权威合约。

2026-10-13 Batch 1A 运行时后续操作现在通过 42 BP/Python UMG 比较、四个实时Profile往返、本机消息取消和三个受控 reload/native-GC 周期来验证四个 weapon/ammo 小部件。 `WeaponNetwork08` 使用一台专用编辑器服务器和两个渲染客户端运行 19 实际输入阶段：本机 firing/GAS 重新加载、耗尽、现有拾取 entry/slot 切换、Pawn 重新启动、两次切图和客户端 exit/rejoin. 弹药和HUD 与当地业主同住。探测器不会写入inventory/ammo. 物理重叠拾取是一个单独的未经测试的场景。

`weapon_observer.py` 拥有一个只读帧采样器以及本机 QuickBar/Pawn 信号和共享订阅范围。 StatTags没有公共弹药委托。来源明确为`read-only-frame-sampler`。仅当values/ownership更改时，演示才会更新。通用范围支持位于UEP，而不是Lyra桥中。实际打包的presentation/lifetime固定装置也会在运行时插件脚本导入修复后通过。

`Migration/batches.json` 区分有界运行时验证和发布。专用打包网络保持开放：本机LyraGame不能充当LyraServer，并且混合Editor/cookedWorld分区对等体被拒绝。完整的服务器构建是一个单独的1,235操作冷计划。 CC 审核两次超时。这些是保留的限制，而不是绿色发布证据。

0.10 接下来的两个试点保留 `W_Reticle_AmmoBar_C` 和 `W_FireButton_C`，并在示例拥有的副本中保留 Interface/Mixin Set/CDO 配置。 `fire_button_mixin.py` 替换了编写的 CommonButton 绑定单击条目，用 FVector(1,1,1) 注入原始的 Fire/Fire_Auto 操作。其原始 BP 简介仍然可用。测试以编程方式调用该条目。物理touchscreen/input-widget手势行为未经认证。

`CombatHUDNetwork04`通过19原生武器阶段，两个渲染客户端，两次切图，Pawn/weapon替换和B0exit/B1重新加入。四个进程全部退出0。 A/B0/B1订阅余额17/17、13/13和3/3，最终scopes/ticker.为零，保留八张屏幕截图和本机UI/weapon比较。原始的三个武器定义**不是**使用`W_Reticle_AmmoBar`：其显式测试拥有的覆盖层从实际生产弹药计数器的WeaponInstance初始化。制造可达性的定义没有改变。 Package/physical-touch 和其他 30 候选项仍然开放。

尽管有较早的协议通过，但视觉审查发现并修复了两个问题：夹具使用UEP的滚动优先FRotator构造函数，就好像它是俯仰优先一样。本机Pitch/Roll现已报告并断言。 ASC 0/0 之前的运行状况读取，随后是相同的 100/100 属性通知，从而消除了 UI。演示者现在可以识别之前显示的零状态。 `HealthBootstrapRegression01` 涵盖恢复、正常健康动画和实时个人资料清理。示例主机测试通过111。此后续操作没有执行 C++ 编译或cook/package。较古老的产物仍然具有历史意义。

世界交互试点是保留的 `BP_GameplayEffectPad_C` 和未更改的子类上的 `uep_lyra_world.effect_pad_mixin`。八个延迟生成BP/Python 构建案例通过。 `PhysicalGAS03`在原生LyraPawn上通过了八个案例/十六个真实重叠轮，匹配damage/healing并完全消除了源效应。 Pawn瞬移，不手动输入，驱动碰撞。父结构保留一个两节点虚拟`UEPConstructEffectPad`转发器。保存下来的原有BP业务就是后备辅助体。因此，子显式父调用仅使用父路由器即可到达Python。相关类路由器防护和通用缓存指针绕过边界保留。仅编辑器增量构建、继承选择器和七个调用装置传递。主机测试在此入口通过126。 `PadNetwork02` 通过了 16 个 server-physical/native-GAS 案例，其中有两个客户，每个所有者 Health/HUD 和三个干净的退出。它不保证客户效果预测、强制焊盘复制、手动焊盘输入、生产可达性或打包。 0.10 仍在开发中。

`debug_spread_mixin.py` 迁移编写的调试扩展 Tick，同时保留本机 ComputeSpreadAngle 和准确的 Kismet 双文本格式默认值。 `DebugSpreadNetwork01`通过19阶段weapon/CombatHUD通道，其中`-DebugSpread`：自动本机小部件勾选，非零扩展，BP/Python/native文本，所有权，travel/Pawn/weapon更改并重新加入。四个出口干净。调试覆盖是测试拥有的，而不是作为生产小部件声明的。保留 8 个 PNG。本机 NoSound EarlyReflections 和 EditorDataStorage 小部件用途警告仍然存在 visible/logged. 这不是无警告或打包接受。示例主机测试通过135。这里不需要新的 C++ build/cook/package。

`weapon_reticle_mixin.py` 现在拥有三个保留的生产标线布局的几何 Tick 和键入的 ADS/elimination 订阅。原始的ADS动画链被断开，因此动画仍然是空操作。消除使用LyraPlayerState所有权并排除自杀。保留本机 UMG animation/projection/spread 执行。共享十二节点`BP_UEPGameplayMessages`只是一个类型化的VM传输适配器（原生通配符GetPayload/Broadcast），不是复制游戏业务。 `transport01`和`ReticleDifferential04`通过本地类型交付，同一支手枪上的三种布局，BP/Python几何和动画时间，owner/suicide过滤和五个最终封闭瞄准镜。主机测试通过141。核心订阅测试13。 `ProductionReticleNetwork01` 通过了 19 个本机 weapon/lifetime 阶段，并具有实际生产 Pistol/Rifle 小部件和零退出后范围。真正的IA_ADSpress/release成功于`ReticleNativeADS05`。 `ReticleNativeShotgun06`使用原生pickup/equip/fire（8->5弹药）并比较该原生霰弹枪上的每个布局。物理拾取、真杀输入、网络霰弹枪和包裹仍待处理。参考资产未受影响。主机测试现已通过148。

`open_menu_mixin.py` 迁移原始菜单按钮绑定点击。相同的本机CommonUI异步操作接收UI.Layer.Menu，输入暂停和惰性软类路径。 Python 不会首先加载该类。 `MenuDifferential04` 通过三个 Python/BP/Python 本机 open/close 循环，其中包含保留的按钮类型、初始卸载的类、干净的退出和检查的菜单 PNG。核心软类转换和八个当前 DLL 调用装置在仅模块构建后通过。物理触摸、输入令牌cancellation/resumption、生产可达性、网络菜单和包仍然是单独的验收工作。

`reticle_host_mixin.py`迁移实际生产主机的creation/clear、健康观察和可见性。本机LyraWeaponUserInterfaceTick仍然检测设备变化。原始库存片段和UMG类别保留。 `HostDifferential02`通过了八个原始BP比较，实时Profile子保存，原生Pistol/Rifle/Shotgun装备和一次性原生死亡事件处理。注入的事件并不是真正的lethal-damage/kill证明。四节点VM助手仅在清理期间删除旧的BP死亡委托。 `ReticleHostNetwork01`通过两个客户端、travel/rejoin、本机child/owner/configuration检查点和最终主机范围7/7、5/5、1/1（服务器0/0）经历了十九个阶段。屏幕截图和已知的本机警告将被保留。主机测试通过170。物理拾取、网络霰弹枪、包裹和完整的0.10保持开放。
