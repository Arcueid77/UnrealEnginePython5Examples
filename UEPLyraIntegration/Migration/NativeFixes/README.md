# Isolated Lyra simulated-proxy initialization guard

The user approved this native game-C++ followup on 2026-10-26. It is separate
from the original 246 Python candidates. Official `F:/LyraStarterGame` stays
unchanged; the patch applies only to a marked disposable validation stage.

`LyraHeroComponent-simulated-proxy-owner.patch` adds eight lines before the
DataAvailable -> DataInitialized transition. A simulated proxy waits until its
PlayerState's native Pawn points to it, before binding the persistent ability
system. Authority and autonomous initialization retain their existing path.
The guard never writes Health or manually initializes an ability system.

The build driver checks the original source fingerprint, applies only this
insertion, and reuses the stage's generated MSVC response files. It compiles
the one unity unit containing HeroComponent and performs the two LyraGame link
steps. Engine binaries, NetCore object/import library and the UEP/bridge DLLs
are fingerprint protected. There is no Engine rebuild, cook or package.

From the core repository, use fresh private output folders with
`Validation/Run-UEP58LyraPawnInitGuardBuild.ps1 -OutputDirectory <build-folder>`,
then `Validation/Run-UEP58LyraPawnInitGuardValidation.ps1 -OutputDirectory
<run-folder> -BuildEvidenceDirectory <build-folder>`. Both folders must be under
the workspace `.build` directory. The stage must already have matching generated
build commands and the accepted SDK; this is an incremental refresh driver.

Batch246 records two fresh dedicated-server/two-client runs, with the second
client launched after eight seconds and with both clients launched immediately.
Each passed 20 original/Python authority interactions and 40 replicated viewer
checks. Twelve captured simulated-proxy waits stayed unbound until canonical
initialization; no canonical GameplayReady/healthy-attribute/empty-binding row
was observed. The old failed gameplay record remains intact.

The exact earlier retired-channel sequence is timing dependent and was not
deterministically replayed. These runs prove the observed init-state behavior
and affected interaction matrix, rather than arbitrary network stability.
The original official-source issue remains recorded while its source is
unmodified. Full version, package, presentation and migration acceptance remain
separate. See `../Acceptance/246-isolated-native-pawn-init-guard-and-network-regression.json`.
