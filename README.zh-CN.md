[English](README.md) | [简体中文](README.zh-CN.md)

<a id="unrealenginepython5-examples"></a>

# UnrealEnginePython5 示例

这是 [`Arcueid77/UnrealEnginePython5`](https://github.com/Arcueid77/UnrealEnginePython5) 的配套示例存储库。它的历史记录是从核心存储库中分离出来的，因此0.1.0到0.8.0示例演变仍然可用，而无需在插件源代码树中保留演示项目。

**稳定版本 — 1.0.0。** 匹配的核心和示例标签是`v1.0.0`。验证目标 UE 5.8.1 和引擎 CPython 3.11.8 Win64。该发布分别记录了Development和Shipping证据。

确认的迁移范围通过22原始Blueprint标准、30游戏-C++候选和H01-H05接受。 [完成及证据](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/completion_status.json)记录每个接受批次的范围。

[核心发布与安装](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-1.0.0/README.zh-CN.md) · [文档索引](docs/README.md)

下面的里程碑部分和注明日期的批次记录保留其原始范围。完成索引和版本化发布记录提供组合状态。

演示驱动程序将Unreal Engine的官方Blueprint第三人称模板中的资产存放在`.build/Demos`下，将当前插件复制到该一次性项目中，并根据配置的引擎进行构建。它永远不会编辑引擎源、引擎模板或适当的参考资源。打包使用 UE 的松散熟包编写器，因此 Cook 和 Stage 不会耦合到瞬态本地 Zen 进程。

驱动程序需要检查核心插件。当两个存储库都是名为 `UnrealEnginePython5` 和 `UnrealEnginePython5Examples` 的兄弟存储库时，它会自动查找插件。对于任何其他布局，请传递`-PluginRoot <path-to-UnrealEnginePython5>`。还会自动检测使用此存储库作为其 `Demos` 子模块的核心签出。

特意保留了三个变体：

| 变体 | 目的 | 运行时游戏所有者 |
| --- | --- | --- |
| `Overlay` | 0.1.0 兼容性示例 | 官方Blueprint模板加上Python皮卡和配套 |
| `PythonFirst` | 0.6.0 可播放示例 | 动态Python游戏类、可收集循环和视口HUD |
| `Mixin` | 0.7.0 保留级样本 | 官方Blueprint类，包含每个实例PythonProfile、BP回退、可收集循环和视口HUD |

<a id="lyra-python-health-bar"></a>

## Lyra Python 生命条

0.8.0Lyra覆盖保留官方`/Game/UI/Hud/W_Healthbar`路径和`W_Healthbar_C`运行时类型。其示例拥有的副本添加了 `UEPPythonMixinInterface`、`PythonMixinProfile` 选择器和 `DA_LyraHealthbarMixin`。所有现有的Blueprint图表仍然可用。 Lyra的游戏功能`Add Widgets`动作和CommonUI仍然是create/remove小部件。

默认的PythonProfile拥有`Construct`/`Destruct`，跟随`OnPossessedPawnChanged`，绑定活动的`ULyraHealthComponent`，标准化健康状况并决定何时刷新。其当前的Python`SetDynamicMaterials`、`ResetAnimatedState`和`InitializeBarVisuals`方法调用本机UMG/material基元，保留创作的材质和动画资源。 `BlueprintFallback` Profile改为运行保留的 Blueprint 构造。游戏效果、权威和复制仍然是原生的Lyra行为。

实现了健康数据、damage/heal/death/respawn动画选择和数字插值，并传递一个隔离的真实UMG渲染的夹具。恰好一个演示者和关闭后零拥有的回调现在具有显式的 probe/driver 检查、主机测试和当前脚本 Unreal Standalone 通行证。当前源组合network/package的接受仍有待确定。

核心存储库的完整内容驱动程序将此覆盖层暂存在`F:\LyraStarterGame`的一次性副本中，因此参考项目和引擎源都不会被编辑。核心`GenerateHUDAssets`泳道创作了两个健康栏覆盖资产。单独的舞台守卫武器创作工具创建四个 BP 副本和四个Mixin 集。集中运行时通道永远不会节省资源。 `Standalone`、`Network`、`Package`和`All`练习运行时通道。 `All` 包括繁重的 Win64 cook/package 步骤。 HUD启用的`All`现在运行`HUDAudit`，一个预编译的交叉Actor调用者固定装置并渲染UMG检查。每个也可以独立运行。旧的绿色`full_acceptance`标志不包括该审核，并且无法关闭更正后的0.8发布验收项。

运行时代码位于`UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_hud`下。 clean-base 创作和只读审计脚本位于 `UEPLyraIntegration/Tools` 下，主机端演示者合约位于 `UEPLyraIntegration/Tests` 下。

收尾检查通过了 29 Python 测试以及 40 核心端 PowerShell 检查。架构5保留活动的HUD快照，并且仅在Python退出快照证明零拥有的callbacks/widget引用后升级`awaiting_shutdown`。驱动程序还需要干净的进程退出和有序标记。在官方UBT的两次仅元数据修复操作之后，新的严格审核和当前脚本NullRHI独立传递了2026-09-07：一名活跃演示者，零最终presenters/references，控制器绑定3/3和健康绑定6/6.不需要 C++ 编译、打包或资源保存。集成的`All`、同步的网络和包门仍然需要新的证据。在2026-09-10上，跨Actor路由和八个渲染帧以最终零拥有的widget/callback状态传递。核心`Run-UEP58FocusedHUDValidation.ps1`在已构建的标记阶段上重现这些检查，无需UBT/cook/package或资产保存（可以进行测试窗口和着色器缓存工作）。它的焦点`All`不是完整驱动程序的`All`，并且始终报告`full_acceptance: false`。它还运行一个单独的动画中期Profile切换案例。在路由器修改期间，清理暂停而不调用完成事件。核心插件还修复了该测试暴露的零大小的本机回退帧。

约定的下一个范围是0.8健康栏收尾，0.9Mixin工程加一个weapon/ammoHUD链和有界消息订阅，运行时BP业务迁移到0.10–0.14，然后RC冻结和1.0支持绑定。每个小行为批次都会添加original-BP/Python比较和real-UE/two-client检查。动画和editor/test工具保留。游戏项目 C++ 迁移稍后进行。候选记录必须标识示例和核心提交。核心`Demos`引脚必须与测试的示例提交匹配。这是发布策略，而不是新的测试运行。

<a id="blueprint-mixin-gameplay"></a>

## Blueprint Mixin游戏

0.7.0 `Mixin` 变体保留运行时类型 `BP_ThirdPersonGameMode_C`、`BP_ThirdPersonPlayerController_C` 和 `BP_ThirdPersonCharacter_C`。官方增强输入EventGraph仍然收到操作。默认的`Python`Profile实现了`Move`和`Aim`。 `BlueprintFallback`仅实现了`Aim`，因此同一类路由器调用保留的Blueprint`Move`。当玩家使用 Python 时，具有相同 `BP_*_C` 类型的第二个角色保留后备Profile。Mixin的 `ReceiveBeginPlay` 在添加 Python 行为之前显式调用保留的原始内容。 Blueprint/native跳转，相机设置和`ABP_Unarmed_C`保持不变。

示例叠加层拥有可玩角色的 `DA_ThirdPersonCharacterMixin` 以及 `BP_ThirdPersonCharacter` 的相同路径项目副本。该副本添加了 `UEPPythonMixinInterface`、两个小的选择器图表和一个实例可编辑的 `PythonMixinProfile` 变量，同时保留了原始游戏图表。正常播放从该声明注册普通的PythonProfile类，而不是使用装饰器或启动直接注册侧通道。

`/Game/UEPTests` 下还有另外三个回归资产：一个 `UEPPythonMixinSet`、一个直接声明 `UEPPythonMixinInterface` 的组件 Blueprint，以及一个继承它的子组件 Blueprint。它们执行后期包加载发现并继承路由器所有权。所有五个资源都是示例拥有的覆盖文件。生成器永远不会就地编辑已安装的引擎模板。

烟雾合约在Profile之间切换实时 pawn，使每个实例的缓存无效并证明丢失Profile`Move`会自动回退。然后，它在已生成的 pawn 上取消注册路由器，并证明原始 Blueprint `Move` 功能已恢复并可播放。最后，它在同一对象上测试直接-API生成和第二个声明-Mixin-Set生成，证明在最终恢复之前两者中的Python运动。它还会在不干扰活动路由器的情况下拒绝无效的 Python 签名，并检查每个Profile的平衡init/teardown. 这是基于子类的 PythonFirst 不提供的实时实例行为。

<a id="python-first-gameplay"></a>

## Python-第一个游戏

0.6.0实现是`UEPPythonThirdPerson/Overlay/Content/Scripts/uep_third_person`下的包。旧的 `uep_python_third_person.py` 路径是兼容性导入。启动时，该包会创建瞬态反射类并将它们作为虚幻垃圾收集器的根：

- `UEPThirdPersonGameMode` 选择Python pawn 和控制器类。
- `UEPThirdPersonPlayerController` 安装官方默认和鼠标外观增强输入映射上下文。
- `UEPThirdPersonCharacter`配置碰撞和移动，创建弹簧臂和跟随相机，绑定move/look/jump动作，并在Python中执行这些动作。
- 角色在`ReceiveTick`中计算速度、坠落和着陆状态，并通过单节点动画实例驱动保留的混合空间和动画序列。
- 世界会话创建六个可收藏的球体和一个移动伴侣，拥有round/score/timer状态，并在地图切图后干净地替换自身。和
- `ThirdPersonHUD` 将命中测试不可见的 Slate 树附加到游戏视口并显示目标、得分、计时器、速度和动画状态。

关卡、人体模型网格、输入动作、输入映射上下文、混合空间和动画序列仍然是虚幻资源。原始角色、控制器、GameMode和AnimBlueprint资产仅保留作为未更改的参考集。 Python-第一个游戏URL选择瞬态PythonGameMode。运行时代码和选择加入的烟雾状态机位于单独的模块中。

该覆盖层还包含一个空的 `UEPPythonThirdPerson` 主 C++ 模块和 Game/Editor 目标文件。他们将 Epic 的纯内容模板转换为源项目，以便 UBT 可以在打包版本中链接和暂存源插件。他们不实现游戏玩法或初始化Python。

有关迁移边界和审核的参考图计数，请参阅 [`UEPPythonThirdPerson/BLUEPRINT_INVENTORY.md`](UEPPythonThirdPerson/BLUEPRINT_INVENTORY.zh-CN.md)。

<a id="automated-checks"></a>

## 自动检查

所有命令都从存储库根运行。第一次运行后添加`-Incremental`以保留生成的项目构建数据。

在不调用 UBT 的情况下暂存或刷新一次性项目：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Mode Prepare `
    -Incremental
```

使用 `-Variant Mixin` 选择保留类版本。它的无头运行时门是：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant Mixin `
    -Mode Smoke `
    -Incremental
```

该门需要原始 `BP_*_C` 类标识、具有不同Profile的两个同时同类对象、Python Move/Aim、自动原始 BP 回退、显式原始 BeginPlay 调用、保留 Blueprint jump/animation、 collectible/HUD循环、实时切换、unregister/re-register和最终恢复。它还检查注册时签名拒绝、缓存失效、回调重入防护、继承的接口所有权、本机const-array/return回退和每个Profile生命周期清理。

更改 Mixin 反射或界面创作助手后，在一次性阶段重新生成五个示例拥有的资产：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant Mixin `
    -Mode GenerateMixinAssets `
    -Incremental
```

该命令构建编辑器目标，并仅将五个经过验证的 `.uasset` 文件复制回示例叠加层中：可玩角色 BP/Mixin 集和三个回归装置。它不会cook/package或编辑Engine/template内容。

重复生成结果`20260831-012003`和模式-4无头烟雾结果`20260831-012054`传递UE5.8.0和引擎CPython3.11.8。 Win64 打包结果 `20260831-014230` 然后构建游戏目标 cooks/stages/archives 并从打包的可执行文件中传递相同的合约。它们共同涵盖了资产创作的角色MixinSet/profile-variable路径、相同BP实例选择、包加载固定装置、回调重入、const-array/return、直接API回归、声明的重新注册和最终恢复。 Cook 日志证明在序列化资产时跳过了命令行引导程序，并且未注册运行时路由器。严格的构建、Cook和运行时扫描都是干净的。该树仅保留可见客户端手动通道。

使用 UE 捆绑的 CPython 3.11 测试与虚幻无关的回合状态，无需构建编辑器：

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
& F:\UnrealEngine\Engine\Binaries\ThirdParty\Python3\Win64\python.exe `
    -m unittest discover `
    -s UEPPythonThirdPerson\Tests `
    -p "test_*.py" `
    -v
```

审计未更改的Blueprint参考资产：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Audit `
    -Incremental
```

运行无头游戏烟雾测试：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Smoke `
    -Incremental
```

Python-第一个烟雾合约需要CPython3.11、三个Python运行时类、映射上下文和恰好五个操作绑定。它通过`IMC_Default`发送真实的`W`press/release，提供`MouseX`/`MouseY`，因此PlayerInput构建映射的`Mouse2D`值，并发送真实的值然后`SpaceBar`press/release.门需要Pythonmovement/look和Started/Completed跳跃回调，真正的跳跃弧，相机组件，观察到的`locomotion`，`jump`， `fall` 和 `land` 动画状态序列，所有六个可收藏球体，一个移动伴侣和一个attached/updated Slate HUD。它执行相同的地图切图，证明新的round/HUD会话并显式检查清理。 JSON 报告和完整日志写在 `.build/Demos/Results/<timestamp>` 下。演示进程禁用 Android 文件服务器、UDP 消息传递和 TCP 消息传递，因为示例不使用游戏网络。演示 Game 目标还禁用 Unreal Trace，因此新打包的可执行文件不会打开其 TCP 1985 控制侦听器。 Editor Play使用稳定的`UnrealEditor.exe`路径。请参阅[`docs/Third_Person_Demo_0.6.0.md`](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Third_Person_Demo_0.6.0.md)中的防火墙说明。

Cook，在打包的Win64构建中打包并执行相同的合约：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Package `
    -Incremental
```

针对源构建引擎的第一个干净包可能是繁重的游戏目标编译，因为项目本地引擎依赖对象尚不存在。它不会修改引擎源。保留暂存的项目并使用 `-Incremental` 在以后的包运行中重用这些对象。 `Prepare` 永远不会调用 UBT，并且 `Smoke` 不会调用 Cook 或包。

<a id="play-the-python-first-demo"></a>

## 播放Python-第一个演示

启动 1280 x 720 独立窗口：

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Play `
    -Incremental
```

使用 WASD 或左摇杆移动，使用鼠标或右摇杆绕摄像机旋转，使用 Space 或游戏手柄正面按钮跳跃。触摸所有六个浮动球体即可完成这一轮。视口HUD显示目标、得分、计时器、速度和Python运动状态。分阶段项目为`.build/Demos/UEPPythonThirdPerson/UEPPythonThirdPerson.uproject`。

要使用官方 Blueprint 类别身份和Mixin Python Move/Aim 玩同一项目，请将命令更改为 `-Variant Mixin`。 HUD 标题显示哪种所有权模型处于活动状态。

<a id="010-overlay-regression"></a>

## 0.1.0 叠加回归

Python-第一个变体现在是默认值。通过传递`-Variant Overlay`，原始集成示例仍然可用。其烟雾测试需要六个Python拾音器和移动立方体伴侣，而官方Blueprint模板继续拥有基本角色控件。

<a id="lyra-integration-development"></a>

## Lyra集成开发

`UEPLyraIntegration` 仍然是已完成的 0.5.0 项目端桥和 Python 游戏探针。新的LyraUI作品有意遵循可玩的第三人称0.6.0里程碑，而不是与之并行开发。它不是Lyra重写：体验激活、游戏功能操作、增强输入所有权、能力授予、GAS执行和复制保留在LyraC++和资产中。 Python 拥有已验证切片的命令值和序列。狭窄的 C++ 适配器拒绝不安全或非权威的写入。自动通道证明了针对完整的LyraUE5.8内容的桥梁，而准备自动化拒绝了真实游戏声明的无内容Git示例。请参阅 [`UEPLyraIntegration/README.md`](UEPLyraIntegration/README.zh-CN.md) 和 [`docs/Lyra_Gameplay_Slice_0.5.0.md`](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Lyra_Gameplay_Slice_0.5.0.md)，以及 [`docs/Lyra_Integration_0.4.0.md`](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Lyra_Integration_0.4.0.md) 中的历史 0.4 边界。
