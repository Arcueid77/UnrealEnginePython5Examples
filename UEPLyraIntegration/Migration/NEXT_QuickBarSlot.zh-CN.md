[English](NEXT_QuickBarSlot.md) | [简体中文](NEXT_QuickBarSlot.zh-CN.md)

<a id="010-2k-quickbar-slot"></a>

# 0.10-2K 快捷栏插槽

历史批次plan/checkpoint. 当前已接受的工作和剩余间隙记录在PROGRESS.md和Acceptance/09-quickbar-slot.json中。下面带日期的观察结果将被保留，而不是新的当前 DLL 结果或下一个任务。

状态：有界display/native-network/lifecycle证据在之前的查询保留版本上被接受。命名输出核心调度现在传递其十通道矩阵，并且QuickBarDifferential03在新的DLL/query上传递十二个案例（九个Python查询调用，scopes12/12）。 QuickBarRespawnNetwork03经过十九phases/twotravels/rejoin/four正常退出。 A/B0/B1查询计数15/8/2、scopes12/12、12/12、6/6并检查选定的屏幕截图。受影响的standalone/native生命周期回归仍然开放，现在由另一个版本的共享引擎binary/BuildId更改保持。不要重新标记旧清单以绕过兼容性。保持0.10.0打开。

`IsThisTheActiveQuickbarSlot` 现在选择加入`uep_named_outputs=True` 并返回`{"IsActive": bool}`。内部条目也使用路由的UFunction。 BlueprintFallback故意省略了该方法，并真正使用保留的BPbytecode/output传播。没有类替换或引擎源编辑。

保留`/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C`、其原生LyraTaggedWidget父级、设计器widgets/animations、输入操作和封闭的快速栏布局。捕获的官方审计包含106节点。编译原始BP比较，而不是图形形状推理，决定奇偶性。

Python业务条目：

- OnInitialized：空槽和两个作用域类型化消息订阅。
- 勾选：本机拥有控制器QuickBar组件刷新和弹药总数。
- UpdateSlot：库存快捷栏片段、原生材质图标参数、empty/populated动画状态。保留失败的纹理投射延续。
- UpdateComponentRef：equality/validity/index分支和选择刷新。
- UpdateIsSelected / IsThisTheActiveQuickbarSlot：本机活动索引读取和现有动画。尊重named-bool 输出形状。
- UpdateTotalAmmoLeft：本机杂志+备用统计标签计数，CommonNumeric。
- 鼠标输入：本机增强输入操作值、注入和FEventReply。

仅添加 LyraQuickBarSlotsChangedMessage / LyraQuickBarActiveIndexChangedMessage 拥有的代理存储、显式侦听器恢复和类型化 VM 传输。数组有效负载必须在交付时复制并在取消后进行测试。不要通过无类型的 ProcessEvent 调用发送通配符 CustomThunk。现有的十个传输图需要不变的语义摘要和回归。

验收：实际生产槽位和隐藏的原BP对应项。原生输入武器切换、原始库存消息、empty/populated/相同引用/无效索引/施法失败比较、numeric/material/animation检查。原生Destruct/remount，键入owner/foreign消息，Profile往返。两个客户端，travel/rejoin和零最终scopes/watchers.屏幕截图哈希值和实际检查附带数据。不要改变原生Slots/ActiveSlotIndex、弹药、设备或复制品来制造这些结果。待处理的包或acoustic/physical-input门保持明确。
