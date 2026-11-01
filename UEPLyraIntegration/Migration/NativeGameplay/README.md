# Native gameplay migration

The approved scope is CPP-001 through CPP-015 in `../cpp_batches.json`.
The earlier Blueprint acceptance remains a separate completed scope.

CPP01 replaces elimination streak, elimination chain, and assist rules. Native
Gameplay Message subscriptions and their shutdown remain in C++. Four native
callbacks enter reflected `BlueprintNativeEvent` functions; persistent classes
select the `Python` implementation or the retained `NativeFallback` body.

`CPP01-message-rules.patch` is the exact source change. The transformation checks
the original source census hashes and only writes to a marked, independently
copied validation project. The official Lyra project is the read-only reference.
The original streak and chain Blueprint classes, defaults, and graphs remain;
assist uses one thin Blueprint subclass. The shared accolade ActionSet changes
only that assist component reference, preserving its server/client roles.

Run the main repository's validation entry points in order:

1. `Validation/Run-UEP58NativeMessageBuild.ps1` generates only ShooterCoreRuntime
   headers and compiles/links that module using the accepted native dependencies.
2. `Validation/Run-UEP58NativeMessageAuthoring.ps1` generates and checks the three
   declarations, retaining the original class defaults and graph semantics.
3. `Validation/Run-UEP58NativeMessageValidation.ps1` compares real native callback
   dispatch for synthetic messages. It checks float accumulation, broadcast order,
   reentrant assist clearing, exact native clock boundaries, and listener teardown.
4. `Validation/Run-UEP58NativeMessageNetworkValidation.ps1` uses a dedicated server
   and two actual clients. Native GAS damage and HealthSet deaths must produce the
   assists, five-kill streak, rapid chains, scores, and owner notifications. It does
   not fabricate Verb messages, health, damage immunity, or score statistics.

Each run requires a fresh evidence directory. Inputs are frozen while processes
run, with archived scripts and controls. Failed attempts are retained. Live JSON
must be read through `uep_lyra_network_io.read_json` so observation cannot prevent
Windows atomic replacement. No test in this batch establishes another platform,
configuration, package, or the remaining C++ candidates.

## CPP02: team selection

[CPP02 acceptance](CPP02-acceptance.json) covers choosing a player's team and the
least-populated team calculation. Two native policy events and one thin reflected
setter are in `CPP02-team-rules.patch`. The setter calls the original native
`SetGenericTeamId`, preserving its notifications. Team creation, experience
callbacks, authority rules, and the two/four-team configuration Blueprints remain.

The team validation entry points are `Run-UEP58NativeTeamBuild.ps1`,
`Run-UEP58NativeTeamAuthoring.ps1`, and `Run-UEP58NativeTeamValidation.ps1` in the
main repository's `Validation` directory. Only the two affected LyraGame unity
units are compiled; the unchanged unit is reused. `-Families Four` reruns only
the four-team family after the two-team family has passed.

Six native/Python cases cover equal population, unequal population, inactive
players, spectators, the original four-team IDs, and no configured teams. Native
team notifications and fixture restoration are checked. The four-team map has one
natural local owner; three temporary native PlayerState actors provide the
population fixture and are destroyed afterward. This does not claim a four-owner
network test. The actual dedicated-server/two-client run uses
`Run-UEP58NativeMessageNetworkValidation.ps1 -ValidateTeam` with the team asset
evidence. It verifies eleven natural bot/owner assignments, balanced populations,
and the affected CPP01 damage, score replication, and notification pipeline.

## CPP03: bot count, names, and removal choice

[CPP03 acceptance](CPP03-acceptance.json) covers the normal and control-point bot
spawners. Python handles effective count, remaining name selection, fallback
names, and the random removal index. Native code still creates controllers,
initializes players, restarts Pawns, applies self-destruct damage, and destroys
controllers. Random selection calls the native RNG. The performance test spawner
retains its custom Blueprint creation graph and native fallback, as in the
original Blueprint test-tooling exclusion.

Use the main repository's `Run-UEP58NativeBotBuild.ps1`,
`Run-UEP58NativeBotAuthoring.ps1`, and `Run-UEP58NativeBotValidation.ps1` entry
points. The compile rebuilds LyraGame units 1/2 and reuses the accepted CPP02 team
object in unit 3. Native/Python runs for both production families verify missing
controller configuration, default and URL count precedence, zero/negative counts,
name exhaustion, nine native removals/deaths, and nonempty Python state teardown.
No exact RNG sequence or separate PIE editor-override acceptance is claimed.

The actual three-peer run adds `-ValidateBots` and the bot asset evidence to
`Run-UEP58NativeMessageNetworkValidation.ps1`. It verifies nine naturally created
and named bots, plus the affected CPP01 and CPP02 damage/notification/team gates.
