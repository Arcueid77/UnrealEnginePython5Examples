[English](NEXT_NameplateComponents.md) | [简体中文](NEXT_NameplateComponents.zh-CN.md)

<a id="next-bounded-nameplate-group-source-and-manager"></a>

# 下一个有界铭牌组：源和管理器

历史批次plan/checkpoint.Source/Manager后续现在分别记录在PROGRESS.md和Acceptance/10-nameplates.json.中保留以下早期限制。这不是当前的下一个任务或新的本机运行。

该小部件仅在`20261015-ue581-acceptance/NameplateDifferential06`：14native/BP比较、范围23/23、团队代理13/13和初始化委托10/10显式删除中被接受。这不是 Source/Manager 或多人游戏接受。最新的源匹配 Lyra UEP DLL 是 A37911F9...（完整哈希正在进行中）。请勿将其替换为之前的 DLL 或强制模块BuildIds。

<a id="verified-native-boundaries"></a>

## 已验证的原生边界

- `CompareTeams` 反映为 `(ReturnValue, TeamIdA, TeamIdB)`，而不是标量。
- 使用`world.get_world_type()`和可为空的GameplayStatics.GetPlayerController。
- WidgetBlueprintLibrary.GetAllWidgetsOfClass 有 1 个外数组。没有`ue.get_objects`API。保留`ue.add_ticker`的返回句柄。
- 现有的`object.broadcast`现在使用属性值地址。原生empty/bound/rejection/recovery/unsubscribe证明位于CallMatrix02。不要发明`broadcast_event`或抑制访问检测器错误。
- 原生Actor.AddComponentByClass / FinishAddComponent实现BP添加组件节点。对于测试拥有的 BP 基线，请推迟完成，选择其每个实例Profile，然后完成，以便运行实际的原生生命周期。不要手动调用ReceiveBeginPlay/ReceiveEndPlay来制造覆盖范围。
- LyraIndicatorManagerComponent.Indicators 是一个反射数组，可用于只读本机成员资格证据。它的 C++ GetIndicators 便捷方法和 IndicatorDescriptor.GetIndicatorManagerComponent 未反映出UFunctions。不要通过ProcessEvent调用这些名称。
- IndicatorDescriptor的反射吸气剂暴露DataObject、SceneComponent、IndicatorClass、projection/anchor/offset/alignment、clamp/auto-remove和所需的可见性。描述符UnregisterIndicator也被反映。

<a id="execution-order-and-gates"></a>

## 执行顺序和门

1. 在接触冻结的 script/asset 输入或启动另一个编辑器进程之前，Finish/check 现有的 Network03 进程及其最终报告。
2. 针对标记的 Lyra 阶段，将 `Run-UEP58NameplateComponentsAssetAuthoring.ps1` 运行到新目录中。需要保留的组件 BP 类、序列化的 Interface/CDO、19 类型化 VM 函数/59 节点，以及所有 15 先前函数的未更改语义摘要。只有接受的输出才可以复制到示例中。官方Lyra必须保留其哈希值。
3. 使用实际生产本地管理器和本机完成之前选择的同级原始 BP 基线构建有界组件差异。读取本机指标并比较描述符配置和Pawn映射，而不仅仅是Python计数器或模拟生成的预期值。
4. 通过编译的 VM 适配器、本机源组件销毁、每个实例 Profile/resume 和精确清理，练习输入 Discover/Add/Remove。测试拥有的Character/Pawn/component对象必须被识别和清理。不要编写本机Health/team/inventory状态或重放生命周期事件。
5. 根据真实的原始 BP 确认审核后的重复Pawn行为：替换 Map 值可以使先前的描述符保持注册状态。记录双方的本机成员资格并明确仅进行固定装置清理。不要默默地删除生产策略的重复数据或将模拟错误地标记为证据。
6. 扩展后重新运行 Widget 差异和旧类型传输案例。现有的创作报告冻结资产SHA-256值：扩展共享传输会使旧报告的传输哈希无效。保留旧报告。创建一个新的已接受的capability/asset-chain报告，而不是重写哈希值、削弱驱动程序或声明旧的15功能报告涵盖19。
7. 将铭牌特定证据添加到两个客户端travel/respawn/rejoin通道：本地经理资格、每个Pawndiscovery/removal、本地指标、Widget/Source/Manager最终scopes/proxies/helper根以及无延迟交付。仅通过较旧的HUD网络交换机并不能认证铭牌。

当前的 397 主机检查是 policy/negative/entry-point 测试，而不是这些本机案例。除非实际执行，否则将原生伤害产生、团队重新分配和投射平价分开。不要cook/package、重建引擎、提交、推送、标记或发布未完成的版本。保留混合工作树、animation/editor/test工具、官方Engine/Lyra和`.nepy`边界。
