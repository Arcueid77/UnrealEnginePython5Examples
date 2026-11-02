# Lyra C++ 业务迁移确认清单

候选清单日期：2026-10-31。2026-11-01 用户确认先提交现有改动，再按推荐顺序逐步执行。

本轮执行 **CPP-001 至 CPP-015，共15个候选函数组，分9批**。
CPP-016 至 CPP-030 是另外15个需要先验证入口或运行条件的候选；2026-11-02 已选入
CPP-016～018，见第二阶段进度。随后用户要求持续推进直到全部完成，CPP-019～030 已全部选入，见第三阶段进度。
这里的候选按业务函数组计数，同一 C++ 文件可以包含多个候选；文件中的其他实现继续承担原生职责。

当前执行范围、批次状态和验收账本见 [C++ 批次进度](cpp_batches.json)。
源码台账保留10月31日候选提案的初始状态和指纹；实际实施状态以批次进度为准。
原246个蓝图候选及22项验收保留原记录，新阶段独立统计。

## 扫描范围

参考源码为本机 `F:/LyraStarterGame`。本轮拟支持 UE 5.8.1、CPython 3.11、Win64 Development。

| 模块 | 路径缩写 | C++ 实现文件 | 头文件 | 构建规则 |
| --- | --- | ---: | ---: | ---: |
| LyraGame | LG | 225 | 232 | 1 |
| ShooterCoreRuntime | SC | 12 | 14 | 1 |
| TopDownArenaRuntime | TA | 5 | 5 | 1 |
| 合计 | | **242** | **251** | **3** |

LG 指 `Source/LyraGame`；SC 指 `Plugins/GameFeatures/ShooterCore/Source/ShooterCoreRuntime`；
TA 指 `Plugins/GameFeatures/TopDownArena/Source/TopDownArenaRuntime`。
ShooterExplorer 和 ShooterMaps 没有独立 Source 目录。LyraEditor 的26个源码及构建文件、
ShooterTestsRuntime 的18个源码及构建文件按编辑器或测试模块保留。
Engine 和 CommonGame、CommonUser、GameplayMessageRouter、GameSettings 等通用插件继续提供原生能力。

[源码台账](cpp_source_inventory.json)逐文件记录路径、SHA256、行数、候选归属与保留理由，
并定位30个候选的65个函数符号。242个实现文件中，13个包含建议先执行的候选，
14个仅包含条件候选，215个按模块职责归为原生保留。

这是完整的指定模块文件扫描和候选函数定位，其他文件采用模块职责分类，
并非逐函数的完整语义审计。实际调用入口、可达性和参数传递在对应批次确认；
“保留原生”也不表示这些文件永远不能继续拆出规则。

## 接口使用规则

已有 UFUNCTION 在参数和返回值受支持时直接从 Python 调用。现有可覆写事件优先复用。
普通 UFUNCTION 的 C++ 直接调用和未反射函数，需要确认真实调用点，必要时在业务边界
增加类型明确的事件或适配器。仅添加 UFUNCTION 标记不能让原生直接调用自动进入 Python。

现有 Mixin 通过持久化蓝图类承载。已有配置蓝图可复用；原生实例或不可蓝图化类型
需要先确定薄蓝图子类、实例事件或其他明确适配方式。纯原生类型不能直接套用这一假设。
新增接入口必须由原调用链实际经过，再用真实运行证明 Python 执行及原生回退路径。

静态函数、RPC、委托签名、latent 函数和可变引用保持各自已记录的边界。
需要迁移其业务时，使用普通实例事件或明确的非 RPC 业务入口；原生复制、预测和调度职责继续保留。
默认复用现有 UEP 绑定；确需补通用能力时，在该批次中单列 API 改动及受影响回归。

## 建议先执行的15个候选

| 编号 | 原生函数组 | Python 负责 | 接入和原生职责 |
| --- | --- | --- | --- |
| CPP-001 | SC `UElimStreakProcessor::OnEliminationMessage` | 非自杀击杀的连杀累计、奖励标签选择、被击杀者连杀清零 | 原生监听回调增加类型明确的事件入口；消息监听和注销保留 |
| CPP-002 | SC `UElimChainProcessor::OnEliminationMessage` | 按实际配置时间窗重置或累加连击、选择奖励消息 | 保留原生服务器时钟来源；新增事件入口；时间窗比较和边界与原版一致 |
| CPP-003 | SC `UAssistProcessor::OnDamageMessage`、`OnEliminationMessage` | 按目标累计伤害贡献，排除击杀者，生成助攻结果并清理该目标记录 | 保留原生伤害和击杀消息来源，两个业务回调接入 Python；广播复用现有类型适配器 |
| CPP-004 | LG `ULyraTeamCreationComponent::ServerChooseTeamForPlayer`、`GetLeastPopulatedTeamID` | 旁观者分支、有效队伍人数统计、最少人数及相同人数时的编号选择 | 原生继续设置队伍身份、创建队伍对象和复制状态；为决策提供只读输入及选择结果入口 |
| CPP-005 | LG `ULyraBotCreationComponent::ServerCreateBots_Implementation` | 默认数量、编辑器覆盖和 URL 参数的优先级、生成循环 | 复用现有 BlueprintNativeEvent；原生 SpawnOneBot 继续创建和初始化 Controller/Pawn。无服务器代码的客户端占位分支保留 |
| CPP-006 | LG `ULyraBotCreationComponent::CreateBotName`、`RemoveOneBot` 的选择段 | 名字池、耗尽后的命名、待移除机器人选择 | 为命名和选择增加接入口；保留 UE 随机源、RemoveAtSwap 语义以及原生自毁、销毁顺序和原有行为限制 |
| CPP-007 | SC `UTDM_PlayerSpawningManagmentComponent::OnChoosePlayerStart` | 按敌人距离、出生点占用及备用路径选择出生点 | 原生负责占用、碰撞和实际重生；原签名含可变数组引用，接入口传递受控只读快照并返回选择结果 |
| CPP-008 | LG `ULyraPlayerSpawningManagerComponent::ChoosePlayerStart`、`GetFirstRandomUnoccupiedPlayerStart` 的规则段 | 旁观者选择、可用候选分组、随机和回退顺序 | 原生保留缓存维护、Play From Here、占用查询及 TryClaim；Python 不直接改写原生候选缓存 |
| CPP-009 | LG `ULyraQuickBarComponent::CycleActiveSlotForward`、`CycleActiveSlotBackward`、`GetNextFreeItemSlot` | 跳过空槽、正反循环、首个空槽选择 | 查询和调用现有 UFUNCTION；确认所有生产调用点。SetActiveSlotIndex 继续走原生服务器 RPC，装备和复制保留 |
| CPP-010 | LG `UPickupableStatics::AddPickupToInventory` | 模板与既有实例的遍历顺序、数量和入包编排 | GetPickupInventory、AddItemDefinition、AddItemInstance 继续使用原生接口。静态函数不作为 Mixin 目标；迁移调用方或增加明确实例入口 |
| CPP-011 | LG `ALyraWeaponSpawner::AttemptPickUpWeapon_Implementation`、`ResetCoolDown`、`OnCoolDownTimerComplete` 的业务段 | 拾取条件、发放成功后的可用状态流程、冷却结束及再次检查的编排 | 复用现有事件；给未反射的必要操作提供窄接口。原生保留计时器句柄、调度、复制、OnRep、碰撞和网格更新 |
| CPP-012 | SC `ULyraAccoladeHostWidget::OnNotificationMessage`、`OnRegistryLoadCompleted` 的规则段 | 目标频道和玩家过滤、请求编号、加载结果进入队列的规则 | DataRegistry、资产异步加载和取消保留；完成回调传递拥有明确生命周期的类型化结果，不能泛用反射读取未反射字段 |
| CPP-013 | SC `ULyraAccoladeHostWidget::ConsiderLoadedAccolades`、`ProcessLoadedAccolade`、`DisplayNextAccolade`、`PopDisplayedAccolade` | 按序显示、位置标签、取消标签、队列推进和显示时长选择 | 复用 CreateAccoladeWidget/DestroyAccoladeWidget 事件；原生保留资源加载、定时器及必要对象所有权；补齐序号等未反射字段的明确数据出口 |
| CPP-014 | LG `ULyraGameplayAbility_Interact::UpdateInteractions`、`TriggerInteraction` 的编排段 | 默认或专用指示器选择、增删顺序、当前选项及首项选择 | 已有 UFUNCTION 用于调用；真正替换需处理原生调用入口。扫描任务、原生接口 CustomizeInteractionEventData、ActorInfo 构造和 GAS 触发保留在明确适配器内 |
| CPP-015 | LG `ULyraHUDLayout::HandleEscapeAction` | Escape 菜单选择及推入 UI 层的请求 | 原生保留 CommonUI 输入绑定和异步界面加载；验证真实输入进入 Python、输入恢复和控件销毁 |

CPP-011 是原生刷新台父类的编排，CPP-012/013 是原生奖励宿主的规则，
CPP-014 是原生交互技能的选项编排。原来已迁移的刷新台蓝图业务、奖励控件蓝图和
交互技能蓝图继续作为依赖测试，不能重复算作新迁移完成量。

## 建议批次及对照验证

批次按共同调用链和共享接入口组织。进入每批后，先定位实际类、CDO、生产调用方和接口，
再冻结该批函数范围。需要拆分时保留原编号及对应关系，记录新增子项和理由。

| 批次 | 候选 | 主要对照 | 必须保持的结果 |
| --- | --- | --- | --- |
| CPP01 | CPP-001 至 CPP-003 | 实际伤害和击杀产生原生消息；专用服务器、双客户端及原生机器人 | 连杀累计和死亡清零；实际 CDO 连击时间窗前、等于、后的分支；助攻伤害累计、击杀者排除和目标记录清理；每次只广播一次；原生/Python 结果及所有权一致 |
| CPP02 | CPP-004 | 已有玩家、新加入玩家、旁观者、断线和重连；双客户端 | 无队伍、空队伍、人数相同、无效和 inactive 玩家；选择结果及原生队伍复制一致 |
| CPP03 | CPP-005、CPP-006 | 默认及覆盖数量、名字池耗尽、增减机器人、切图 | 覆盖优先级、随机调用与交换移除语义、Controller/Pawn 初始化及销毁顺序一致；保留原有死亡动画中断等基线限制 |
| CPP04 | CPP-007、CPP-008 | 空、部分占用、满、已认领出生点；敌我、旁观者、真实死亡后重生 | 返回候选、回退顺序及原生 claim 行为一致；同一出生点争用和实际落点正确 |
| CPP05 | CPP-009、CPP-010 | 空槽、全满、正反切换、重复拾取、模板及实例入包；双客户端 | 原生 RPC、装备切换、数量、所有权及复制一致；真实调用链只执行一次 |
| CPP06 | CPP-011 | 发放失败/成功、冷却期间重入、冷却结束、站在刷新台上再次检查、销毁；双客户端 | 可用标记、计时、再次拾取、复制及表现一致；原生计时器清理正确，已有刷新台蓝图回归通过 |
| CPP07 | CPP-012、CPP-013 | 不同玩家/频道/位置、异步乱序、失败、取消标签、连续显示、销毁及重建 | 显示顺序、取消关系、数量、时长和对象生命周期一致；没有重复监听、重复显示或销毁后回调，已有奖励控件回归通过 |
| CPP08 | CPP-014 | 无选项、单/多选项、默认/指定控件、目标定制 Payload、实际交互；双客户端 | 选项、指示器、事件目标、预测和权威结果一致；已有 Explorer 交互回归通过 |
| CPP09 | CPP-015 | 实际 Escape 输入、打开/关闭菜单、重复请求、切图及重建 | UI 层、输入暂停/恢复、触发次数和清理一致；原生界面加载仍正常 |

第一批的默认设计为保留三个处理器的原生消息注册和注销，
在连杀、连击、助攻伤害、助攻击杀四处业务回调增加类型明确的事件入口。
原生实现作为显式对照模式保留，Python 模式接管规则及其状态。
异常作为失败记录，不能异常后再执行原生规则造成重复结算。
初期用独立进程比较两种模式，不把运行中切换有状态规则纳入默认验收。

## 另外15个需要先验证入口或运行条件的候选

下列候选不排入上面的9批。确认时可以选入全部或指定编号；一旦选入，入口原型和
适用场景验证就是该候选批次内的工作。入口不成立时保留失败证据及具体阻塞原因。

| 编号 | 原生函数组及拟迁规则 | 先解决的问题 | 对照重点 |
| --- | --- | --- | --- |
| CPP-016 | LG `UInventoryFragment_SetStats::OnInstanceCreated` 的初始属性表应用 | 片段为 Instanced 原生对象，当前基类没有声明 Blueprintable；先确认事件承载方式和 CDO 片段替换范围 | 实际实例创建、各初始标签栈、重复创建、装备和复制；定义数据仍保留 |
| CPP-017 | LG `ULyraAbilityCost_ItemTagStack::CheckCost`、`ApplyCost` 的消耗规则 | 原签名含 ActorInfo 指针、能力句柄和可变失败标签；需要上下文快照、明确结果及原生写回 | 实际装备技能的充足/不足、数量截断、失败标签、预测、服务器只扣一次 |
| CPP-018 | LG `ULyraAbilityCost_PlayerTagStack::CheckCost`、`ApplyCost` 的消耗规则 | 同上，并确认 PlayerState 访问和原生权威扣除入口 | 玩家标签栈、失效玩家、重生、更换 Pawn、双客户端结果 |
| CPP-019 | LG `ULyraGameplayAbility_Jump::CanActivateAbility`、`CharacterJumpStart`、`CharacterJumpStop` 的原生编排 | 区分现有跳跃蓝图逻辑与原生父类；先验证 native virtual、GAS 上下文和结束入口 | 真实输入、落地、取消、死亡/重生和预测；移动组件继续原生实现 |
| CPP-020 | LG `ULyraGameplayAbility_Death::ActivateAbility`、`EndAbility`、`StartDeath`、`FinishDeath` 的编排 | 原生 GAS 结束、阻断、取消和健康组件回调次序必须先能观察和对照 | 真实伤害致死、自毁、重复通知、取消、重生、双客户端；不能只看 Python 回调次数 |
| CPP-021 | LG `ULyraGameplayAbility_Reset::ActivateAbility` 的重置流程 | native virtual 与实际 Reset 调用链、能力结束及 Pawn 销毁顺序 | 玩家和机器人重置、受保护能力、重复触发、实际新 Pawn 及所有权 |
| CPP-022 | LG `ULyraFrontendStateComponent` 的 OnExperienceLoaded、FlowStep 等启动决策 | FControlFlowNodeRef、账号初始化和会话回调不能直接假设可反射；保留原生异步句柄和取消机制 | 离线启动、初始化成功/失败、加入会话成功/失败、取消、控件销毁；线上服务结果单独记录 |
| CPP-023 | LG `ULyraControllerComponent_CharacterParts` 的 Add/Remove、OnPossessedPawnChanged 编排 | 部件句柄和来源枚举需要明确接口；区分生产部件与作弊/开发配置 | Pawn 替换、同 Pawn 再通知、增删、重复和销毁；部件 Actor、网格及复制保留 |
| CPP-024 | LG `ULyraHeroComponent::DetermineCameraMode` 的模式选择 | 当前为原生委托入口；技能所有者句柄和相机模式生命周期先保持在原生层 | 技能相机优先、默认模式、缺 Pawn/Data、结束恢复；不迁移每帧相机混合和碰撞 |
| CPP-025 | LG `ULyraHUDLayout` 的手柄断连提示策略 | 平台用户 ID、设备 ID 和设备映射需原生快照；真实硬件输入需要适用运行环境 | 自己/其他玩家设备、重配对、多手柄、重复通知、断连/恢复和提示销毁；模拟测试与硬件结果分开 |
| CPP-026 | LG `ULyraReplaySubsystem` 的 CleanupLocalReplays、OnEnumerateStreamsCompleteForDelete、OnDeleteReplay 保留策略 | 原生 StreamInfo、异步流和删除回调需要适配；只使用专用临时测试录像 | 保留标记、排序、正在录制、数量边界、一次删除后重新查询、失败停止；不操作用户现有录像 |
| CPP-027 | LG `ULyraAudioMixEffectsSubsystem::ApplyDynamicRangeEffectsChains`、`ApplyOrRemoveLoadingScreenMix` 的选择规则 | 原生总线、Submix、World 生命周期保留；确认变化事件及资源传递 | HDR/LDR 重叠项、加载界面切换、重复应用、缺资源和销毁；参数检查与实际声音验证分开 |
| CPP-028 | LG `ULyraTeamSubsystem::CanCauseDamage` 的自伤/队伍/无队伍规则 | 当前没有 UFUNCTION 标记，需提供明确的查询/决策入口，并让原生伤害调用链实际经过该入口；明确性能和权威边界 | 自己、同队、敌队、无队伍且有/无 ASC、无效对象、实际伤害及预测一致 |
| CPP-029 | TA `UTopDownArenaAttributeSet::ClampAttribute` 的属性约束 | 发生在 GAS 属性变更中，原签名含可变 float 引用；先验证只读输入、数值返回和原生写回入口 | 炸弹数量/容量/范围、移速上下界、容量变化、真实炸弹消耗返还及双本地玩家 |
| CPP-030 | LG `ALyraGameMode::GetPawnDataForController`、`GetDefaultPawnClassForController_Implementation`、`ControllerCanRestart` 的选择/许可段 | 与 Experience 就绪、原生父类和 Pawn 初始化耦合；只拆规则，保留真实生成和初始化 | PlayerState 数据优先、Experience 默认及 AssetManager 默认回退、未就绪/缺数据、真人/机器人、重生许可及实际落地 |

## 保留的原生职责

下列职责继续供 Python 调用，具体文件见源码台账的逐项理由。

| 职责 | 保留范围 |
| --- | --- |
| 引擎与绑定 | UObject/反射、GC、CPython 嵌入和转换、通用插件基础设施 |
| 联机与 GAS | RPC 壳、复制和 FastArray、子对象复制、预测、能力和任务调度、属性存储及执行底座 |
| 角色和实时计算 | 移动、碰撞、物理、动画、每帧相机求解、射线/散布/命中、每帧输入修正和辅助瞄准 |
| 加载和对象管理 | Experience/资产异步加载、计时器与原生句柄、部件 Actor 和装备实例创建、失效和销毁机制 |
| 界面与平台 | UMG 布局、Slate 渲染、CommonUI 基础设施、设备/账号/设置持久化和录像流实现 |
| 声音和表现 | 音频渲染与资源、Niagara、动画和网格实现；已迁移的 BP 编排继续使用 |
| 声明和工具 | 数据资产、接口、枚举/结构、标签、模块入口、Editor、测试和开发/作弊工具 |

条件候选可以拆出其中明确的规则，但不能把整套原生系统都算作迁移范围。
多平台、Shipping/DebugGame、任意动态类替换和更强热重载独立规划，不包含在这份默认清单中。

以下占位或未启用实现也不算迁移成果：

- `LyraAbilityCost_InventoryItem.cpp` 的业务主体位于 `#if 0`，CheckCost 当前返回 false。
- `ULyraPlayerSpawningManagerComponent::ControllerCanRestart` 当前为 TODO 后返回 true；它与 CPP-030 的 GameMode 方法不同。
- `UTDM_PlayerSpawningManagmentComponent::OnFinishRestartPlayer` 当前为空。
- 模块空入口、仅含类型/配置的源码和声明壳继续保留。

## 确认后的执行流程

1. 按确认编号建立新阶段进度和 `CppAcceptance` 账本，冻结每批函数、配置、依赖和目标环境。
   保留本清单的初始源码指纹。发现额外候选时追加编号和理由，不静默扩大已确认批次。
2. 在有标记的隔离工程应用版本化补丁或适配器。Lyra 专用 C++、Python、蓝图生成器和账本归 Examples，
   主库保存必要的通用绑定变更、验证入口及 Demos 指针。官方 Lyra 和 Engine 参考源码保持原状。
3. 先验证接口和原版结果，再替换规则，执行定向 Python 检查及实际 UE 原生/Python 对照。
   记录原生消息、参数/返回、权威结果、复制、时序和退出清理；失败记录与对应输入保留。
   原版自身不满足的行为或生命周期条件单列为原生基线问题，不改写对照结果，也不混入规则迁移签收。
4. 原生声明或实现变化时增量编译受影响模块，保留确切源码和二进制对应关系；
   仅改 Python 时复用匹配二进制。一次只运行一条 UE/构建验证流程，原生进程存活期间不改冻结输入。
5. 每批回归受影响调用方、继承、配置和已有蓝图依赖。共享接口变动扩大到受影响矩阵；
   完成一个版本或阶段时再执行相应实际打包、可见运行及生命周期验收。日常不例行全量构建或 Cook。
6. 真实运行验收通过后，提交并推送 Examples，再提交并推送主库的验证入口和 Demos 指针。
   核对远端提交及两仓配对。原有6份地址更新已按本轮指令提交、推送，
   对应 Examples `3e9c68f`、主库 `d00bee7`。
7. 用新阶段实际通过的候选统计完成度。只通过源码检查、入口原型或测试模拟时，状态仍保留为部分完成；
   原246个蓝图候选和22项验收不被重写。

现有隔离 Lyra Hero 初始化补丁继续作为已记录的前置条件；原生 NetShooter 差异保持原记录，
不与本清单中的规则迁移混合签收。

## 当前执行范围

已确认 CPP-001 至 CPP-015，按 CPP01 至 CPP09 顺序推进。
2026-11-02 用户回复“继续吧”后，CPP-016～018 纳入第二阶段，见
[第二阶段进度](cpp_extended_batches.json)。随后用户要求持续推进，CPP-019～030
全部纳入并已完成，见[剩余批次验收进度](cpp_remaining_batches.json)。
普通的接口适配、定向验证和该批提交推送按已确认范围持续执行。

2026-11-02 已完成 CPP-016～018 的只读入口及资产预检，见
[下一轮分批方案](CPP16_18_PREFLIGHT_REVIEW.md)和[预检证据](NativeGameplay/CPP16-18-preflight.json)。
发现初始属性表的 GameplayTag 结构键读取限制，且本次定义扫描没有玩家标签消耗配置。
这份预检不等于业务替换或运行验收，不改变第一轮已确认范围和完成计数。

相关记录：

- [逐文件源码及候选函数台账](cpp_source_inventory.json)
- [C++ 批次进度](cpp_batches.json)
- [已完成的原定蓝图迁移验收](ACCEPTANCE_REVIEW.md)
- [原蓝图清单和增量回归约定](batches.json)
- [现有 Mixin 调用与生命周期边界](../../../docs/Mixin_Call_Lifecycle_Matrix.md)
- [现有消息适配和订阅规则](../../../docs/Runtime_Subscriptions_API.md)
- [现有隔离 Hero 初始化补丁](NativeFixes/README.md)

2026-11-02 第二阶段所选三组已完成：CPP-016 初始化、CPP-017 物品消耗按生产替换验收；
CPP-018 玩家消耗按独立夹具及联网生命周期能力验收，原配置消费者为0，不计为生产替换。
见 [CPP11 账本](NativeGameplay/CPP11-acceptance.json) 与 [CPP12 账本](NativeGameplay/CPP12-acceptance.json)。
第一阶段 CPP09 仍保留真实窗口 Escape/Menu 输入待验收，CPP-019～030 继续待选。

2026-11-02 用户明确要求“持续推进直到全部完成”，剩余 CPP-019～030 全部进入执行范围，见
[剩余批次进度](cpp_remaining_batches.json)。CPP13 跳跃已通过12次上下文边界和双客户端28次原生输入/预测/落地验证，
死亡/重生联动验证保留给紧接着的 CPP14，不提前计为该组全部验收。
用户选择暂不操作桌面，因此 CPP09 的实际窗口输入继续待办，其余迁移持续推进。

2026-11-02 CPP13～15 已验收：Jump 的死亡取消/新 Pawn 联动4例、死亡矩阵20例、
自毁与受保护能力4例、原版 Arena 死亡两种策略，以及原生 Reset 网络12例均通过。
原生类不能直接挂接当前 mixin，Reset 使用 World 管理的蓝图策略对象；保留原生 GAS 上下文、
事件负载、异步任务和复制。其余 CPP-022～030 持续执行，CPP09 桌面输入遵照用户选择继续待办。

2026-11-03 CPP16～18 已验收并设为默认：前端70组、外观28组、相机8组参数检查，
原生/Python实际运行及默认启动均通过。外观补充双客户端4次原生重置、8份独立网格/部件
观察，恢复原始部件后才释放客户端；相机验证真实技能结束恢复。前端线上服务结果未实测，
成功/失败及取消策略保留为参数与原生回调夹具证据。剩余 CPP-025～030 继续执行。

2026-11-03 CPP19～24 已验收并设为默认，覆盖最后的 CPP-025～030：

- 设备提示：56组参数边界，原生/Python实际设备回调、用户过滤、重复通知合并和下一帧处理。
  回调参数由夹具提供，未插拔真实手柄；原生弱引用、对话框和委托生命周期继续保留。
- 录像保留：132组参数边界，临时内存流的0/1/2/5个保留数量、原生删除后重新查询、失败停止和清理。
  保留/正在录制标记按参数边界检查；不接触用户已有录像，不声称实际玩法录制或回放。
  Python明确拒绝负数保留配置。当前引擎目录残留的5.8.0内存流模块不加载、不登记，
  只把当前5.8.1源码的一个编译单元构建到隔离工程；Engine清单和二进制保持原状。
- 音频选择：52组参数边界，原生HDR/LDR及加载混音调用、重复调用状态和资源数组检查。
  未实测可听声音输出。
- 队伍伤害：256组参数边界、原生/Python实际同队与敌队伤害，4次联网对照中同队不扣血、
  敌队扣血10点，双客户端8份独立血量观察。最终默认配置另通过原版手枪4次客户端预测射击、
  预测键/命中数据一致和8份伤害复制观察。
- Arena属性：48组参数边界；原生、Python和最终默认三次运行各包含两个本地玩家、
  16次真实GAS属性钳制及原有炸弹输入、重复输入不重扣、销毁返还。夹具先写入并恢复属性，
  再单独验证原有输入阶段；进程内Slate用户初始化不算桌面输入。
- 生成许可：56组参数边界，玩家数据优先、Experience回退、真人/机器人许可的原生/Python
  实际结果一致；4次联网原生Reset提供双客户端8份独立新Pawn类和所有权观察。

共600组边界检查、两组联网各4次权威试验和16份独立客户端观察通过。最终默认前端、
生成、双本地玩家输入及原版手枪交叉回归通过；51项启动选择检查通过。
增量构建只涉及LyraGame三个编译单元、TopDownArena一个编译单元及LyraGame反射头；
修正夹具实现时复用已成功的头文件和前两个编译单元。SDK、桥接库、Engine及保留的CPP09
验证工程没有重建或修改，972个受保护输入指纹复核一致。未执行全引擎构建、Cook/打包、
多平台或真实声音/设备验收。

已确认30项均已实现；29项已按各自范围验收，其中CPP-018是零原配置消费者的能力验收。
CPP-015/CPP09仍仅保留用户暂缓的真实桌面Escape/Menu验收，不计为已完成该验收。
六组独立账本见[CPP19](NativeGameplay/CPP19-acceptance.json)至
[CPP24](NativeGameplay/CPP24-acceptance.json)。
