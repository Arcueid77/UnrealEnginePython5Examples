# 0.10-2I Dash cooldown

Historical batch plan/checkpoint. Current accepted work and remaining gaps are
recorded in PROGRESS.md and Acceptance/07-dash-cooldown.json; the dated
observations below are retained, not a new current-DLL result or next task.

Current: asset authoring, bounded 11-case differential and 19-phase two-client
network pass. The production pool lifetime defect is repaired and verified;
native Dash/death validation is now running. Whole batch/version still open.

Runtime owner: `uep_lyra_hud.dash_cooldown_mixin.LyraDashCooldownPythonProfile`.
Class/layout/animations remain `/ShooterCore/Game/Dash/W_DashCooldown_C`.
Python replaces OnInitialized, ListenForDuration, Construct, Tick,
UpdateCooldownPercent, UpdateVisibility, OnCheckForDeath and OnDeathStarted.
An explicit UEPResumeDashObservation activates a listener without replaying
initialization or resetting charging state. The existing ReadDuration/
BroadcastDuration VM adapter is reused unchanged.

Preserved authored details:

- Pawn (not Controller) equality filters the Dash duration channel. A valid
  owner message stores Duration/StartTime, optionally stops InactiveToActive,
  writes both AnimateArcFill scalars to zero, plays ActiveToInactive and marks
  Charging. Native game time, not wall time or Tick delta, drives the arc.
- Charging completion clears the flag, plays InactiveToActive and writes one.
- A missing Pawn only clears NewHealthComponent. It does not clear Current
  or update visibility. Invalid Health after a change also has no visibility
  continuation. Valid living Health makes CenteringOvr HitTestInvisible;
  dead/invalid explicitly queried Health makes it Collapsed.
- Original old-health bindings are retained until its one-shot death branch,
  rather than silently changing that original policy. All script-owned
  bindings are removed on Profile teardown/Destruct/pool deactivation.
- Native UMG animations have no script completion ownership in this widget;
  live Profile cleanup must not pause them. Differential01 exposed that bug.

Evidence:

- Assets01: copied Interface/CDO and four-node exact original death-delegate
  cleanup; no BP business in the helper. Official asset hash unchanged.
- DashDifferential05: 11 cases / 50.422s / scopes 11/11 / zero active/errors.
  Nine comparisons use the production UI. Two native Destruct/remount cases
  use a separately declared same-class viewport pair, because production
  UIExtension pools do not honor RemoveFromParent like Panel children. PNG
  inspected. Material tolerance tightened to 0.00001, not widened to fix it.
- DashNetwork01: second travel fails with two active production pool entries;
  13 A / 12 B0 phases are not a full network pass.
- The shared pooled_widget_lifetime sampler reads native GetAllEntries and
  closes an entry after it leaves the active pool. No pool mutation or event
  replay. Inactive Tick cannot immediately rebind Health. Snapshot at shutdown
  uses only saved counters. DashNetwork05 passes both travels/rejoin/all exits;
  A/B0 each record an actual deactivation, all final watchers/scopes are closed.
  Dash scopes server/A/B0/B1: 0/0, 14/14, 12/12, 3/3; pool watches 0/0, 4/4,
  4/4, 1/1. Images inspected. Local durations remain synthetic in this lane.
- host-tests11: 276 pass; mocks and artificial report guards are supporting
  evidence, not native pool/ability acceptance.

Continue with current-source standalone and the entire dedicated-server/two-
client lane, including both travels/rejoin/all exits. Then prove unchanged
GA_Hero_Dash -> native GAS -> duration message -> Python UI, native death/invalid
health branches and the affected transport/HUD regressions. No synthetic
message can establish ability production or message replication. Current
package acceptance remains a later combined gate; do not launch a full Engine
build or change reference projects.
