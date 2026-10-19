"""Real native Cue events, original UMG widgets and manager-driven add/removal."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer, GameplayEffectContextHandle
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from uep_lyra_world.effect_pad_mixin import valid
from . import cue_widget_mixin as policy
from .cue_widget_contract import PROFILES, CLASSES, CASES, require, validate

CHILDREN = {
    "match":"/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided_C",
    "waiting":"/ShooterCore/GameplayCues/GCNL_WaitingForPlayers.GCNL_WaitingForPlayers_C"}
MATCH = "/ShooterCore/GameplayCues/W_MatchDecided_Message.W_MatchDecided_Message_C"
WAITING = "/ShooterCore/GameplayCues/W_WaitingForPlayers_Message.W_WaitingForPlayers_Message_C"


def dead(actor): return not valid(actor) or actor.call_function("IsActorBeingDestroyed")


def payload(params):
    return dict(raw=float(params.RawMagnitude), normalized=float(params.NormalizedMagnitude),
        instigator=params.Instigator.get_path_name() if valid(params.Instigator) else None,
        causer=params.EffectCauser.get_path_name() if valid(params.EffectCauser) else None,
        level=int(params.GameplayEffectLevel))


class Validation(Ready):
    healths = Health.healths
    def __init__(self, result):
        super().__init__(result); self.require_auto_active = False
        self.actors = []; self.cue_actors = []; self.widgets = []; self.base_sources = {}; self.interface_events = []; self.current = None; self.manager_started = []
        self.report = dict(status="running", error=None, cases=[], manager_cases=[], full_acceptance=False, network_acceptance=False,
            packaged_runtime=False, pixels_tested=False, audio_playback_tested=False, native_remote_controller_branch_tested=False,
            message_widget_business_migrated=False, cue_manager_callbacks_replayed=False, health_properties_written=False)
    def own(self, cls=None):
        actor = self.world.actor_spawn(cls or ue.find_class("Actor")); self.actors.append(actor); actor.call_function("SetReplicates", False); return actor
    def begin(self):
        bridge = policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld", self.world)
        self.report["native_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"] == "Standalone", "native standalone widget Cue required")
        self.health_before = self.healths(); self.game_state = self.statics.call_function("GetGameState", self.world)
        self.players_before = list(self.game_state.get_property("PlayerArray"))
        self.base_cls = ue.load_class(policy.CLASS); ue.register_declared_mixin(self.base_cls)
        end_signature = ue.describe_function(self.base_cls,"K2_EndGameplayCue")
        self.report["native_end_cue_owner"] = end_signature["owner"]
        fixture = ue.load_class("/Game/UEPValidation/BP_CueWidgetBaseFixture.BP_CueWidgetBaseFixture_C")
        self.report["abstract_base_verified_through_concrete_fixture"] = fixture != self.base_cls and fixture.get_cdo().is_a(self.base_cls)
        self.classes = dict(base=fixture, **{name:ue.load_class(path) for name,path in CHILDREN.items()})
        self.match_widget = ue.load_class(MATCH); self.waiting_widget = ue.load_class(WAITING)
        self.probe = ue.load_class("/Game/UEPValidation/BP_CueWidgetCaller.BP_CueWidgetCaller_C").get_cdo(); self.probe.add_to_root()
        music_cls = ue.load_class("/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C")
        self.music = self.game_state.get_component_by_type(music_cls)
        self.music_fields = {name:self.music.get_property(name) for name in ("Music System", "Alpha_Intensity", "Alpha_Mvmt", "bIsMenu")}
        # Keep real match-widget construction/Stinger calls, without mutating live audio parameters.
        self.music.set_property("Music System", None)
        self.foreign = self.own(); self.foreign.add_actor_root_component(ue.find_class("SceneComponent"), "UEPCueWidgetTarget")
        self.orphan = self.own(ue.find_class("PlayerState")); self.bot = self.own(ue.find_class("PlayerState")); self.bot.set_property("bIsABot", True)
        self.observe(); self.matrix(); self.manager_index = 0; self.start_manager()
    def observe(self):
        row, = [r for r in ue.get_registered_mixins() if r["target_class"] == self.base_cls]
        self.base_sources = {name:value["python_class"] for name,value in row["profiles"].items()}; owner = self
        for profile,source in self.base_sources.items():
            def around(handler, event, selected):
                def invoke(actor, Target, Parameters, SpawnResults):
                    if event == "start" and hasattr(owner,"manager_target") and Target == owner.manager_target:
                        owner.manager_started.append(actor)
                    return handler(actor, Target, Parameters, SpawnResults)
                invoke.override = policy.START if event == "start" else policy.REMOVE; return invoke
            ue.register_mixin_profile(self.base_cls, profile, type("ObservedCueWidget"+profile, (), dict(Start=around(source.Start,"start",profile), Remove=around(source.Remove,"remove",profile))))
        require(not any(r["target_class"] == self.match_widget for r in ue.get_registered_mixins()), "do not replace a production message widget Profile")
        self.original_interface = self.match_widget.get_cdo().find_function("ConstructFromCueParams")
        class ObserveInterface:
            def ConstructFromCueParams(widget, Params):
                owner.interface_events.append((widget, payload(Params)))
                return widget.call_mixin_original("ConstructFromCueParams", Params)
        ue.register_mixin_profile(self.match_widget, "UEPCueWidgetObserve", ObserveInterface, make_default=True)
    def params(self, instigator, raw=1.):
        return policy.lib("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters", NormalizedMagnitude=.125, RawMagnitude=raw,
            EffectContext=GameplayEffectContextHandle(), MatchedTagName=GameplayTag(), OriginalTag=GameplayTag(),
            AggregatedSourceTags=GameplayTagContainer(), AggregatedTargetTags=GameplayTagContainer(), Location=ue.FVector(121.,42.,17.), Normal=ue.FVector(0.,0.,1.),
            Instigator=instigator, EffectCauser=self.foreign, SourceObject=None, PhysicalMaterial=None, GameplayEffectLevel=3, AbilityLevel=2,
            TargetAttachComponent=None, bReplicateLocationWhenUsingMinimalRepProxy=False)
    def collect(self, actor, before):
        widget = actor.get_property("SpawnedWidget")
        if valid(widget) and widget not in self.widgets: self.widgets.append(widget)
        return widget
    def widget_state(self, actor):
        widget = actor.get_property("SpawnedWidget")
        result = dict(controller_is_local=actor.get_property("OptionalLocalController") == self.controller,
            widget_valid=valid(widget), in_viewport=valid(widget) and bool(widget.call_function("IsInViewport")))
        if not valid(widget): return result
        result.update(widget_owner_is_local=widget.call_function("GetOwningPlayer") == self.controller, widget_class=widget.get_class().get_path_name(), visibility=int(widget.call_function("GetVisibility")))
        if widget.is_a(self.match_widget):
            result.update(team=int(widget.get_property("Team")), text=str(widget.get_property("VictoryMessage").call_function("GetText")),
                victory_animation=bool(widget.call_function("IsAnimationPlaying",widget.get_property("VictoryIntro"))), defeat_animation=bool(widget.call_function("IsAnimationPlaying",widget.get_property("DefeatIntro"))))
        else:
            result.update(text=str(widget.get_property("TeamNotification").call_function("GetText")), countdown_started=bool(widget.get_property("CountdownStarted")))
        return result
    def matrix(self):
        for label in CLASSES:
            for profile in PROFILES:
                for name in CASES:
                    actor = self.own(self.classes[label]); self.cue_actors.append(actor); ue.set_mixin_profile(actor,profile); self.current = actor
                    if label == "base": actor.set_property("WidgetToSpawn", self.waiting_widget)
                    selected = "python" if profile == "Python" else "fallback"; before = dict(policy.evidence(actor)); events_before = len(self.interface_events); created_before = len(self.widgets)
                    returns = []; seed = None
                    if name not in ("local", "none"):
                        returns.append(actor.call_function("WhileActive",self.foreign,self.params(self.controller.PlayerState)))
                        seed = self.collect(actor,None); require(valid(seed),"native seed widget missing")
                    instigator = {"none":None,"foreign":self.foreign,"orphan":self.orphan,"bot":self.bot}.get(name,self.controller.PlayerState)
                    if name == "missing-widget": actor.set_property("WidgetToSpawn",None)
                    if name in ("local", "none"):
                        returns.append(actor.call_function("WhileActive",self.foreign,self.params(instigator)))
                    else:
                        # Re-enter only the BP business event. Repeating native
                        # WhileActive bypasses the manager guard and appends FX
                        # slots, violating the native StopEffects precondition.
                        returns.append(actor.call_function("OnLoopingStart",self.foreign,self.params(instigator),actor.get_property("LoopingSpawnResults")))
                    widget = self.collect(actor,seed); state = self.widget_state(actor)
                    sound_slots = len(actor.get_property("LoopingEffects").LoopingSounds)
                    spawned_slots = len(actor.get_property("LoopingSpawnResults").AudioComponents)
                    controller = actor.get_property("OptionalLocalController")
                    for _ in range(2): returns.append(actor.call_function("OnRemove",self.foreign,self.params(instigator)))
                    after = policy.evidence(actor)
                    self.report["cases"].append(dict(**{"class":label},profile=profile,name=name,
                        actual_start_entries=after[selected+"_start"]-before[selected+"_start"],actual_remove_entries=after[selected+"_remove"]-before[selected+"_remove"],
                        native_event_returns=returns,created_widgets=len(self.widgets)-created_before,actual_interface_entries=len(self.interface_events)-events_before,
                        explicit_second_business_event=seed is not None,native_looping_sound_slots=sound_slots,actual_native_spawn_audio_slots=spawned_slots,
                        interface_payloads=[event[1] for event in self.interface_events[events_before:]],pre_remove=state,same_seed_widget=valid(seed) and widget == seed,
                        retained_fields_after_removal=actor.get_property("SpawnedWidget") == widget and actor.get_property("OptionalLocalController") == controller,
                        removed_widget_not_visible=not valid(widget) or not widget.call_function("IsInViewport"),
                        old_widget_visible_after_removal=valid(seed) and bool(seed.call_function("IsInViewport"))))
                    for owned in self.widgets[created_before:]:
                        if valid(owned): owned.call_function("RemoveFromParent")
                    actor.call_function("K2_EndGameplayCue")
        self.current = None
    def start_manager(self):
        self.manager_label = ("match","waiting")[self.manager_index]; self.manager_target = self.own()
        self.manager_target.add_actor_root_component(ue.find_class("SceneComponent"),"UEPNaturalCueWidget")
        self.manager_tag = self.classes[self.manager_label].get_cdo().get_property("GameplayCueTag")
        self.manager_params = self.params(self.controller.PlayerState); self.manager_started = []
        self.probe.call_function("Start",self.manager_target,self.manager_tag,self.manager_params); self.enter("manager")
    def manager(self):
        require(time.monotonic()-self.phase_started < 15., "real native Cue manager did not start widget")
        if not self.manager_started: return
        require(len(self.manager_started) == 1,"real Cue manager repeated looping start")
        actor = self.manager_started[0]; widget = self.collect(actor,None); require(valid(widget),"native manager did not create original widget")
        before = dict(policy.evidence(actor)); visible = bool(widget.call_function("IsInViewport")); selected_profile = str(ue.get_mixin_profile(actor))
        self.probe.call_function("Start",self.manager_target,self.manager_tag,self.manager_params)
        duplicate_guard = len(self.manager_started) == 1 and actor.get_property("SpawnedWidget") == widget
        sound_slots = len(actor.get_property("LoopingEffects").LoopingSounds); spawned_slots = len(actor.get_property("LoopingSpawnResults").AudioComponents)
        self.probe.call_function("Remove",self.manager_target,self.manager_tag,self.manager_params)
        after = policy.evidence(actor)
        self.report["manager_cases"].append(dict(**{"class":self.manager_label},selected_profile=selected_profile,
            actual_manager_start_entries=1,actual_manager_remove_entries=after["python_remove"]-before["python_remove"],bp_library_caller=True,
            native_target_has_no_asc=not valid(policy.lib("AbilitySystemBlueprintLibrary").call_function("GetAbilitySystemComponent",self.manager_target)),
            widget_added=visible,widget_removed=not widget.call_function("IsInViewport"),source_cached_reference_preserved=dead(actor) or actor.get_property("SpawnedWidget") == widget,
            borrowed_a_matrix_actor_returned_to_native_pool=actor in self.cue_actors,duplicate_add_respected_native_guard=duplicate_guard,
            native_looping_sound_slots=sound_slots,actual_native_spawn_audio_slots=spawned_slots))
        self.manager_index += 1
        if self.manager_index == 2: self.finish()
        else: self.start_manager()
    def cleanup(self):
        self.current = None
        for widget in self.widgets:
            if valid(widget): widget.call_function("RemoveFromParent")
        for actor in reversed(self.actors):
            if actor in self.cue_actors:
                if not dead(actor) and (not actor.get_property("bHidden") or valid(actor.call_function("GetOwner"))): actor.call_function("K2_EndGameplayCue")
            elif not dead(actor): actor.call_function("K2_DestroyActor")
        self.report["all_owned_widgets_removed"] = all(not valid(w) or not w.call_function("IsInViewport") for w in self.widgets)
        self.report["native_recycled_cue_actor_states"] = [dict(path=a.get_path_name(),hidden=bool(a.get_property("bHidden")),owner_none=not valid(a.call_function("GetOwner")),tick_disabled=not a.call_function("IsActorTickEnabled")) for a in self.cue_actors if not dead(a)]
        self.report["all_owned_regular_actors_destroyed"] = all(dead(a) for a in self.actors if a not in self.cue_actors)
        self.report["all_owned_cue_actors_recycled"] = len(self.report["native_recycled_cue_actor_states"]) == 42 and all(r["hidden"] and r["owner_none"] and r["tick_disabled"] for r in self.report["native_recycled_cue_actor_states"])
        self.report["player_array_restored"] = hasattr(self,"players_before") and set(self.game_state.get_property("PlayerArray")) == set(self.players_before)
        if hasattr(self,"original_interface"):
            self.report["widget_observer_restored"] = bool(ue.unregister_mixin(self.match_widget)) and self.match_widget.get_cdo().find_function("ConstructFromCueParams") == self.original_interface
        for name,source in self.base_sources.items(): ue.register_mixin_profile(self.base_cls,name,source)
        if self.base_sources:
            row, = [r for r in ue.get_registered_mixins() if r["target_class"] == self.base_cls]
            self.report["base_providers_restored"] = all(row["profiles"][name]["python_class"] is source for name,source in self.base_sources.items())
        if hasattr(self,"music_fields"):
            for name,value in self.music_fields.items(): self.music.set_property(name,value)
            self.report["music_dependency_fields_restored"] = all(self.music.get_property(name) == value for name,value in self.music_fields.items())
        if hasattr(self,"probe"): self.probe.remove_from_root(); self.report["probe_unrooted"] = not self.probe.is_rooted()
        self.report["health_unchanged"] = hasattr(self,"health_before") and self.healths() == self.health_before
    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 180.,"native Cue widget total timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "manager": self.manager()
            self.report["phase"] = self.phase; self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def finish(self,error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CUE_WIDGET_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CUE_WIDGET_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPCueWidgetResult=")),None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
