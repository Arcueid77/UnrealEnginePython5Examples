# UnrealEnginePython5 Examples

This is the companion examples repository for
[`AvaloNero/UnrealEnginePython5`](https://github.com/AvaloNero/UnrealEnginePython5).
Its history was split from the core repository, so the 0.1.0 through 0.7.0
sample evolution remains available without keeping demo projects in the plugin
source tree.

The demo driver stages assets from Unreal Engine's official Blueprint Third
Person template under `.build/Demos`, copies the current plugin into that
disposable project and builds it against the configured engine. It never edits
the engine, the engine template, or the reference assets in place. Packaging
uses UE's loose cooked-package writer so Cook and Stage are not coupled to a
transient local Zen process.

The driver needs a checkout of the core plugin. When both repositories are
siblings named `UnrealEnginePython5` and `UnrealEnginePython5Examples`, it finds
the plugin automatically. For any other layout, pass
`-PluginRoot <path-to-UnrealEnginePython5>`. A core checkout that uses this
repository as its `Demos` submodule is also detected automatically.

Three variants are intentionally kept:

| Variant | Purpose | Runtime gameplay owner |
| --- | --- | --- |
| `Overlay` | 0.1.0 compatibility sample | Official Blueprint template plus Python pickups and companion |
| `PythonFirst` | 0.6.0 playable sample | Dynamic Python gameplay classes, collectible loop and viewport HUD |
| `Mixin` | 0.7.0 retained-class sample | Official Blueprint classes with Python `Move`/`Aim`, collectible loop and viewport HUD |

## Blueprint mixin gameplay

The 0.7.0 `Mixin` variant keeps the runtime types
`BP_ThirdPersonGameMode_C`, `BP_ThirdPersonPlayerController_C` and
`BP_ThirdPersonCharacter_C`. The official Enhanced Input EventGraph still
receives actions, but its `Move` and `Aim` calls are redirected to Python. A
mixed `ReceiveBeginPlay` explicitly calls the preserved original before adding
Python behavior. Blueprint/native jump, camera setup and `ABP_Unarmed_C` remain
unchanged.

The smoke contract unregisters the mixin on the already spawned pawn, proves
that the original Blueprint `Move` function is restored and playable, then
registers a new generation on that same object and proves Python movement
again. It also rejects an invalid Python signature without disturbing the
active generation and checks per-object init/teardown for both generations.
This is the live-instance behavior that subclass-based PythonFirst does not
provide.

## Python-first gameplay

The 0.6.0 implementation is the package under
`UEPPythonThirdPerson/Overlay/Content/Scripts/uep_third_person`. The old
`uep_python_third_person.py` path is a compatibility import. At startup the
package creates transient reflected classes and roots them for Unreal's garbage
collector:

- `UEPThirdPersonGameMode` selects the Python pawn and controller classes;
- `UEPThirdPersonPlayerController` installs the official default and mouse-look
  Enhanced Input mapping contexts;
- `UEPThirdPersonCharacter` configures collision and movement, creates the
  spring arm and follow camera, binds move/look/jump actions, and executes those
  actions in Python;
- the character computes speed, falling and landing state in `ReceiveTick` and
  drives the retained blend space and animation sequences through a single-node
  animation instance;
- a world session creates six collectible orbs and a moving companion, owns the
  round/score/timer state and cleanly replaces itself after map travel; and
- `ThirdPersonHUD` attaches a hit-test-invisible Slate tree to the game viewport
  and displays the objective, score, timer, speed and animation state.

The level, mannequin mesh, Input Actions, Input Mapping Contexts, blend space
and animation sequences remain Unreal assets. The original character,
controller, GameMode and AnimBlueprint assets are retained only as the
unchanged reference set; the Python-first game URL selects the transient Python
GameMode instead. Runtime code and the opt-in smoke state machine live in
separate modules.

The overlay also contains an empty `UEPPythonThirdPerson` primary C++ module and
Game/Editor target files. They turn Epic's content-only template into a source
project so UBT can link and stage the source plugin in packaged builds; they do
not implement gameplay or initialize Python.

See [`UEPPythonThirdPerson/BLUEPRINT_INVENTORY.md`](UEPPythonThirdPerson/BLUEPRINT_INVENTORY.md)
for the migration boundary and the audited reference graph counts.

## Automated checks

All commands run from the repository root. Add `-Incremental` after the first
run to retain generated project build data.

Stage or refresh the disposable project without invoking UBT:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Mode Prepare `
    -Incremental
```

Select the retained-class version with `-Variant Mixin`. Its headless runtime
gate is:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant Mixin `
    -Mode Smoke `
    -Incremental
```

That gate requires the original `BP_*_C` class identities, Python Move/Aim,
an explicit original BeginPlay call, retained Blueprint jump/animation, the
collectible/HUD loop, live unregister/re-register and final restoration.
It also checks registration-time signature rejection and per-object lifecycle
teardown.

Current headless evidence is result `20260829-225225` on UE 5.8.0 and engine
CPython 3.11.8. The Mixin Cook/package and visible-client lanes have not yet
been run for 0.7.0.

Test the Unreal-independent round state with UE's bundled CPython 3.11 without
building the Editor:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
& F:\UnrealEngine\Engine\Binaries\ThirdParty\Python3\Win64\python.exe `
    -m unittest discover `
    -s UEPPythonThirdPerson\Tests `
    -p "test_*.py" `
    -v
```

Audit the unchanged Blueprint reference assets:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Audit `
    -Incremental
```

Run the headless gameplay smoke test:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Smoke `
    -Incremental
```

The Python-first smoke contract requires CPython 3.11, the three Python runtime
classes, both mapping contexts and exactly five action bindings. It sends a real
`W` press/release through `IMC_Default`, feeds `MouseX`/`MouseY` so PlayerInput
builds the mapped `Mouse2D` value, and sends a real `SpaceBar` press/release. The
gate then requires the Python movement/look and Started/Completed jump callbacks,
a real jump arc, camera components, the observed `locomotion`, `jump`, `fall` and
`land` animation-state sequence, all six collectible orbs, a moving companion
and an attached/updated Slate HUD. It performs same-map travel, proves a fresh
round/HUD session and explicitly checks teardown. JSON reports and full logs are
written under
`.build/Demos/Results/<timestamp>`. Demo processes disable Android File Server,
UDP Messaging and TCP Messaging because the sample uses no gameplay networking.
The demo Game target also disables Unreal Trace, so newly packaged executables
do not open its TCP 1985 control listener. Editor Play uses the stable
`UnrealEditor.exe` path; see the firewall note in
[`docs/Third_Person_Demo_0.6.0.md`](https://github.com/AvaloNero/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Third_Person_Demo_0.6.0.md).

Cook, package and execute the same contract in the packaged Win64 build:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Package `
    -Incremental
```

The first clean package against a source-built engine can be a heavy Game-target
compile because project-local Engine dependency objects do not exist yet. It
does not modify Engine source. Keep the staged project and use `-Incremental` to
reuse those objects on later package runs; `Prepare` never invokes UBT, and
`Smoke` does not Cook or package.

## Play the Python-first demo

Launch a 1280 x 720 standalone window:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant PythonFirst `
    -Mode Play `
    -Incremental
```

Use WASD or the left stick to move, the mouse or right stick to orbit the camera,
and Space or the gamepad face button to jump. Touch all six floating orbs to
complete the round. The viewport HUD displays the objective, score, timer, speed
and Python locomotion state. The staged project is
`.build/Demos/UEPPythonThirdPerson/UEPPythonThirdPerson.uproject`.

To play the same project with official Blueprint class identities and mixed
Python Move/Aim, change the command to `-Variant Mixin`. The HUD title shows
which ownership model is active.

## 0.1.0 overlay regression

The Python-first variant is now the default. The original integration sample
remains available by passing `-Variant Overlay`. Its smoke test requires the six
Python pickups and moving cube companion while the official Blueprint template
continues to own the base character controls.

## Lyra integration development

`UEPLyraIntegration` remains the completed 0.5.0 project-side bridge and Python
gameplay probe. New Lyra UI work intentionally follows the playable Third Person
0.6.0 milestone rather than being developed in parallel with it.
It is not a Lyra rewrite: Experience activation, Game Feature actions, Enhanced
Input ownership, ability grants, GAS execution and replication stay in Lyra C++
and assets. Python owns the validated slice's command values and sequence; a
narrow C++ adapter rejects unsafe or non-authoritative writes. The automated
lane proves the bridge against complete Lyra UE5.8 content while readiness
automation rejects the content-free Git sample for real gameplay claims. See
[`UEPLyraIntegration/README.md`](UEPLyraIntegration/README.md) and
[`docs/Lyra_Gameplay_Slice_0.5.0.md`](https://github.com/AvaloNero/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Lyra_Gameplay_Slice_0.5.0.md),
plus the historical 0.4 boundary in
[`docs/Lyra_Integration_0.4.0.md`](https://github.com/AvaloNero/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Lyra_Integration_0.4.0.md).
