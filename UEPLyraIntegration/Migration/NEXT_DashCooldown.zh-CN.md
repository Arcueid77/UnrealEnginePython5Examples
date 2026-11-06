[English](NEXT_DashCooldown.md) | [简体中文](NEXT_DashCooldown.zh-CN.md)

<a id="010-2i-dash-cooldown"></a>

# 0.10-2I 冲刺冷却时间

历史批次plan/checkpoint. 当前已接受的工作和剩余间隙记录在PROGRESS.md和Acceptance/07-dash-cooldown.json中。下面带日期的观察结果将被保留，而不是新的当前 DLL 结果或下一个任务。

当前：资产创作、有界11案例差异和19阶段两客户端网络通行证。生产池寿命缺陷修复并验证。本机Dash/death验证现已运行。整个batch/version仍然开放。

运行时所有者：`uep_lyra_hud.dash_cooldown_mixin.LyraDashCooldownPythonProfile`。 Class/layout/animations 保留`/ShooterCore/Game/Dash/W_DashCooldown_C`。 Python 替换 OnInitialized、ListenForDuration、构造、勾选、UpdateCooldownPercent、UpdateVisibility、OnCheckForDeath 和 OnDeathStarted。显式的 UEPResumeDashObservation 会激活监听器，而无需重放初始化或重置充电状态。现有的 ReadDuration/ BroadcastDuration VM 适配器原样重复使用。

保留的作者详细信息：

- Pawn（不是控制器）等式过滤 Dash 持续时间通道。有效的所有者消息存储Duration/StartTime，可选择停止InactiveToActive，将两个AnimateArcFill标量写入零，播放ActiveToInactive并标记充电。驱动弧的是本机游戏时间，而不是挂墙时间或 Tick delta。
- 充电完成清除标志，播放InactiveToActive并写入1。
- 丢失 Pawn 仅清除 NewHealthComponent。它不会清除当前或更新可见性。更改后的无效生命值也没有可见性延续。有效的生活健康使CenteringOvrHitTestInvisible。 dead/invalid 明确查询 Health 使其崩溃。
- 原始的旧健康绑定将保留到其一次性死亡分支，而不是默默地改变原始策略。所有脚本拥有的绑定都会在Profile teardown/Destruct/pool 停用时删除。
- 原生UMG动画在此小部件中没有脚本完成所有权。实时Profile清理不得暂停它们。 Differential01 暴露了这个错误。

证据：

- Assets01：复制Interface/CDO和四节点精确原始死亡委托清理。帮手里没有BP业务。官方资产哈希值不变。
- DashDifferential05: 11 案例 / 50.422s / 范围 11/11 / 零 active/errors. 九个比较使用产生式 UI。两个原生 Destruct/remount 案例使用单独声明的同类视口对，因为生产 UIExtension 池不像面板子项那样支持 RemoveFromParent。巴布亚新几内亚检查。材料公差收紧至0.00001，而不是扩大以修复它。
- DashNetwork01：第二次切图失败，有两个活动生产池条目。 13 A / 12 B0 阶段不是完整的网络通行证。
- 共享的pooled_widget_lifetime采样器读取本机GetAllEntries并在其离开活动池后关闭条目。没有池修改或事件重播。不活动的蜱无法立即重新绑定生命值。关闭时的快照仅使用保存的计数器。 DashNetwork05 通过两个travels/rejoin/all 出口。 A/B0各记录一次实际停用，所有最终watchers/scopes均关闭。达世币范围 server/A/B0/B1: 0/0、14/14、12/12、3/3。泳池手表 0/0、4/4、4/4、1/1. 图片已检查。本地持续时间在此通道中仍然是合成的。
- 主机测试11：276通过。模拟和人工报告守卫是支持证据，而不是原生pool/ability接受。

继续使用当前源独立和整个dedicated-server/two-客户端通道，包括两个travels/rejoin/all出口。然后证明不变的GA_Hero_Dash->原生GAS->持续时间消息->PythonUI，原生death/invalid健康分支和受影响的transport/HUD回归。没有合成消息可以建立能力生产或消息复制。目前的包裹验收仍然是后来的合并门。不要启动完整的引擎构建或更改参考项目。
