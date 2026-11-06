[English](HARDENING_REVIEW.md) | [简体中文](HARDENING_REVIEW.zh-CN.md)

<a id="native-migration-hardening-and-delivery"></a>

# 原生迁移强化和交付

用户在2026-11-03上选择了所有四个后续组。在 [hardening_batches.json](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/hardening_batches.json) 中跟踪进度。这项工作保留了选定的 UE5.8.1 / CPython3.11 / Win64 Development 目标。 H01-H05 将 CPP09 桌面输入分开。在2026-11-05，用户解锁屏幕并授权继续。 [CPP09 实际窗口接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP09-acceptance.json) 现在关闭该输入门。下面早期的范围和捕获限制仍然是历史性的。

| 集团 | 所需证据 |
| --- | --- |
| H01 | 伤害接纳、原始装备成本check/apply、播出后奖励结算、原生重置等实际原生回调异常。无重复本机payment/reward，后续调用成功，非活动失败重置并恢复subscriptions/profiles |
| H02 | 相同本地夹具入口点上的交错 native-fallback/Python 时序。一个二十分钟的实际游戏过程，包含重复的本机Reset/respawn、持久PlayerState、有界跟踪和静态GC后对象以及操作系统memory/handle样本 |
| H03 | 根据参考项目创建的全新独立舞台，版本为SDK、桥梁、覆盖、固定装置和订购的生产配方。没有复制旧的stage/compiler输出。受保护的引擎构建、组合源码清单和实际新鲜阶段运行时 |
| H04 | 当前受保护的Win64Development游戏构建，实际的cook/stage/archive，煮熟的资产和松散的Python/dependency指纹，以及使用打包的可执行文件的真实打包的standalone/listen-authority/two-client执行 |

H02 计时包括两条路线上相同的反射入口点和安装的桥梁入口。它不测量裸引擎调用或渲染帧速率。主要持续运行在运行时准备就绪后至少1,200秒。工作会在两次计划的完整本机 GC 传递期间暂停。在初次运行之前声明操作预算：预热后私有内存增长 <=256 MiB、句柄增长 <=32、世界参与者人口范围 <=25、无Mixin注册增长、<=8 静态策略上下文和诊断跟踪<=128条目。这些是特定于工作负载的检查，而不是通用的memory/performance保证。

最初的 H01 运行保留了失败的证据。它暴露了不完整的Python世界政策的引擎保障。适配器现在记录被拒绝的操作并返回失败，而不重播原始本机主体。第一次成本夹具调用错误地使用了游戏世界中的仅限编辑器的工厂。运行时案例现在观察到现有玩家的本机spec/ActorInfo/item.重置的不完整计划更改为其终端EndAbility操作，因此失败的脚本计划无法使其本机GAS实例保持活动状态或reset/broadcast其Pawn。受影响的编译器依赖文件仅选择更改的主体单元。不变UHT，SDK，桥，其他游戏单元和受保护的CPP09阶段被重复使用。

新鲜再现和游戏打包是分开的关卡。他们需要自己的目标构建。它们并不是每次编辑后的常规完全回归。每个接受的组都会在主验证脚本和演示指针之前提交并推送到示例，并验证两个远程头。

<a id="h01-accepted"></a>

## H01已接受

[H01接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H01-acceptance.json)关闭了13个真正的原生exception/recovery案例：伤害承认3次，原始装备成本check/apply6次，原生广播后奖励回调失败，以及3次重置失败后实际新的Pawn恢复。支付失败不扣款，恢复扣款一次，结算失败广播一次，关闭其观察者会抑制后续原生交付。重置失败结束其GAS实例，而不重置Pawn。以下有效请求会重新生成它。所有临时声明、选择器和订阅都将恢复。正常的默认离线前端和52选择加入启动选择测试通过。

对于这两个单独的修复，仅编译了LyraGame主体单位3和1。 UHT、单元2、TopDownArena、SDK、桥和引擎均保留。奖励输入是显式回调装置。标签是替换其源本机映射之前分离的值快照。这并不是说每个游戏操作在任意用户代码副作用之后都是事务性的。 H02-H04 验收如下。

<a id="h02-incremental-world-lifetime-repair"></a>

## H02 增量终身修复

第一次完整运行暴露了原来的十二分钟比赛结局和无缝切图使缓存的世界失效。 Mixin get/set/clear 选择器接受了保留的包装器，而没有首先检查其跟踪的弱所有者。共享转换助手现在在检查其原始本机指针之前拒绝该包装器。仅重建`UEPyMixin.cpp`和SDKimport-library/DLL链路。

[选择器守卫接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H02-selector-guard-acceptance.json) 记录了 90 秒的活跃原生游戏，一次实际的早期服务器切图，三个安全的 get/set/clear 拒绝，三个原始的 Reset/respawns 和 4,250 原生查询。安全带重新获取就绪世界，并将切图等待排除在其活动持续时间内。 GC 后actor/router 群体保持不变。引擎、game/bridge DLL 和保留的 CPP09 检查点保留其受保护的哈希值。随后的全长 H02 运行将通过下面的独立操作门。

<a id="h02-accepted-within-its-operational-budgets"></a>

## H02 在其运营预算范围内被接受

[H02受理](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H02-acceptance.json)记录1,200秒活跃游戏，58原始原生Reset/respawns，57,250原生查询和一场自然的比赛结束无缝切图。其34.843秒travel/readiness等待不包括在活动时间中。三个过期的选择器被安全拒绝。

在声明的120第二次预热之后，111操作系统样本和103静态本机GC样本通过了运行前设置的预算。私有字节中位数增长 217,219,072 字节（207.16 MiB。限制 256 MiB），处理量增加 4 个（限制 32），参与者数量范围增加 1 个（限制25），路由器数量保持不变，最多保留两个临时本机策略上下文（限制八个）。这是一个为期二十分钟的有限观察，伴随着可测量的记忆增长。它并不是无限稳定性或无泄漏的证明。

当前的 SDK 基准测试在单独预热后，每 route/family: 14,400 定时调用总数交错十二个 300 调用批次。伤害接纳中位数为6.18微秒本机和17.22Python。 Pawn 数据中位数为4.70 和15.43。两者都使用相同的反射夹具入口点。本机后备包括已安装的桥接。这些数字不测量渲染帧速率。 H04记录下面单独的实际包门。

<a id="h03-accepted"></a>

## H03 accepted

[H03接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H03-acceptance.json)关闭独立的[复制入口点](REPRODUCE_NATIVE.zh-CN.md)：十五个版本化配方组成63生产C++输出，9,702原始和1,871版本化输入被固定，并且11,341 最终暂存文件与订购的 copy/overlay/patch 组合相匹配。不导入旧项目二进制文件或中间构建目录。除了现有的 SDK/bridge 和 AndroidFileServer 设置之外，拥有的生产描述符仅禁用参考测试插件。

审核后的项目构建包含 23 模块和 289 compile/link 操作，每个输出都在新阶段内。本地加载器清单使用未更改的引擎BuildId。引擎source/binaries/manifests和原始Lyra项目被保留。十三个实际的本机exception/recovery案例传递这些新的DLL，具有独立的result/log门和正常的解释器关闭。初始受保护的完整目标尝试、仅内容描述符修复以及缺少的参考测试插件设置均保留在分类帐中。后一个配置更改重新生成了共享编译器标头，并在最终运行时验收之前重建了受影响的项目模块。

<a id="h04-accepted"></a>

## H04 accepted

[H04 接受](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H04-acceptance.json) 关闭同一独立项目当前的游戏交付。冷游戏配置编译了1,190动作，包括其所属项目内的引擎运行时依赖项。 4,105编译器output/PCH/dependency路径保留在该阶段内。现有的引擎分发二进制文件、清单和源保持不变。第一个游戏配置构建与编辑器构建和增量回归是分开的。

实际厨师处理了4,707包。存档的容器列表包括所有246原始候选资产、493覆盖资产、十二个运行时映射和三个仅阶段类型化消息观察器。生产资产和源指纹保持固定。内部打包的可执行文件等于新的游戏版本。成熟的存在并不能建立所有原始候选项的行为。

Eight actual packaged processes pass: thirteen standalone native exception/recovery cases, the normal frontend flow, and Damage/Pawn network lanes with one listen authority and two real remote clients each.本机主机LocalPlayer已删除。 Together the network lanes check eight authority trials and sixteen independent client rule views, including replicated damage, spawn classes, Reset, RPCs, restoration and observer cleanup.文件坐标timing/acknowledgments。本机 RPC 携带游戏状态。所有八个进程均正常退出。

每个进程都会从存档中加载 CPython 以及该存档中的 4,578 收据文件。 One standard-library test INI receives UAT's UTF-8 BOM/CRLF transformation: exact normalized bytes must agree, while every other byte stays strict. Its original failed pure dependency summary is retained beside a reviewed summary。成功的本机过程没有重复。

The first network attempt exposed the packaged Game target ignoring Editor-style `-server`.成功的运行使用其支持的监听URL。专用服务器契约也预计没有授权UI/cosmetic完成。 Listen 保留稳定的 UI 引用及其本机本地完成消息。特定于侦听的检查器断言这些事实并保留所有其他原始对等断言。第一次成功的损害运行失败的纯门被保留，并对未改变的同行进行单独审查。 Pawn直接使用最终检查器。纯粹的门修复都不会触发另一个构建、Cook或重复成功的游戏玩法。

UE5.8.1 / CPython3.11 / Win64 Development 接受所有四个选定的组。 CPP09 物理Escape/Menu 在此捕获时被推迟，并于2026-11-05 单独完成。打包专用服务器、Shipping、附加平台、渲染图形和hardware/audio 接受度不属于这些结果。

<a id="h05-rendered-frame-rate-and-cpu-follow-up-accepted"></a>

## H05渲染帧率及CPU后续已接受

用户随后请求实际的FPS和CPU进行比较。 [H05](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H05-acceptance.json) 和 [其 method/results](RENDERED_PERFORMANCE.zh-CN.md) 在当前包上添加实际的 D3D12 离屏比较，无需编译或重新烹饪。这仅比较共享的本土世界政策载体。其他迁移的层保持固定。在 1080p 中，每个工作负载有四个平衡对提供38,274 分析帧。 Windows CPU snapshots independently check process CPU accounting.

The fixed noncombat scene gives Native/Python 120.56/120.39 average FPS, 79.36/78.52 low FPS, 36.92%/36.72% whole-machine CPU 和 3.30/3.32 毫秒 GameThread。其配对的局部间隔包括零。这并不区分效果。通过每帧 200 附加反射规则查询，Native/Python 给出 120.23/118.26 FPS、71.29/66.44 低FPS、37.28%/39.85% CPU 和 4.54/8.25 毫秒 GameThread。压测使PythonGameThread、2.57CPU增加了3.71毫秒，减少了FPS1.64%。这是一个单独的合成工作负载，而不是正常的游戏玩法或通用性能声明。 CPP09 的单独实际窗口输入门随后传递到2026-11-05。
