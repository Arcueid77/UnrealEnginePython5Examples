[English](NEXT_AbilityFailureFeedback.md) | [简体中文](NEXT_AbilityFailureFeedback.zh-CN.md)

<a id="010-2h-ability-failure-feedback-audit--next-implementation"></a>

# 0.10-2H能力-失败反馈：审核/下一步实施

历史批次plan/checkpoint. 当前已接受的工作和剩余间隙记录在PROGRESS.md和Acceptance/06-ability-failure.json中。下面带日期的观察结果将被保留，而不是新的当前 DLL 结果或下一个任务。

状态：有界original-BP/runtime差分和本机FText身份已通过。 237 主机检查通过。接受的运行：Assets06、FailureDifferential06（17案例）和NativeCulture02（一个原生文本广播，en/zh-Hans/en）。检查了更正的可见屏幕截图。 AbilityFailureNetwork02正在运行。本机GAS生产者、dead/invalid健康状况、当前适配器回归、包和整个版本接受仍然开放。早期的受限启动失败和被取代的计时器模型是历史上的失败尝试，而不是当前的实现。保留 Engine/official Lyra、animation/editor/test 资产、混合工作树和不完整发布发布边界。

候选：`/ShooterCore/UserInterface/HUD/W_AbilityFailureFeedback`（保留LyraTaggedWidgetclass/layout）。静态审计列出三个条目/31业务节点。这不是迁移完成计数。

观察到的创作依赖关系：

- OnInitialized 折叠小部件并在 `Ability.UserFacingSimpleActivateFail.Message` 上监听 ExactMatch。与能力进度不同，异步工厂`then`没有延续：代理所有权存储必须处理该拓扑，而无需发明业务延续。
- 原生`FLyraAbilitySimpleFailureMessage`有PlayerController、FailureTags和UserFacingReason（FText）。 `ULyraGameplayAbility::NativeOnAbilityFailedToActivate` 保持生产者不变。 Python 必须仅拥有 UI policy/presentation.
- 图表比较拥有PlayerController和当前原因，查询原生Pawnhealth/death，设置text/visibility，播放保留的UI动画并使用一秒RetriggerableDelay。保留确切的分支order/defaults.
- OutroCompleted / OutroCurrentCompleted 是创作的动画完成条目。动画资产保留。回调策略和清理迁移。

实施顺序：

1. 跟踪紧凑的引脚链接并获取当前反射的signatures/defaults.确认FText的原生程度transported/written，而无需从仅字符串的视觉比较中声明本地化身份保留。
2. 仅为此负载添加类型化 VM reader/broadcaster。前面的六个图必须保留语义摘要和当前的UI/Verb/Duration运行时回归。保留辅助节点conversion/ownership-only，而不是UI决策。生成器现在包含本机 FText copy/equality 原语，因此策略永远不会将 UserFacingReason 作为 Python 字符串进行访问。 Assets06 通过了干净编译，NativeCulture02 证明了实时本地化身份。
3. 实施owner/reason/death策略、原生小部件潜在延迟、保留动画playback/completion以及Python中的解除清理。切勿使用未经验证的 wildcard/latent ProcessEvent 占位符。首先绑定timer/animation支持，而不是声称通用的潜在支持。接受的实现通过显式 LatentActionInfo 和 int32 链接完成声明调用本机 RetriggerableDelay。它使用小部件的原始本机潜在调度程序，包括世界暂停时的到期时间。不要求任何外部代码、新的 Tick 业务、通用潜在支持或额外的动态动画委托。 world-clock/tick-delta 原型未能通过比较并被删除。现在有 17 个运行时案例验证本机计时和原始持久 callback/deferred-payload 顺序。
4. 在自然构造时幂等地重新武装（包括折叠的小部件重用），在Destruct/Profile清理时解除武装，并保持显式隐藏的实时Profile激活与生命周期重放不同。使用精确拥有的清理取消已保存的原始代理和任何后备 latent/animation 回调。
5. 重点original-BP/Python案例：owner/foreign、same/different/repeated原因、真正的暂停时钟、截止日期前重新触发、death/invalid-health分支、中断的尾声、隐藏的Profile开关、重新挂载和无延迟回调。 `ability_failure_validation.py`及其重点驱动程序现在实施十七个有序的production-widget/original-BP检查，在FailureDifferential06中通过。第一个延迟门拒绝大于两个观察到的UI帧（硬上限0.15s）的不匹配，而不是默默地扩大容差。实际的原始延迟有效负载和持久完成结果通过实际基线，而不仅仅是源模型。合成的FText显示比较并不能证明本地化历史。 Dead/invalid 健康状况仍然是一个额外的原生门，而不是这十七例固定装置的一部分。原始 BP 基线被侦听器恢复。原始的OnInitialized不会被灯具重播。失败的资产创作会在启动之前阻止运行时驱动程序。这个守卫实际上是在`20261014-batch2h/fixture-preflight01.json`中检查过的。
6. 然后生产可达性/未改变的本地能力生产者和两个客户端/切图/重新启动/重新加入/全部退出。合成有效负载的成功并不是原生的GAS失败生产或网络复制证据。

应重用当前匹配的编辑器二进制文件。如果选定的不受支持的绑定需要小范围的UEP模块更改，请首先声明该范围。不要将启动引擎重建或打包作为默认实施步骤。

布尔相等适配器有一个命名输出：它返回`(bool,)`，而不是一个裸布尔。 FailureDifferential04 暴露了不正确的真实性检查。策略和主机现在模拟validate/extract实际的反射形状。失败的计时、创作和屏幕截图尝试仍记录在PROGRESS/history.中
