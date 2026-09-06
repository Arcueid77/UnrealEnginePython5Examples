# UnrealEnginePython5 Examples

This is the companion examples repository for
[`AvaloNero/UnrealEnginePython5`](https://github.com/AvaloNero/UnrealEnginePython5).
Its history was split from the core repository, so the 0.1.0 through 0.8.0
sample evolution remains available without keeping demo projects in the plugin
source tree.

As of the 2026-09-07 review, 0.7.0 is the latest tagged release and 0.8.0 is
unreleased development on `dev/release-0.8.0`. Its implementation and retained
test runs are not yet complete release acceptance.

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
| `Mixin` | 0.7.0 retained-class sample | Official Blueprint classes with per-instance Python profiles, BP fallback, collectible loop and viewport HUD |

## Lyra Python health bar

The 0.8.0 Lyra overlay keeps the official `/Game/UI/Hud/W_Healthbar` path and
`W_Healthbar_C` runtime type. Its example-owned copy adds
`UEPPythonMixinInterface`, a `PythonMixinProfile` selector and
`DA_LyraHealthbarMixin`; all existing Blueprint graphs remain available. Lyra's
Game Feature `Add Widgets` action and CommonUI still create/remove the widget.

The default Python profile owns `Construct`/`Destruct`, follows
`OnPossessedPawnChanged`, binds the active `ULyraHealthComponent`, normalizes
health and decides when to refresh. It calls the retained Blueprint
`SetDynamicMaterials` and `InitializeBarVisuals` functions as visual primitives.
The `BlueprintFallback` profile runs the preserved Blueprint Construct instead.
Gameplay Effects, authority and replication remain native Lyra behavior.

Health data updates are implemented, but damage/heal/death animation selection
and numeric interpolation still need parity fixes and rendered acceptance.
Exactly-one presenter and post-shutdown zero owned callbacks remain required
validation improvements, not currently enforced guarantees.

The core repository's full-content driver stages this overlay into a disposable
copy of `F:\LyraStarterGame`, so neither the reference project nor Unreal Engine
is edited. `GenerateHUDAssets` is the only authoring lane and copies back only
the two verified overlay assets. `Standalone`, `Network`, `Package` and `All`
exercise runtime lanes; `All` includes the heavy Win64 cook/package step.
`HUDAudit` currently runs separately, not as part of `All`. The old green
`full_acceptance` flag therefore does not close the corrected 0.8 release gates.

The runtime code is under
`UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_hud`; the clean-base
authoring and read-only audit scripts are under `UEPLyraIntegration/Tools`, and host-side
presenter contracts are under `UEPLyraIntegration/Tests`.

The agreed next scope is 0.8 health-bar closeout, 0.9 Mixin engineering plus one
weapon/ammo HUD chain and bounded message subscriptions, then an RC freeze and
1.0 supported binding. The remaining combat HUD is 1.1+ backlog. Candidate
records must identify both Examples and core commits; a core `Demos` pin must
match the tested Examples commit. This is release policy, not a new test run.

## Blueprint mixin gameplay

The 0.7.0 `Mixin` variant keeps the runtime types
`BP_ThirdPersonGameMode_C`, `BP_ThirdPersonPlayerController_C` and
`BP_ThirdPersonCharacter_C`. The official Enhanced Input EventGraph still
receives actions. The default `Python` profile implements `Move` and `Aim`;
`BlueprintFallback` implements only `Aim`, so the same class router calls the
preserved Blueprint `Move`. A second Character with the same `BP_*_C` type holds
that fallback profile while the player uses Python. A mixed
`ReceiveBeginPlay` explicitly calls the preserved original before adding Python
behavior. Blueprint/native jump, camera setup and `ABP_Unarmed_C` remain
unchanged.

The examples overlay owns the playable Character's
`DA_ThirdPersonCharacterMixin` plus a same-path project copy of
`BP_ThirdPersonCharacter`. That copy adds `UEPPythonMixinInterface`, two small
selector graphs and an instance-editable `PythonMixinProfile` variable while
retaining the original gameplay graphs. Normal Play registers the plain Python
profile classes from this declaration rather than using decorators or a startup
direct-registration side channel.

Three additional regression assets live under `/Game/UEPTests`: a
`UEPPythonMixinSet`, one component Blueprint that directly declares
`UEPPythonMixinInterface`, and a child Blueprint that inherits it. They exercise
late package-load discovery and inherited router ownership. All five assets are
example-owned overlay files; the generator never edits the installed Engine
template in place.

The smoke contract switches the live pawn between profiles, invalidates the
per-instance cache and proves missing-profile `Move` falls back automatically.
It then unregisters the router on the already spawned pawn and proves that the
original Blueprint `Move` function is restored and playable. Finally it tests a
direct-API generation and a second declared-Mixin-Set generation on the same
object, proving Python movement in both before final restoration. It also
rejects an invalid Python signature without disturbing the active router and
checks balanced per-profile init/teardown.
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

That gate requires the original `BP_*_C` class identities, two simultaneous
same-class objects with different profiles, Python Move/Aim, automatic original
BP fallback, an explicit original BeginPlay call, retained Blueprint
jump/animation, the collectible/HUD loop, live switching,
unregister/re-register and final restoration. It also checks registration-time
signature rejection, cache invalidation, callback-reentry guards, inherited
Interface ownership, native const-array/return fallback and per-profile
lifecycle teardown.

After changing Mixin reflection or the Interface authoring helper, regenerate
the five example-owned assets in the disposable stage:

```powershell
.\Run-UEPThirdPersonDemo.ps1 `
    -EngineRoot F:\UnrealEngine `
    -Variant Mixin `
    -Mode GenerateMixinAssets `
    -Incremental
```

The command builds the Editor target and copies only the five verified `.uasset`
files back into the examples overlay: the playable Character BP/Mixin Set and
the three regression fixtures. It does not cook/package or edit Engine/template
content.

Repeat-generation result `20260831-012003` and schema-4 headless smoke result
`20260831-012054` pass on UE 5.8.0 and engine CPython 3.11.8. Win64 Package
result `20260831-014230` then builds the Game target, cooks/stages/archives and
passes the same contract from the packaged executable. Together they cover the
asset-authored Character MixinSet/profile-variable path, same-BP instance
selection, package-load fixture, callback-reentry, const-array/return,
direct-API regression, declared re-registration and final restoration. The Cook
log proves commandlet bootstrap was skipped and no runtime router was registered
while assets were being serialized. Strict build, Cook and runtime scans are
clean. Only the visible-client manual lane remains for this tree.

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
