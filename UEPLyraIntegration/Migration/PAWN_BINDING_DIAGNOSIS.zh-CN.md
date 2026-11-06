[English](PAWN_BINDING_DIAGNOSIS.md) | [简体中文](PAWN_BINDING_DIAGNOSIS.zh-CN.md)

<a id="pawn-binding-investigation-and-spawn-cue-cleanup"></a>

# Pawn 绑定调查和 Spawn Cue 清理

原来的间歇性规范-Pawnempty-ASC/Health0问题仍然存在**开放，未修复**。 Batch233 修复了运行当前近战矩阵时发现的单独的 Spawn Cue 生命周期错误。参见[证据分类账](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/Acceptance/233-spawning-cached-target-cleanup-and-current-melee-diagnosis.json)。

<a id="historical-binding-evidence"></a>

## 具有约束力的历史证据

在`20261018-melee-replica-readiness/FullPythonTimeline02`中，四个B0模拟代理之前是健康的，保留了PlayerState的规范Pawn并报告了GameplayReady，然后失去了extension/Health/actorASC绑定。他们的PlayerStateHealthSet仍然包含100个。本机详细日志显示本地替换 Pawns C5/C6/C7/C8 使用旧的 C2/C3/C1/ C0 Pawns 初始化相同的 ASCs 作为现有头像。这是一个对等点自己捕获的log/history的加入，而不是跨对等点线路身份的证明。

未更改的官方原生源码解释了这个边界：`ULyraPawnExtensionComponent::InitializeAbilitySystem`未初始化现有化身的扩展。未初始化的委托调用`ALyraCharacter::OnAbilitySystemUninitialized`，这会清除健康组件绑定。对于 null HealthSet，`ULyraHealthComponent::GetHealth` 返回 0，即使 PlayerState 属性仍包含 100。这将故障范围从丢失运行状况复制值缩小到Pawn/ASC所有权转换。它不能证明为什么更换Pawns是created/retired或识别生产修复。进一步的诊断必须捕获creation/retirement出处，而不是手动写入Health或初始化ASC。

<a id="separate-spawn-cue-error-fixed"></a>

## 修复了单独的 Spawn Cue 错误

当前`Native04ExitIdentity`完成了所有20个authority/40查看器混战行并且所有三个进程都退出了0，但是严格的日志门拒绝了真正的`spawning_cue_mixin.OnRemoval`TargetActor转换错误。缓存的目标可能已经无效，因此在效果停用、缓存清除和订阅取消之前引发材质参数调度。

该修复将 null 传递给本机网格助手以获取无效的缓存目标。这些本机助手明确对 null 不执行任何操作。实时目标排序和保留的 TargetActor/Timeline 字段保持不变。删除继续停用效果，清除两个缓存，取消团队观察者并解除绑定部分。颜色更新、时间轴更新和网格查询覆盖相同的缓存目标边界。强制无效目标主机回归验证了此清理。它们不被声明为额外的本机被破坏目标对。

<a id="current-bounded-verification"></a>

## 当前有界验证

`Native05DestroyedTarget`使用当前的SDK217，一个专用编辑器服务器和两个真实客户端。所有 20 个original/Python 权威案例、40 查看器行和四个本机敌对 100 伤害命中均通过，包括原始本机预测 Cue 过滤器。所有三个进程和独立的语义门 exit0 都具有严格的干净日志。惰性construction/BeginPlay/EndPlay观察不会预加载角色或写入其CDO，并恢复原始类。提示观察转发并恢复现有的生产Profile处理程序。接受的当前捕获没有规范的 healthy-attribute/empty-binding 行。这次成功的运行并不是稳定性或原始比赛修复声明。

保留所有四个早期失败的组：过时的 Cue 观察者前提条件、外部瞬态共享冲突、丢失的退出令牌 run_id 以及真正的 Spawn Cue 错误。精确的阅读器测试练习替换间隙、独占文件访问、已发布的 JSON、错误的 JSON、不相关的 I/O 错误和拥有的退出标识。无需 C++、Engine/Blueprint 编辑、编译、cook/package 或完整版本接受。

<a id="native-stack-capture-baseline-batch235"></a>

## 本机堆栈捕获基线 (batch235)

`20261023-native-construction-stack/Native01` 将显式 `-UEPReplicaNativeConstructionStacks` 选项添加到现有的惰性诊断中。每个construction/EndPlay/破坏事件最多捕获96个本机当前线程帧。符号解析发生在 Unreal 退出后，在单独的每个 PID 离线上下文中，使用现有的匹配本地 PDB。检查模块指纹、PESizeOfImage、地址算术和PDBmatch/GUID/age。不涉及调试器、目标 DLL 执行、符号下载或本机游戏修改。

所有三个进程都退出0并且original20-authority/40-viewer混战门通过。这 65 个堆栈包含 39 个构造调用和 26 个EndPlay 调用。权威建设达到`SpawnDefaultPawnFor`/`RestartPlayer`。客户端建设通过ActorChannel处理达到`UWorld::SpawnActor`。 EndPlay 达到原生破坏。在此健康捕获中未观察到Blueprint重新实例化、构建重新运行或重复。这并不排除那些机制运行失败的情况。没有重现规范的empty-binding/takeover行，因此原始问题仍然是**open，未修复**。捕获可用于未来受影响的复制。不需要重复的完整构建或广泛回归。请参阅[ledger235](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/Acceptance/235-native-pawn-construction-and-retirement-stack-provenance.json)。

<a id="historical-sdk-counterfactual-and-separate-bootstrap-repair-batch236"></a>

## 历史SDK反事实和单独的引导修复（batch236）

存档的 DLL 与失败的历史捕获的 ED133E... 哈希值完全匹配。它的本地 PDB 匹配。旧的 DLL 在短的隔离阶段路径中传递 current20-authority/40-viewer 矩阵，并捕获具有零规范空绑定行的原生生命周期堆栈。这一成功的反事实并不排除timing/load-order原因或证明任何Pawn/ASC修复。

在任何 Pawn 观察之前，第一个长隔离阶段在解释器路径设置中崩溃。它的确切源保留TCHAR_TO_UTF8临时指针并达到空Py_DECREF。当前217 DLL独立丢失了配置的长UnicodeScriptsPath。修复SDK启动函数中的转换生命周期和Python错误处理，保持搜索顺序和327导出不变。一个插件编译加上两个链接就足够了。引擎保持不变。然后，确切失败的 Unicode 固定装置将通过，normal/long-ASCII/shared-interpreter 模式和真正的本机反射也是如此。固定的SDK的近战组也通过了所有三个出口0。这修复了启动路径，不是原​​来的**打开，没有修复**绑定问题。早期候选项口普查证据仍处于历史待定SDK出处刷新。这种有界检查和健康重试都不会关闭完全迁移。请参阅[ledger236](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/Acceptance/236-python-bootstrap-path-conversion-lifetime-and-sdk-counterfactual.json)。

<a id="current-delayed-client-reproduction-and-retired-pawn-identity-batch240"></a>

## 当前延迟-客户端复制和退役-Pawn身份（batch240）

`20261025-reset-boundary/Native01DelayedB` 使用当前固定引导SDK 重现原始的四个规范空绑定行。仅B0的进程启动延迟了8秒。游戏计时器、生命值和ASC绑定未写入。武装 case4 时，近战组失败，所有进程都终止。 256 条记录的诊断限制保持不变。这 256 个快照的不同之处仅在于移动时钟和诊断校正后作为一个稳定绑定重播。没有声称成功的游戏矩阵或比赛修复。

47 个解析的本机堆栈包括五个 `ULyraGameplayAbility_Reset` 调用。对于 B0，晚期本地对象 C5/C6/C7/C8 具有旧版 actor GUIDs100/50/78/24，与服务器的重置和退役 Pawns 匹配。已经存在的规范客户端Pawns有GUIDs200/198/196/202，也被确认为健康的当前Pawns在权威机构上具有相同的PlayerStateGUIDs104/54/82/4.Actor名称永远不会在对等方之间用于身份识别。每个延迟退休的Pawn都会初始化持久的ASC，取代健康的当前Pawn，然后在同一时钟周期内接收本机ActorChannel清理。其EndPlay清除ASC头像。规范电流 Pawn 与健康的 PlayerState HealthSet 保持未绑定状态。 Creation/retirement 堆栈达到 ActorChannel/UWorld 生成和破坏。这是当前重现故障的具体根源。历史上的C5/C6/C7/C8标签本身并不能确定它们是哪一代服务器。

较晚退役的Pawn已经在BeginPlay有一个ASC，而它的PlayerState仍然命名为健康当前Pawn。 Native Hero 初始化不等待规范模拟-Pawn 选择。建议的 8 行 `CanChangeInitState` 防护添加了等待。现有的本机 OnRep 回调重新检查初始化。候选项未被应用或编译。游戏项目 C++ 被当前迁移范围保留到稍后阶段，因此此修复的单独验证正在等待用户的范围决定。没有介绍手动ASC/Health修复。请参阅[ledger240](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/Acceptance/240-delayed-client-retired-pawn-guid-takeover-reproduction.json)。
