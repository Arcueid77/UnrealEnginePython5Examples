# 0.10-2H ability-failure feedback: audit / next implementation

Historical batch plan/checkpoint. Current accepted work and remaining gaps are
recorded in PROGRESS.md and Acceptance/06-ability-failure.json; the dated
observations below are retained, not a new current-DLL result or next task.

Status: bounded original-BP/runtime differential and native FText identity
passed; 237 host checks pass. Accepted runs: Assets06, FailureDifferential06
(17 cases) and NativeCulture02 (one native-text broadcast, en/zh-Hans/en).
Corrected visible screenshots were inspected. AbilityFailureNetwork02 is
running; native GAS producer, dead/invalid health, current adapter regressions,
package and whole-version acceptance remain open. Early restricted startup
failures and superseded timer models are historical failed attempts, not the
current implementation.
Preserve Engine/official Lyra, animation/editor/test assets,
mixed worktrees and incomplete-release publication boundaries.

Candidate: `/ShooterCore/UserInterface/HUD/W_AbilityFailureFeedback` (retained
LyraTaggedWidget class/layout). The static audit lists three entries / 31
business nodes; this is not a migration-completion count.

Observed authored dependencies:

- OnInitialized collapses the widget and listens ExactMatch on
  `Ability.UserFacingSimpleActivateFail.Message`. Unlike ability progress,
  the async factory `then` has no continuation: a proxy ownership store must
  handle that topology without inventing a business continuation.
- Native `FLyraAbilitySimpleFailureMessage` has PlayerController, FailureTags
  and UserFacingReason (FText). `ULyraGameplayAbility::NativeOnAbilityFailedToActivate`
  remains the unchanged producer; Python must only own UI policy/presentation.
- Graphs compare owning PlayerController and current reason, query native
  Pawn health/death, set text/visibility, play retained UI animations and use
  a one-second RetriggerableDelay. Preserve the exact branch order/defaults.
- OutroCompleted / OutroCurrentCompleted are authored animation-completion
  entries. The animation assets remain; callback policy and cleanup migrate.

Implementation order:

1. Trace compact pin links and obtain current reflected signatures/defaults.
   Confirm how native FText is transported/written without claiming localized
   identity preservation from a string-only visual comparison.
2. Add a typed VM reader/broadcaster for this payload only. Prior six graphs
   must retain semantic digests and current UI/Verb/Duration runtime regressions.
   Keep helper nodes conversion/ownership-only, not UI decisions.
   The generator now includes native FText copy/equality primitives so policy
   never accesses UserFacingReason as a Python string. Assets06 passes clean
   compilation, and NativeCulture02 proves live native localization identity.
3. Implement owner/reason/death policy, native widget latent delay,
   retained animation playback/completion and disarmed cleanup in Python.
   Never use an unvalidated wildcard/latent ProcessEvent placeholder. Bound
   timer/animation support first, rather than claiming generic latent support.
   The accepted implementation calls native RetriggerableDelay with an explicit
   LatentActionInfo and an int32 Linkage completion declaration. It uses the
   widget's original native latent scheduler, including expiry while the world
   is paused. No external ticker, new Tick business, generic latent support or
   additional dynamic animation delegate is claimed. The world-clock/tick-delta
   prototypes failed comparison and were removed. Seventeen runtime cases now
   verify native timing and original persistent callback/deferred-payload order.
4. Rearm idempotently at natural Construct (including collapsed widget reuse),
   disarm at Destruct/Profile teardown, and keep explicit hidden live-profile
   activation distinct from lifecycle replay. Cancel the saved original proxy
   and any fallback latent/animation callback using exact owned cleanup.
5. Focused original-BP/Python cases: owner/foreign, same/different/repeated reason,
   real pause clock, retrigger before deadline, death/invalid-health branches,
   interrupted outro, hidden Profile switch, remount and no late callbacks.
   `ability_failure_validation.py` and its focused driver now implement seventeen
   ordered production-widget/original-BP checks, passed in FailureDifferential06.
   The first-delay gate rejects a mismatch larger than two observed UI frames
   (hard ceiling 0.15s),
   rather than silently widening the tolerance. Actual original deferred payload
   and persistent completion result pass against the actual baseline, not only
   a source model. Synthetic FText display comparison does not
   prove localization history. Dead/invalid health stays an additional native
   gate, not part of this seventeen-case fixture. The original-BP baseline is
   listener-resumed; original OnInitialized is not replayed by the fixture.
   Failed asset authoring blocks the runtime driver before launch; this guard
   was actually checked in `20261014-batch2h/fixture-preflight01.json`.
6. Then production reachability / unchanged native ability producer and two
   clients / travel / restart / rejoin / all exits. Synthetic payload success
   is not native GAS failure production or network replication evidence.

Current matching Editor binaries should be reused. If a selected unsupported
binding requires a narrowly scoped UEP module change, announce that scope first;
do not start an Engine rebuild or package as a default implementation step.

The bool equality adapter has a named output: it returns `(bool,)`, not a bare
bool. FailureDifferential04 exposed an incorrect truthiness check; the policy
and host mock now validate/extract the actual reflection shape. Failed timing,
authoring and screenshot attempts remain documented in PROGRESS/history.
