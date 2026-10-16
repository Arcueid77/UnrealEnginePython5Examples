"""Native lethal authority GAS -> ServerInitiated owner -> two real Cue viewers.

Files only schedule/ack the experiment. They do not deliver GAS events, damage,
replicated state or Cue payloads. The unchanged native transport does all that.
"""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import death_mixin as policy, death_observation as observation
from .death_contract import PLAN, require
from .death_validation import Validation as NativeDeath, RESPAWN
from .jump_network_validation import Server as NativePlayingFixture, arg

PEERS, TOTAL = ("A", "B0"), len(PLAN)*4
FLAGS = ("full_acceptance", "packaged_runtime", "physical_input_tested", "death_event_sent_by_probe",
    "ability_activation_called_by_probe", "callback_replay", "health_properties_written", "death_duration_written",
    "packet_loss_tested", "travel_rejoin_tested")


def delta(before):
    return {key: value-before[key] for key, value in policy.snapshot().items() if type(value) is int and key != "active_count"}


def instances(asc, cls):
    return [value for spec in asc.get_property("ActivatableAbilities").Items
        if valid(spec.Ability) and spec.Ability.get_class() == cls
        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]


def health(pawn):
    return pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))


def pawn_state(pawn):
    component = health(pawn)
    return dict(pawn=pawn.get_path_name(), health=float(component.call_function("GetHealth")), death=int(component.call_function("GetDeathState")))


class Server(NativeDeath):
    def __init__(self, result, run):
        super().__init__(result)
        self.run, self.root, self.position, self.expected_cues = run, Path(result).parent, 0, 0
        self.source_observer_uses_death = True
        self.hold_respawn_fixture = True
        self.fixture = NativePlayingFixture(result, run); self.fixture.ability_class = policy.CLASS
        self.statics, self.phase = self.fixture.statics, "setup"
        self.report.update({key: False for key in FLAGS})
        self.report.update(peer="server", run_id=run, server_waited_for_client_process_exit=False, player_ids={})

    def prepare(self):
        self.target, self.index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        owner = self.fixture.owners[self.target]
        require(time.monotonic()-self.phase_started < 15., "native Death preparation gate: "+repr(getattr(self, "attach_status", None)))
        if not self.attach(self.fixture.world, self.fixture.bridge, owner["controller"]): return
        rows = self.bridge.call_function("CapturePlayerSnapshots")
        ready = [row for row in rows if int(row.PlayerId) == owner["player_id"]]
        self.attach_status["authority_ready"] = [dict(health_ready=bool(row.bHealthReady), health=float(row.Health),
            damage_immune=bool(row.bDamageImmune)) for row in ready]
        if not ready or not (ready[0].bHealthReady and ready[0].Health > 0 and not ready[0].bDamageImmune): return
        self.other = self.fixture.owners[PEERS[1] if self.target == PEERS[0] else PEERS[0]]["controller"]
        self.other_before = pawn_state(self.other.get_controlled_pawn())
        profile = ("BlueprintFallback", "Python")[self.index % 2]
        ue.set_mixin_profile(self.ability, profile)
        atomic_write(self.root/"arm.json", dict(run_id=self.run, position=self.position, target=self.target,
            index=self.index, name=PLAN[self.index//2], profile=profile, player_id=owner["player_id"]))
        self.enter("armed")

    def begin(self):
        NativeDeath.begin(self)
        self.row.update(position=self.position, target=self.target, index=self.index, name=self.name, profile=self.profile,
            other_owner_unchanged=True, health_after=self.row["health_after_damage"])
        self.report["real_lethal_gas_damage"] = True

    def respawn(self):
        pawn = self.controller.get_controlled_pawn()
        if not valid(pawn) or pawn.get_path_name() == self.old_pawn: return
        native = pawn_state(pawn)
        if native["health"] <= 0 or native["death"] != 0: return
        self.row.update(new_pawn=native["pawn"], respawn_health=native["health"], counters=delta(self.before))
        self.enter("ack")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native Death network authority timeout: "+self.phase)
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                else:
                    self.fixture.bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.fixture.world)
                    self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
                    self.enter("prepare")
            else:
                isolate_bots(self.statics, self.fixture.world, ue.find_class("LyraPlayerBotController"))
                if self.phase == "prepare": self.prepare()
                elif self.phase == "armed":
                    require(time.monotonic()-self.phase_started < 20., "native Death clients did not arm")
                    armed = [read_json(self.root/(peer+"-armed.json")) for peer in PEERS]
                    if all(row is not None and (row["run_id"], row["position"]) == (self.run, self.position) for row in armed): self.begin()
                elif self.phase == "death": self.observe()
                elif self.phase == "respawn": self.respawn()
                elif self.phase == "ack":
                    acks = [read_json(self.root/(peer+"-"+str(self.position)+"-ack.json")) for peer in PEERS]
                    if all(row is not None and (row["run_id"], row["position"]) == (self.run, self.position) for row in acks):
                        self.report["cases"].append(copy.deepcopy(self.row))
                        ue.log("UEP_DEATH_NETWORK_CASE_OBSERVED "+str(self.position)+"/"+self.target+"/"+self.name)
                        self.position += 1; self.enter("release" if self.position == TOTAL else "prepare")
                elif self.phase == "release":
                    atomic_write(self.root/"release.json", dict(run_id=self.run))
                    exited = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                    if all(row is not None and row["exit_code"] == 0 for row in exited):
                        self.report["server_waited_for_client_process_exit"] = True; self.finish()
                if self.phase in ("death", "respawn", "ack"):
                    self.row["other_owner_unchanged"] &= pawn_state(self.other.get_controlled_pawn()) == self.other_before
                    require(self.row["other_owner_unchanged"], "native Death changed the foreign owner")
            atomic_write(self.root/"server-status.json", dict(phase=self.phase, position=self.position,
                elapsed_seconds=time.monotonic()-self.started, attach_status=getattr(self, "attach_status", None)))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.restore_respawn_fixture()
            self.close_source()
            if hasattr(self, "ability") and valid(self.ability): ue.set_mixin_profile(self.ability, "Python")
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_DEATH_NETWORK_AUTHORITY_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DEATH_NETWORK_"+self.report["status"].upper())


class Client:
    def __init__(self, result, peer, run):
        self.path, self.root, self.peer, self.run = Path(result), Path(result).parent, peer, run
        self.started, self.finished, self.phase, self.position = time.monotonic(), False, "ready", -1
        self.target_path, self.cues, self.observation_errors = None, [], []
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(schema_version=1, status="running", error=None, run_id=run, peer=peer, cases=[],
            cue_observer_restored=False, **{key: False for key in FLAGS})

    def find_pawn(self, player_id):
        pawns, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraCharacter"))
        matches = [pawn for pawn in pawns if valid(pawn) and valid(pawn.PlayerState) and int(pawn.PlayerState.PlayerId) == player_id]
        return matches[0] if len(matches) == 1 else None

    def ready(self):
        gate = read_json(self.root/"playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run, "foreign Death native Playing gate")
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bAbilitySystemReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune): continue
            require(str(snap.NetMode) == "Client", "Death viewer is not a real native client")
            self.world, self.bridge = world, bridge
            self.controller = self.statics.call_function("GetPlayerController", world, 0)
            self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
            self.cls, self.cue_cls = ue.load_class(policy.CLASS), ue.load_class(observation.CUE)
            require(not any(row["target_class"] == self.cue_cls for row in ue.get_registered_mixins()), "production Death Cue must remain unmixed")
            self.original_cue = self.cue_cls.get_cdo().find_function("OnBurst")
            owner = self
            class ObserveCue:
                def OnBurst(self, Target, Parameters, SpawnResults):
                    try:
                        if observation.path(Target) == owner.target_path:
                            owner.cues.append(observation.cue(Target, Parameters))
                    except Exception: owner.observation_errors.append(traceback.format_exc())
                    return self.call_mixin_original("OnBurst", Target, Parameters, SpawnResults)
            ue.register_mixin_profile(self.cue_cls, "UEPDeathNetworkCueObserve", ObserveCue, make_default=True)
            atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
            self.phase = "idle"; return

    def arm(self, command):
        require(command["run_id"] == self.run and command["position"] == self.position+1, "foreign/out-of-order Death command")
        pawn = self.find_pawn(command["player_id"])
        if not valid(pawn) or pawn_state(pawn)["health"] <= 0: return
        self.is_owner = command["target"] == self.peer
        if self.is_owner:
            snap = self.bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and not snap.bDamageImmune): return
            abilities = instances(ability_system(pawn), self.cls)
            if len(abilities) != 1 or abilities[0].get_property("bIsActive"): return
            self.ability = abilities[0]
            owners = instances(ability_system(pawn), ue.load_class(RESPAWN))
            require(len(owners) == 1, "owning native AutoRespawn fixture instance missing")
            self.respawn_owner = owners[0]
            self.original_respawn_delay = float(self.respawn_owner.RespawnDelayDuration)
            self.fixture_respawn_delay = float(self.ability.Duration)+1. if command["name"] in ("native-timer", "native-cancel-refused") else self.original_respawn_delay
            self.respawn_owner.set_property("RespawnDelayDuration", self.fixture_respawn_delay)
            self.respawn_fixture_pending = True
            ue.set_mixin_profile(self.ability, command["profile"])
            require(str(ue.get_mixin_profile(self.ability)) == command["profile"], "owning native Death Profile not selected")
        self.position, self.command, self.pawn = command["position"], command, pawn
        self.target_path, self.cues, self.observation_errors = pawn.get_path_name(), [], []
        self.before = policy.snapshot()
        self.row = dict(position=self.position, target=command["target"], index=command["index"], profile=command["profile"],
            old_pawn=self.target_path, native_health_zero_seen=False, native_respawn_seen=False,
            owner_activation_observed=False, death_camera_matched=False, native_type_preserved=False, native_cancelable=None,
            respawn_delay_restored=not self.is_owner)
        self.phase = "observe"
        self.trial_started = time.monotonic()
        atomic_write(self.root/(self.peer+"-armed.json"), dict(run_id=self.run, position=self.position, old_pawn=self.target_path))

    def observe(self):
        require(time.monotonic()-self.trial_started < 35., "native Death viewer did not observe damage/Cue/respawn: "+repr(self.row))
        require(not self.observation_errors, "native replicated Cue observation failed: "+repr(self.observation_errors))
        if valid(self.pawn):
            component = health(self.pawn)
            if valid(component): self.row["native_health_zero_seen"] |= component.call_function("GetHealth") == 0
        if self.is_owner and self.ability.get_property("bIsActive"):
            require(float(self.respawn_owner.RespawnDelayDuration) == self.fixture_respawn_delay, "owning-client fixture delay changed during death")
            hero = self.pawn.get_component_by_type(ue.find_class("LyraHeroComponent"))
            self.row.update(owner_activation_observed=True, native_type_preserved=self.ability.get_class() == self.cls,
                native_cancelable=bool(self.ability.get_property("bIsCancelable")),
                death_camera_matched=hero.get_property("AbilityCameraMode") == self.ability.get_property("Camera Mode"),
                owner_event=observation.event(self.ability.get_property("CurrentEventData")))
        elif self.is_owner and self.row["owner_activation_observed"]: self.restore_respawn_fixture()
        pawn = self.find_pawn(self.command["player_id"])
        if not valid(pawn) or pawn.get_path_name() == self.target_path or pawn_state(pawn)["health"] <= 0: return
        if self.is_owner:
            snap = self.bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and not snap.bDamageImmune): return
            require(not self.ability.get_property("bIsActive"), "owning native Death survived respawn")
            ue.set_mixin_profile(self.ability, "Python")
        self.row.update(native_respawn_seen=True, new_pawn=pawn.get_path_name(), cues=copy.deepcopy(self.cues), counters=delta(self.before))
        require(self.row["native_health_zero_seen"] and len(self.cues) == 1, "real replicated Death/Cue missing or duplicated")
        self.report["cases"].append(copy.deepcopy(self.row))
        self.phase = "idle"
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run, position=self.position))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native Death client timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "observe": self.observe()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run and len(self.report["cases"]) == TOTAL, "Death release before full native viewer matrix")
                    self.finish(); return False
                command = read_json(self.root/"arm.json")
                if command is not None and command["position"] > self.position: self.arm(command)
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.restore_respawn_fixture()
            if hasattr(self, "ability") and valid(self.ability): ue.set_mixin_profile(self.ability, "Python")
            if hasattr(self, "cue_cls"):
                require(ue.unregister_mixin(self.cue_cls) and self.cue_cls.get_cdo().find_function("OnBurst") == self.original_cue,
                    "native Death viewer Cue function not restored")
                self.report["cue_observer_restored"] = True
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_DEATH_NETWORK_VIEWER_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def restore_respawn_fixture(self):
        if getattr(self, "respawn_fixture_pending", False):
            self.respawn_owner.set_property("RespawnDelayDuration", self.original_respawn_delay)
            self.respawn_fixture_pending = False
            if hasattr(self, "row"):
                self.row["respawn_delay_restored"] = float(self.respawn_owner.RespawnDelayDuration) == self.original_respawn_delay

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DEATH_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDeathNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDeathNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
