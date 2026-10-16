"""Actual second BP Interface caller, native object references and owned cleanup."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from uep_lyra_world.effect_pad_mixin import valid
from .inventory_clear_mixin import inventory_state
from . import emote_audio_mixin as policy
from .emote_audio_contract import CLASS, PLAN, validate

PROBE = "/Game/UEPValidation/BP_CharacterAudioInterfaceProbe.BP_CharacterAudioInterfaceProbe_C"


def path(value): return value.get_path_name() if valid(value) else None
def delta(actor, before): return {key: value-before[key] for key, value in policy.evidence(actor).items()}


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result)
        self.actors, self.saved, self.components = [], [], []
        self.cleaned = False
        self.report.update(cases=[], mixed_instances=[], native_components_created=0, native_components_destroyed=0,
            second_bp_interface_message_caller=True, hardware_sound_verified=False, audio_playback_called_by_fixture=False,
            animation_notify_modified=False, character_subclass_created=False, full_acceptance=False, whole_character_migrated=False)

    def read(self, actor):
        value, = self.probe.call_function("Read", actor)
        return value

    def write_component(self, actor, component): self.probe.call_function("Write", actor, component)

    def begin(self):
        self.exercise(); self.finish()

    def exercise(self):
        self.probe = ue.load_class(PROBE).get_cdo()
        actors, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.load_class(CLASS))
        target_id = getattr(self, "secondary_player_id", None)
        other = next((actor for actor in actors if valid(actor) and actor != self.pawn and actor.get_class().get_path_name() == CLASS and (
            target_id is None or (valid(actor.get_property("PlayerState")) and int(actor.get_property("PlayerState").PlayerId) == target_id))), None)
        require(valid(other), "real second existing same-class Character unavailable")
        self.actors = [self.pawn, other]
        self.saved = [(str(ue.get_mixin_profile(actor)), actor.get_property(policy.FIELD)) for actor in self.actors]
        self.inventory_before = inventory_state(self.controller)
        self.cdo = self.pawn.get_class().get_cdo()
        self.cdo_before = (str(ue.get_mixin_profile(self.cdo)), path(self.cdo.get_property(policy.FIELD)))
        self.report.update(primary_actor=path(self.pawn), secondary_actor=path(other), retained_character_class=self.pawn.get_class().get_path_name(),
            two_native_same_class_actors=all(actor.get_class().get_path_name() == CLASS for actor in self.actors),
            primary_player_id=int(self.controller.PlayerState.PlayerId),
            secondary_player_id=int(other.get_property("PlayerState").PlayerId),
            primary_role=int(self.pawn.call_function("GetLocalRole")), secondary_role=int(other.call_function("GetLocalRole")))
        for index, actor in enumerate(self.actors):
            component = ue.new_object(ue.find_class("AudioComponent"), actor, "UEPInterfaceAudio"+str(index))
            require(valid(component), "native AudioComponent construction failed")
            self.components.append(component); self.report["native_components_created"] += 1
        self.report["native_component_paths"] = [path(value) for value in self.components]
        for name, writer, reader, kind in PLAN:
            value = None if kind == "null" else self.components[0] if kind == "a" else self.components[1]
            before = dict(policy.evidence(self.pawn))
            ue.set_mixin_profile(self.pawn, writer); self.write_component(self.pawn, value)
            actual_field = self.pawn.get_property(policy.FIELD)
            ue.set_mixin_profile(self.pawn, reader); result = self.read(self.pawn)
            self.report["cases"].append(dict(name=name, writer=writer, reader=reader, kind=kind, field_after_write=path(actual_field),
                bp_read_result=path(result), reference_identity_matches=result == value and actual_field == value,
                native_actor_type_preserved=self.pawn.get_class().get_path_name() == CLASS, counters=delta(self.pawn, before)))
        for primary, secondary in (("Python", "BlueprintFallback"), ("BlueprintFallback", "Python")):
            before = [dict(policy.evidence(actor)) for actor in self.actors]
            for actor, component, profile in zip(self.actors, self.components, (primary, secondary)):
                ue.set_mixin_profile(actor, profile); self.write_component(actor, component)
            first, second = self.read(self.pawn), self.read(other)
            self.report["mixed_instances"].append(dict(primary_profile=primary, secondary_profile=secondary, primary_result=path(first), secondary_result=path(second),
                primary_counters=delta(self.pawn, before[0]), secondary_counters=delta(other, before[1]),
                both_native_types_preserved=all(actor.get_class().get_path_name() == CLASS for actor in self.actors)))
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("CollectGarbage")
        self.report["native_gc"] = dict(native_collect_garbage_called=True, both_components_valid=all(valid(value) for value in self.components),
            primary_result=path(self.read(self.pawn)), secondary_result=path(self.read(other)))
        self.report["non_targets"] = []
        for name, target in (("null", None), ("non-interface-controller", self.controller)):
            before = [dict(policy.evidence(actor)) for actor in self.actors]
            self.write_component(target, self.components[0]); result = self.read(target)
            self.report["non_targets"].append(dict(target=name, result_is_null=result is None,
                character_counters_unchanged=all(policy.evidence(actor) == counts for actor, counts in zip(self.actors, before))))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 150, "native Character audio readiness timeout")
            self.ready(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write(); (ue.log_error if error else ue.log)("UEP_CHARACTER_AUDIO_"+("FAILED "+error if error else "DIFFERENTIAL_PASSED"))
        ue.request_exit()

    def cleanup(self):
        if self.cleaned: return
        self.cleaned = True
        for actor, (profile, component) in zip(self.actors, self.saved):
            self.write_component(actor, component); ue.set_mixin_profile(actor, profile)
        self.report["original_fields_restored"] = len(self.saved) == 2 and all(actor.get_property(policy.FIELD) == saved[1] for actor, saved in zip(self.actors, self.saved))
        self.report["original_profiles_restored"] = len(self.saved) == 2 and all(str(ue.get_mixin_profile(actor)) == saved[0] for actor, saved in zip(self.actors, self.saved))
        for component, actor in zip(self.components, self.actors):
            if valid(component): component.call_function("K2_DestroyComponent", actor)
            require(not valid(component), "owned native AudioComponent not destroyed")
            self.report["native_components_destroyed"] += 1
        self.report["inventory_unchanged"] = inventory_state(self.controller) == self.inventory_before
        self.report["cdo_unchanged"] = (str(ue.get_mixin_profile(self.cdo)), path(self.cdo.get_property(policy.FIELD))) == self.cdo_before

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_AUDIO_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterAudioResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
