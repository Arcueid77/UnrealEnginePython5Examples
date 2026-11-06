[English](BLUEPRINT_INVENTORY.md) | [简体中文](BLUEPRINT_INVENTORY.zh-CN.md)

<a id="third-person-blueprint-migration-inventory"></a>

# 第三人称Blueprint迁移清单

此清单将未更改的 Unreal Engine 5.8 Blueprint 第三人称模板与 0.6.0 Python 第一运行时进行比较。计数由`Tools/audit_template.py`生成。在 engine/template 更新后运行记录的 `-Mode Audit` 命令，而不是将这些数字视为永久的 API。

当前的 UE 5.8.0 审核加载了四个 Blueprint 资产，并发现带有 173 节点的 27 图表：

| 角色 | 参考资产 | 家长 | 图/节点 | 0.6.0决定 |
| --- | --- | --- | ---: | --- |
| 性格 | `/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter` | `Character` | 4 / 40 | 移动、看、跳跃、摄像、动作调整和输入绑定移动到`UEPThirdPersonCharacter` |
| 玩家控制器 | `/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController` | `PlayerController` | 3 / 31 | 桌面映射-上下文设置移至`UEPThirdPersonPlayerController`。移动触摸UI不在Win640.6.0契约范围内 |
| GameMode | `/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode` | `GameModeBase` | 2 / 1 | 类选择移至`UEPThirdPersonGameMode` |
| 动画 | `/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed` | `AnimInstance` | 18 / 101 | Speed/falling/landing状态选择移至Python。网格、混合空间和剪辑仍然是资产 |

审核还会加载`/Game/ThirdPerson/Lvl_ThirdPerson`。地图及其WorldPartition/placed-actor数据保持不变。 URL GameMode 覆盖会在运行时选择 Python 类。在Python中重建关卡数据不会提高所有权或可测试性，因此故意不是迁移目标。

<a id="remaining-blueprint-boundary"></a>

## 剩余Blueprint边界

没有参考Blueprint事件图在Python首次运行中拥有keyboard/mouse游戏玩法。可收藏的回合、同伴和视口 HUD 也属于 Python 所有，并且不添加游戏玩法 Blueprint。资产保留在分阶段项目中以进行自动比较，并且因为官方地图引用了模板内容集的部分内容。

该示例的唯一项目 C++ 是一个空的主模块，需要为 UBT 提供源插件打包的游戏目标。它不包含角色、输入、动画、地图或GameMode行为。

保留的动画内容是数据，而不是控制逻辑：

- `SKM_Manny_Simple` 提供骨架网格物体。
- `BS_Idle_Walk_Run` 提供姿势混合。
- `MM_Jump`、`MM_Fall_Loop`、`MM_Land`提供动画片段。
- Python 选择状态并更新每个刻度的混合空间位置。

移动触摸控件保留在参考PlayerControllerBlueprint中，并明确排除在Win640.6.0契约之外。网络、复制和Lyra/Game功能集成是后来的里程碑，而不是此示例的隐藏Blueprint依赖项。
