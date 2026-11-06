[English](README.md) | [简体中文](README.zh-CN.md)

<a id="native-gameplay-migration"></a>

# 原生游戏迁移

第一个批准的范围是CPP-001到CPP-015在`../cpp_batches.json`。早期的Blueprint验收仍然是一个单独的已完成范围。

当前结束：所有 30 个随后选定的候选者都在其确认的范围内被接受（29 个生产替代品和 1 个能力案例）。 [CPP09实际窗口验收](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP09-acceptance.json)在用户解锁桌面后于2026-11-05完成。批注保留其历史验证边界。 [完成索引](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/completion_status.json)记录当前组合结果。

CPP-016到CPP-018现在有单独的只读[条目和资产预检](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP16-18-preflight.json)和[建议的批次计划](../CPP16_18_PREFLIGHT_REVIEW.md)。那里没有声称有业务替换或运行时验收。第一阶段计数保持不变。用户随后选择了这三组。它们的执行和单独的production/capability计数实时存在于[扩展跟踪器](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/cpp_extended_batches.json)中。

CPP01 取代了连胜、淘汰链和助攻规则。原生 Gameplay Message订阅及其关闭仍保留在 C++ 中。四个原生回调进入反射的`BlueprintNativeEvent`函数。持久类选择`Python`实现或保留的`NativeFallback`主体。

`CPP01-message-rules.patch` 是确切的源更改。该转换检查原始源普查哈希值，并仅写入标记的、独立复制的验证项目。官方的Lyra项目是只读参考。原始的条纹和链Blueprint类、默认值和图表仍然保留。 Assist 使用一个薄的 Blueprint 子类。共享荣誉ActionSet仅更改辅助组件参考，保留其server/client角色。

按顺序运行主存储库的验证入口点：

1. `Validation/Run-UEP58NativeMessageBuild.ps1` 仅生成 ShooterCoreRuntime 标头和 compiles/links 使用接受的本机依赖项的模块。
2. `Validation/Run-UEP58NativeMessageAuthoring.ps1` 生成并检查三个声明，保留原始类默认值和图形语义。
3. `Validation/Run-UEP58NativeMessageValidation.ps1` 比较合成消息的真实本机回调调度。它检查浮动累积、广播顺序、可重入辅助清除、精确的本地时钟边界和侦听器清理。
4. `Validation/Run-UEP58NativeMessageNetworkValidation.ps1` 使用专用服务器和两个实际客户端。原生GAS伤害和HealthSet死亡必须产生助攻、五连杀、快速连锁、分数和所有者通知。它不会伪造动词消息、生命值、伤害免疫或分数统计数据。

每次运行都需要一个新的证据目录。当流程运行时，输入被冻结，并带有存档的脚本和控件。失败的尝试将被保留。实时 JSON 必须通过`uep_lyra_network_io.read_json`读取，因此观察不能阻止Windows原子替换。此批次中的任何测试都不会建立另一个平台、配置、包或其余的 C++ 候选者。

<a id="cpp02-team-selection"></a>

## CPP02：团队选择

[CPP02 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP02-acceptance.json) 涵盖选择玩家团队和人口最少团队计算。两个本机策略事件和一个薄反射设置器位于`CPP02-team-rules.patch`中。 setter 调用原始原生 `SetGenericTeamId`，保留其通知。团队创建、体验回调、权威规则和two/four-team配置蓝图仍然保留。

团队验证入口点是主存储库的 `Validation` 目录中的 `Run-UEP58NativeTeamBuild.ps1`、`Run-UEP58NativeTeamAuthoring.ps1` 和 `Run-UEP58NativeTeamValidation.ps1`。仅编译受影响的两个LyraGame统一单位。未改变的单元被重复使用。 `-Families Four` 在两队家庭结束后仅重新运行四队家庭。

六个native/Python案例涵盖人口相等、人口不等、不活跃玩家、观众、原四队IDs、无配置队伍。检查本地团队通知和赛程恢复情况。四队地图有一位天然的本地所有者。三个临时本地PlayerState演员提供了人口固定装置，但随后被摧毁。这并不要求进行四所有者网络测试。实际的dedicated-server/two-client运行使用`Run-UEP58NativeMessageNetworkValidation.ps1 -ValidateTeam`和团队资产证据。它验证 11 个自然bot/owner 分配、平衡群体以及受影响的 CPP01 伤害、分数复制和通知管道。

<a id="cpp03-bot-count-names-and-removal-choice"></a>

## CPP03：机器人数量、名称和删除选择

[CPP03 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP03-acceptance.json) 涵盖正常和控制点机器人生成器。 Python 处理有效计数、剩余名称选择、后备名称和随机删除索引。本机代码仍然创建控制器、初始化玩家、重新启动Pawns、施加自毁伤害并销毁控制器。随机选择调用原生 RNG。性能测试生成器保留其自定义 Blueprint 创建图和本机回退，如原始 Blueprint 测试工具排除一样。

使用主存储库的 `Run-UEP58NativeBotBuild.ps1`、`Run-UEP58NativeBotAuthoring.ps1` 和 `Run-UEP58NativeBotValidation.ps1` 入口点。编译会重建LyraGame单元1/2并重用单元3中接受的CPP02团队对象。为两个生产系列运行Native/Python，验证缺少的控制器配置、默认值和URL计数优先级、zero/negative计数、名称耗尽、九个本机removals/deaths和非空Python状态清理。没有明确的 RNG 序列或单独的PIE编辑器覆盖接受。

实际的三点运行将`-ValidateBots`和机器人资产证据添加到`Run-UEP58NativeMessageNetworkValidation.ps1`。它验证了九个自然创建和命名的机器人，以及受影响的 CPP01 和 CPP02 damage/notification/team 门。

<a id="cpp04-player-start-selection"></a>

## CPP04：玩家开始选择

[CPP04接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP04-acceptance.json)涵盖TDM距离选择和一般spectator/fallback选择规则。两个策略事件保留本机启动发现、弱缓存修剪、从这里播放首选项、冲突查询和TryClaim/expiration计时器。保留的TDM最大距离行为和平局顺序被保留。 Python 调用原生物理和原生 RNG。

主存储库入口点是`Run-UEP58NativeSpawnBuild.ps1`、`Run-UEP58NativeSpawnAuthoring.ps1`和`Run-UEP58NativeSpawnValidation.ps1`。该构建使用新的基本导入库编译两个受影响的 LyraGame 单元和派生的 ShooterCore 单元。十一个native/Python案例练习了真实的empty/partial/full碰撞配合，distance/ties，声称的后备，观众，候选项疲惫，以及普通的本地RestartPlayer。无需写入私有启动缓存即可恢复夹具参与者和状态。常量引用数组调用使用现有的本机输出 ABI 帮助程序来显式提取 ReturnValue。

实际的对等运行将 `-ValidateSpawning` 和生成资产证据添加到共享网络入口点。两个Profile都进入本机启动选择回调22次。 CPP01–CPP03 damage/notification/team/bot 门保持启用状态。

<a id="cpp05-quickbar-selection-and-pickup-grants"></a>

## CPP05：快速栏选择和拾取补助金

[CPP05 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP05-acceptance.json) 涵盖forward/backward 循环、第一个空闲插槽和template/instance 授予订购。四个策略事件保留本机服务器插槽RPC、设备所有权、OnRep广播、库存快速阵列和复制子对象。现有的快捷栏Blueprint保留其graphs/defaults.精简清单Blueprint替换了一个ShooterCore组件引用，保留其角色标志和其他组件数据。

使用`Run-UEP58NativeInventoryBuild.ps1`、`Run-UEP58NativeInventoryAuthoring.ps1`、`Run-UEP58NativeInventoryValidation.ps1`和`Run-UEP58NativeInventoryNetworkValidation.ps1`。共享头依赖项需要所有三个LyraGame统一单元。引擎和ShooterCore二进制文件被重用。十四个native/Python边界情况保留了原始的未设置向后索引行为。实际静态pickup/interface调用保留模板顺序和堆栈计数。两个Profile都通过两个实际拥有客户端的 12 个本机 GAS 事件周期、匹配权威设备、本机 OnRep 通知、快速数组计数、所有者隔离、回滚和真实客户端退出障碍。

官方的`FLyraInventoryList::AddEntry(ULyraInventoryItemInstance*)`仍然是`unimplemented()`。非空的现有实例授权保留了这个原始的本机限制。他们的转发顺序有主机检查，而不是运行时接受。零库存保护是本机执行的。空接口防护未更改并经过源审核，因为当前的 UEP 接口转换器无法将 `None` 编组为脚本接口。没有声明新的软件包或平台。

<a id="cpp06-native-spawner-orchestration"></a>

## CPP06：原生生成器编排

[CPP06接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP06-acceptance.json)涵盖拾取条件、可用性和效果顺序、冷却时间reset/completion以及预定的重叠重试。本机代码保留两个计时器句柄、计时器scheduling/clearing、复制可用性和OnRep、重叠检测、网格更新和EndPlay清理。原始weapon/abilityBlueprint资产逐字节保持不变。他们现有的 Set 获得本机策略处理程序。显式别名保留所有八个先前接受的 Blueprint Python 注册入口点。

使用主存储库的 `Run-UEP58NativeSpawnerBuild.ps1`、`Run-UEP58NativeSpawnerAuthoring.ps1`、`Run-UEP58NativeSpawnerValidation.ps1` 和 `Run-UEP58NativeSpawnerNetworkValidation.ps1`。仅编译LyraGame单元1/3。单元2、ShooterCore、SDK，并且引擎二进制文件被重用。 C++ 和 Python 实现中的五个防护案例、实时计时器完成、冷却重入、固定Pawn 的计划重叠重试以及挂起计时器销毁传递。

两个Profile都保留了可接受的 Blueprint Python 层，因此此比较隔离了三个 C++ 规则。 C++ 集提供 `Python` 和 `NativeFallback`。早期的full-Blueprint后备组合在混合C++阶段不被接受。其失败的运行和重新编译的资产快照将保留在分类帐中。早期的全阶段Blueprint验收仍然是单独的。

专用服务器和两个实际所有者在原始关卡演员上传递36物理拾取场景。这些包括默认的十秒冷却时间、完整的插槽、重复的refill/full弹药、重装守卫、新的重复实例、修复、失败消息、inventory/equipment复制、本机计时器调度、所有者隔离和HUD/observer清理。客户使用NullRHI。该批次未声明可见渲染和新包。

<a id="cpp07-accolade-notification-and-queue-policy"></a>

## CPP07：荣誉通知和队列政策

[CPP07 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP07-acceptance.json) 涵盖CPP-012/013: channel/player 过滤、注册表序列分配、已完成加载排序、位置和取消标记、display/pop 顺序和清理队列重置。七个类型化原生事件选择原始 C++ 或Python 策略。两者都保留了三种公认的BlueprintPython表示方法。注册表获取、本机资产流、侦听器所有权和计时器调度保持本机。

隔离源补丁还会在销毁时清除显示计时器，并拒绝来自早期小部件构建生成的registry/asset回调。十一个配对案例通过，包括在小部件重建之前取消的实际待处理资产和注册表请求。原始的FText、图标、Blueprint图表、默认值和继承均被保留。仅现有的 Set 资产发生变化。

原生伤害网络通道通过专用服务器和两个实际所有者传递两个Profile：六个GAS伤害规格，五个死亡，一个助攻，四个 A 奖项，没有一个 B0 奖项。两个实现组具有相同的队列和表示计数。每个NullRHI客户端都会创建一个由其实际玩家拥有的原始主机小部件。这验证了真实的生产通知，并不声称自然的HUD结构或可见渲染。所有widget/class根和听众均已释放。仅重建ShooterCore统一单元。所有LyraGame、SDK和引擎对象都被重用。使用主存储库的 NativeAccolade 构建、创作、验证和 NetworkValidation 入口点。失败的装置和网络尝试仍记录在验收分类帐中。

<a id="cpp08-native-interaction-orchestration"></a>

## CPP08：本机交互编排

[CPP08 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP08-acceptance.json) 涵盖CPP-014。两个原生事件路由指示器removal/addition、default/specified软小部件选择、选项顺序和第一个选项触发到C++或Python。六个已接受的 Blueprint Python 方法在 C++ 比较中保持固定。现有的 Blueprint 后备Profile和 Explorer 回归也会通过。保留的 GA_Interact 字节、类默认值、图形语义、本机 scan/grant/input 任务和继承保持不变。只有其 Set 资产才能获得本机策略Profile。

本机适配器保持接口不透明，保留卸载的软类路径，自定义有效负载，组装ActorInfo，并触发GAS。 UE5.8.1当前忽略TriggerAbilityFromGameplayEvent中提供的ActorInfo参数并使用ASCowner/avatar.这两个路由保留该行为并分别验证自定义的有效负载目标。本批次不更换发动机。

隔离的本机装置记录实际的interface/GAS结果。他们的输入适配器执行一次Lyra的虚拟规范输入调度。通用 PressInputID 路径还会发出一个事件并复制在 Lyra 中分派的事件。这些固定源在可分发覆盖层之外进行版本控制，并且仅编译到一次性验证阶段。 SDK/bridge 和引擎二进制文件被重用。

Native/Python 边界情况、现有资源管理器activation/scan/press/rearm/end 以及两个Profile中的两个实际客户端所有者均通过。每个所有者发送三个本地输入，其中一个没有选项。本地预测和权威各自记录了两次定制的交互，并且没有外部目标激活。新的规范、任务、参与者、选择器和根都被清理了。重建LyraGame 单元1/2 并重新使用单元3。仅本体见证修复重建单元2单独。这里没有声称新的厨师、打包、物理键盘、渲染或平台接受度。

<a id="cpp09-escape-request-policy-actual-input-accepted"></a>

## CPP09：Escape请求政策（接受实际输入）

`CPP09-escape-rules.patch` 将本机HUD 的转义请求公开为一个`BlueprintNativeEvent`。保留的C++主体和Python策略使用原始软菜单类和原生`UI.Layer.Menu`流式推送。 CommonUI 的动作绑定、异步加载、玩家所有权、输入路由器和 device/lifetime 委托仍然是原生的。所有四个原始HUD配置外壳均保留其默认值、图形、可视化树和继承。他们共享一套新的Mixin 套装。

[CPP09 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP09-acceptance.json) 通过唯一选择的隔离游戏窗口关闭 14 个真实的 OS Escape 输入。七个native/Python菜单循环进入本机菜单输入模式并恢复原始模式和忽略输入标志。两级切图destroy/rebuild本地HUD。所有十四个before/after窗口对都是散列固定的。本机和Python菜单以及最终恢复的HUD也作为评论图像包含在内。进程正常退出，恢复selectors/profileclasses/roots，并清空Menu栈。此验收不会重复任何构建或Cook。

[CPP09 进度](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP09-progress.json) 保留了早期实施检查点`accepted=false`。七个无头open/close循环跨越两个Profile和两个本机级别切图通过菜单class/layer/owner、激活、停用、所需的菜单配置、观察到的输入状态等效性、HUDdestruction/rebuild和恢复检查。

本地构建编译LyraGame单元1/3并重用单元2、SDK、桥、ShooterCore和引擎二进制文件。审查补丁包括原始源丢失的-EOF-换行标记，并在与`core.autocrlf=false`一起应用时逐字节地重现编译后的源。其仅格式修复会在证据存档中保留初始构建补丁。

`Validation/Run-UEP58NativeEscapeValidation.ps1 -Headless`在两个一次性的CommonUI世界中运行单独的策略通道。它直接调用选定的native/Python事件和本机小部件停用。只有这个无头装置将运行时Game/Menu堆栈转换设置为零持续时间，恢复它们或验证它们的世界在退出时释放它们。创作的资源不会改变。它的合约无法满足实际窗口输入门。尽管菜单需要 `Menu` 配置，但屏幕外操作路由器仍保持在 `All` 状态。实际窗口接受单独验证菜单模式接管。无头报告无法证实这一点。

使用新的证据和现有的 Build01、Assets01 和 Fixtures01 摘要，在没有 `-Headless` 的情况下为实际窗口通道运行相同的入口点。该通道保留了原始的转换持续时间，并且需要十四次真正的 Escape 键按下、可见的菜单观察、两次行程、本机输入恢复以及 HUD destruction/rebuild. 之前锁定的桌面尝试仍然保留。成功的2026-11-05运行结束了CPP09和所有十五个第一阶段候选者。

```powershell
$root = 'F:/UnrealEnginePython5/.build/LyraValidation/CppGameplay/20261101-CPP09'
& Validation/Run-UEP58NativeEscapeValidation.ps1 -Headless `
  -BuildEvidenceDirectory "$root/Build01" -AssetEvidenceDirectory "$root/Assets01" `
  -FixtureEvidenceDirectory "$root/Fixtures01" `
  -OutputDirectory 'F:/UnrealEnginePython5/.build/LyraValidation/CppGameplay/20261102-CPP09/HeadlessNew'
```

在未更改的原始步枪 Niagara 资产内进行Python初始化之前，完整的未煮熟的射击场景之前失败了。 UI-仅世界隔离该批次的行为。他们不建立完整的射击渲染或修复该资产。没有进行新的 Cook、包、引擎编译或平台验收。

<a id="cpp10-native-initial-item-stat-application"></a>

## CPP10：本机初始项目统计应用程序

[CPP10 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP10-acceptance.json) 涵盖CPP-016。原始清单创建回调在应用任何统计数据之前选择本机循环或两个 Const 项目定义事件。 Python 以本机映射迭代顺序读取类型化的 Tag/Count 数组，避免 Python 字典中不支持的可变结构键。原始实例化片段、它们的顺序、默认值、图形和父类都被保留。五个项目定义使用恒定的Profile选择器。

二十个definition/repeat创作，十个分阶段的empty/zero/negative/duplicate/max案例，两个缺少定义的本机回调，以及一个处理回调无重放保护通道。区分三种量产武器和两种保留的unused/prototype定义。后者不要求自然的游戏玩法覆盖。一次性边界固定装置在 Overlay 之外进行版本控制。没有声称接受异常注入。

专用服务器和两个实际客户端传递两个初始化Profile。每个Profile创建四个服务器拾取创建，每个都输入选定的回调一次。客户端接收相同的本机复制标签堆栈，而无需运行本地初始化。每个Profile有 12 个本机快捷栏周期，可保留所有者隔离、OnRep/equipment 行为和库存恢复。在此比较期间，之前接受的库存和快捷栏策略在Python中保持固定。

一个独立的阶段保留 CPP09 以供其等待窗口验收。编译器依赖项需要两个共享声明头的三个LyraGame单元。添加分阶段夹具重建单元1/2。其车身修复单独重建单元2，重复使用UHT和单元1/3.SDK，桥梁，ShooterCore，并且重复使用引擎二进制文件。使用主存储库的NativeStats构建、FixtureBuild/FixtureRepair、验证和NetworkValidation入口点。

<a id="cpp11cpp12-native-tag-stack-costs"></a>

## CPP11/CPP12: 原生标签堆栈成本

[共享的七文件补丁](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP11-12-tag-stack-costs.patch)保留本机成本对象并通过拥有的Blueprint功能路由数字决策。上下文包含键入的值，没有ActorInfo/spec指针进入Python。本机代码仍然评估数量curves/levels，截断数量，解析项目或PlayerState，写入失败标签，并删除权威上的堆栈。原始的AdditionalCosts调用者控制排序、快速失败检查和OnlyApplyOnHit。已处理的Python应用返回，没有本机重播。

三个现有的 mixin 集保留了之前接受的 Python 行为，并添加了 `NativeCostFallback` 以进行仅成本比较。旧的 `BlueprintFallback` 和五个配置的原始项目成本子对象保持不变。三种实际武器类型具有网络覆盖。 HealthPickup_Unused 和 NetShooter_PROTO 具有直接的原生成本配置覆盖，没有自然播放声明。

该矩阵在两个Profile中每种都有18场景，包括丢失目标、本机curve/truncation、失败输出、非权威、命中过滤和多重成本。然后，服务器和两个客户端执行真实的预测射击、本机伤害、单一权威扣除、堆栈复制和所有者隔离，同时先前的武器Python实现保持固定。

CPP12没有配置原始播放器消费者。它的接受涵盖了阶段性的仅成本能力和附加于实际拥有武器的临时玩家成本。额外的通道观察致命的GAS死亡、原生重生、强制化身EndPlay、第二个Pawn替换、保留的PlayerState/stacks和原生ASC化身绑定。它重复了新的Pawn的成本比较。已知的强制阿凡达装备差距使用原生快捷栏empty/back选择，保留插槽成员资格。库存恢复使用实际的生命周期后基线。未要求原厂respawn/inventory 维修。

本机编译器依赖项选择所有三个 LyraGame 单元一次。夹具本体修复完成单位2/3。独立的USTRUCT注册包括需要单独的单元1，重用UHT和单元2/3.两个批次共享该二进制文件。稍后Python-仅修复再使用它。诊断历史记录具有 128 条目限制，由 320 本机回调检查。在验证它们唯一的策略文件差异是这个确切的诊断绑定行之后，将重用以前的矩阵。

使用主存储库的 NativeCost 构建、创作、验证、ProductionValidation、DiagnosticsValidation 和 NetworkValidation 入口点。 `-Weapons pistol -Respawn` 选择额外的生命周期通道。 FixtureRepair 和 RegistrationRepair 保留失败的构建证据并重用成功的输出。本机固定装置和生成的可处置资产保留在 Overlay 之外。 CPP09 的精确实际窗口阶段仍然保留。不添加异常注入、新平台、完整引擎构建、cook/package或物理输入声明。

[CPP11验收](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP11-acceptance.json)记录生产项目-成本替换。 [CPP12能力验收](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP12-acceptance.json)记录了零个原始玩家消费者和成功的independent/native-network生命周期装置。

<a id="remaining-approved-groups-and-cpp13-checkpoint"></a>

## 其余获批准的团体和 CPP13 检查点

用户明确要求继续工作，直到所有确认的更换完成。在`../cpp_remaining_batches.json`中选择CPP-019到CPP-030。 CPP09实际窗口输入由用户延迟。其他小组继续。

[CPP13进度](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP13-progress.json)记录28实际网络输入跳转试验和12原生null/validActorInfo/Avatar准入探测。之前的 Blueprint Python 策略保持不变，而新的本机跳转规则会切换。角色观察器增强并恢复现有的生产Profile。显式的本机清理防护可避免在Profile清理期间重新进入已停止的Python路由器。私人车身修复重用UHT和单元2/3，单独编译单元1。

这是一个已实施的检查点，而不是最终的CPP-019接受：下一个死亡批次必须在重生后验证取消和操作。六个文件共享补丁还为下一批提供默认禁用的 death/reset 接缝。接口原型确认当前 mixin API 拒绝原生 UClasses。剩余的纯本地所有者需要Blueprint保单承运人。 SDK/bridge、引擎、ShooterCore以及保留的CPP09阶段保持不变。

<a id="cpp13-15-accepted-lifecycle-replacements"></a>

## CPP13-15 接受生命周期更换

[CPP13 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP13-acceptance.json) 在28 input/physics 试验后关闭了四个真正的死亡取消和新阿凡达跳跃交叉检查。 【CPP14验收】(CPP14-acceptance.json)记录了20致命网络试验，四次有活跃ordinary/protected见证人的原生自毁试验，以及两个native/Python原创竞技场两秒死亡任务。之前的 BP Python 规则保持不变，原生 GAS 上下文、等待、预测和复制仍然存在。 [CPP15 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP15-acceptance.json) 记录12 原始本机重置请求、owning/foreign 客户端隔离、键入的原始重置负载、repeat/pending 请求、完成时的非活动重置以及跨重生的受保护见证人。

支持的适配器是世界拥有的Blueprint策略对象。直接原生UClass mixin 注册仍然被SDK拒绝。较早的接口探测被保留作为失败的证据。四种类型的上下文边界情况和实际网络重置路径验证了替换。仅为此适配器重建了 LyraGame 单元 1/2 和 UHT。单元3、SDK、桥梁和发动机被重复使用。 CPP16-24 继续。 CPP09 实际桌面输入仍然是用户延迟的。

<a id="cpp16-18-accepted-world-policies"></a>

## CPP16-18接受的世界政策

[CPP16](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP16-acceptance.json) 记录 70 前端上下文案例、native/Python/default Profile中的实际离线启动以及由固定装置提供的本机初始化成功/失败回调。在线会话结果未经测试。连接结果和取消选择是有界类型上下文检查。本机流程句柄、异步小部件推送、弱回调和委托删除仍然存在。

[CPP17](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP17-acceptance.json)记录了28部分选择案例、natural/developer/作弊抑制、第一等价删除、实际Reset/possession、重复通知和清理。四次网络重置试验提供了八个独立的客户对实际装饰演员和网格物体的观察。在释放任一客户端之前，模板会在权威确认屏障内恢复。失败的临时-PlayerState清理和观察者竞争尝试仍然存在。

[CPP18](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP18-acceptance.json)记录了8个class/null边界情况，原始PawnData默认值，实际能力相机优先级，外来手柄保护以及本地GAS能力端的恢复。相机blend/collision实现保持原生。升级测试的策略类后，默认前端和摄像头烟雾消失。共享构建编译LyraGame单元1/3并重用单元2。 SDK，桥和发动机不变。初创公司选择通过48重点测试。 CPP19-24仍在进行中。 CPP09 桌面输入仍然是用户延迟的。

<a id="cpp19-24-accepted-remaining-policies"></a>

## CPP19-24接受剩余保单

默认 `Python` Profile (`rule_policies.PawnPython`) 接受并启用最后六个批准的组。之前的世界策略、重置和Blueprint替换仍然启用。所有 600 类型化边界都会通过，包括精确的 int64 重放时间戳、未知操作本机路由和有界跟踪。

| 分类帐 | 原生生命周期证据 | 明确的限制 |
| --- | --- | --- |
| [CPP19](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP19-acceptance.json) | 实际 connection/pairing 回调、own/foreign 用户、合并本机代码和恢复的特征 | 由夹具提供的回调输入。没有物理控制器断开连接 |
| [CPP20](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP20-acceptance.json) | 保留0/1/2/5、delete/requery时的临时本机内存流，真正的故障停止回调和清理 | Keep/live 标记使用类型化上下文。没有现有的录音或游戏回放 |
| [CPP21](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP21-acceptance.json) | 实际的HDR/LDR和加载混合方法，本机只读资源和状态保护 | 不接受声音输出 |
| [CPP22](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP22-acceptance.json) | 友方伤害被格挡，敌方伤害10。四项权威试验和八项独立客户健康观点 | 保留本机GAS/transport。默认手枪分别证明真实预测和复制伤害 |
| [CPP23](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP23-acceptance.json) | 两个真正的本地玩家，16本地GAS每个轮廓夹子，原始炸弹input/cost/repeat/refund | 夹具属性写入在未更改的输入阶段之前恢复。无操作系统输入 |
| [CPP24](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP24-acceptance.json) | 实际的PlayerState/Experience数据和human/bot权限。四个本地重置试验，八个独立的生成类视图 | 保留本机生成、加载、所有权和初始化 |

默认前端，Pawn选择，两人attributes/input和四把原版手枪prediction/damage一起试玩。初创公司选择通过51测试。私有属性固定装置记录Slate的回复并验证未更改的炸弹/属性：零范围无头SceneViewport可以为其中性角色设置返回Handled。然后它独立地进入原始增强输入操作。传统输入线束本身没有变化。 Python 重播策略明确拒绝无效的负保留，而不是尝试删除。

共享本机构建更改了所有三个 LyraGame 单元、一个 TopDownArena 单元和 LyraGame UHT 输出。主体修复重用UHT和成功的Lyra单元1/2.留在引擎目录中的可选内存流是未注册的5.8.0二进制文件。它永远不会被加载或注册。其当前的5.8.1源代码被编译为一个私有测试模块，并且仅在高级阶段注册。添加所需的本机导入后，初始链接失败会重用已编译的对象。发动机manifest/binaries、SDK、桥和老CPP09舞台保持不变。 972 受保护的输入已验证。未添加完整引擎构建、cook/package、新平台、物理设备或声音输出声明。

所有30入选的候选者均在其备案范围内实施并接受。 CPP-018 仍然仅具有能力，原始消费者为零。 CPP09的实际桌面Escape/Menu门于2026-11-05完成。所有三个范围跟踪器现在都同意合并完成指数。
