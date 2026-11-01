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
