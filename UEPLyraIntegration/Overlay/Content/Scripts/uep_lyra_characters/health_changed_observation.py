"""Test-only real GAS producers and independently owned native multicast observers."""
import copy
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_abilities.death_damage import DAMAGE
from unreal_engine.structs import GameplayTag
from .outline_validation import path
from .inventory_clear_mixin import inventory_state
from . import health_changed_mixin as policy
from .health_changed_contract import require


def health_component(actor): return actor.get_component_by_type(ue.find_class("LyraHealthComponent"))
def health(actor): return float(health_component(actor).call_function("GetHealth"))
def vector(value): return [float(value.x), float(value.y), float(value.z)]


def apply(source, target, amount):
    context = source.call_function("MakeEffectContext")
    library = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
    instigator = library.call_function("EffectContextGetOriginalInstigatorActor", context)
    effect = DAMAGE if amount >= 0 else "/Game/GameplayEffects/Heal/GE_Heal_SetByCaller.GE_Heal_SetByCaller_C"
    spec = source.call_function("MakeOutgoingSpec", ue.load_class(effect), 1., context)
    spec = library.call_function("AssignTagSetByCallerMagnitude", spec, GameplayTag(TagName="SetByCaller.Damage" if amount >= 0 else "SetByCaller.Heal"), abs(float(amount)))
    source.call_function("BP_ApplyGameplayEffectSpecToTarget", spec, ability_system(target))
    return path(instigator)


class OwnedAI:
    """Native bot creation includes GenericPlayerInitialization and team assignment."""
    def __init__(self, world):
        self.controller = self.pawn = self.state = self.perception = self.creator = self.template = None
        try:
            game_state = ue.find_class("GameplayStatics").get_cdo().call_function("GetGameState", world)
            self.template = game_state.get_component_by_type(ue.find_class("LyraBotCreationComponent"))
            require(valid(self.template), "original Experience has no native bot producer")
            self.original_bots = [path(value) for value in self.template.get_property("SpawnedBotList")]
            # A fresh unregistered component uses native SpawnOneBot but never
            # runs BeginPlay/ServerCreateBots or changes the original bot list.
            self.creator = ue.new_object(self.template.get_class(), game_state, "UEPHealthBotProducer")
            require(not self.creator.component_is_registered() and not self.creator.get_property("SpawnedBotList"), "fixture bot producer is not fresh/unregistered")
            self.creator.call_function("SpawnOneBot")
            controllers = list(self.creator.get_property("SpawnedBotList"))
            require(len(controllers) == 1, "native fixture producer did not create exactly one owned bot")
            self.controller = controllers[0]
            self.state = self.controller.get_property("PlayerState")
            require(valid(self.state), "native Lyra bot did not initialize its own PlayerState")
            mode = ue.find_class("GameplayStatics").get_cdo().call_function("GetGameMode", world)
            mode.call_function("ChangeName", self.controller, "UEPHealthSenseFixture", False)
            self.pawn = self.controller.get_controlled_pawn()
            require(valid(self.pawn), "native Lyra RestartPlayer did not create the owned AI Pawn")
            brain = self.controller.get_property("BrainComponent")
            if valid(brain) and brain.call_function("IsRunning"): brain.call_function("StopLogic", "UEP health native bot isolation")
            self.controller.call_function("StopMovement")
            self.perception = self.controller.get_property("PerceptionComponent")
            require(valid(self.perception), "original native bot has no configured perception component")
        except Exception:
            self.close(); raise

    def ready(self):
        return valid(self.pawn) and valid(ability_system(self.pawn)) and health(self.pawn) > 20. and not health_component(self.pawn).call_function("IsDeadOrDying") and not ability_system(self.pawn).call_function("HasMatchingGameplayTag", GameplayTag(TagName="Gameplay.DamageImmunity"))

    def close(self):
        errors = []
        for value in (self.pawn, self.controller, self.state):
            try:
                # Controller.K2_DestroyActor deliberately does nothing. Existing
                # UEP actor_destroy calls native AActor::Destroy directly.
                if valid(value): value.actor_destroy()
            except Exception: errors.append(traceback.format_exc())
        producer_list_unchanged = self.template is not None and [path(value) for value in self.template.get_property("SpawnedBotList")] == self.original_bots
        try:
            if valid(self.creator): self.creator.call_function("K2_DestroyComponent", self.creator)
        except Exception: errors.append(traceback.format_exc())
        if errors: raise RuntimeError("owned native AI destruction failed: "+"\n".join(errors))
        return dict(owned_pawn_controller_playerstate_producer_destroyed=all(value is not None and not valid(value) for value in (self.pawn, self.controller, self.state, self.creator)),
            original_bot_producer_list_preserved=producer_list_unchanged)


class Context:
    def __init__(self, actors, controllers, owned=None):
        self.actors, self.controllers, self.owned, self.closed = actors, controllers, owned, False
        self.original_health = {key: health(actor) for key, actor in actors.items()}
        self.original_profiles = {key: str(ue.get_mixin_profile(actor)) for key, actor in actors.items()}
        self.startup = {key: copy.deepcopy(policy.evidence(actor)) for key, actor in actors.items()}
        self.inventory = {key: inventory_state(controller) for key, controller in controllers.items()}
        self.cdo = next(iter(actors.values())).get_class().get_cdo(); self.cdo_profile = str(ue.get_mixin_profile(self.cdo))
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", next(iter(actors.values())).get_world())
        self.net_mode = str(bridge.call_function("CaptureSnapshot").NetMode)
        self.scope, self.bindings, self.raw, self.stimuli, self.errors = SubscriptionScope(), 0, {key: [] for key in actors}, [], []
        try:
            for key, actor in actors.items():
                component, actor_path = health_component(actor), path(actor)
                def changed(source, old, new, instigator, key=key, expected=path(component), owner=actor_path):
                    try:
                        self.raw[key].append(dict(component_matches=path(source) == expected,
                            owner_matches=valid(source) and path(source.get_owner()) == owner,
                            old=float(old), new=float(new), instigator=path(instigator)))
                    except Exception: self.errors.append(traceback.format_exc())
                self.scope.bind_event(component, "OnHealthChanged", changed); self.bindings += 1
            if owned is not None:
                def sensed(actor, stimulus):
                    try:
                        sense = ue.find_class("AIPerceptionSystem").get_cdo().call_function("GetSenseClassForStimulus", owned.pawn.get_world(), stimulus)
                        self.stimuli.append(dict(source=path(actor), strength=float(stimulus.Strength), location=vector(stimulus.StimulusLocation),
                            hit_location=vector(stimulus.ReceiverLocation), tag=str(stimulus.Tag), sense=path(sense)))
                    except Exception: self.errors.append(traceback.format_exc())
                self.scope.bind_event(owned.perception, "OnTargetPerceptionUpdated", sensed); self.bindings += 1
        except Exception:
            self.scope.close(); raise

    def target(self, name): return "AI" if name.startswith("ai-") else ("B0" if name.startswith("player-B0") else "A")
    def amount(self, name): return -3. if name == "ai-foreign-healing" else 5.

    def prepare(self, name):
        require(self.owned is not None, "only authority may produce fixture health changes")
        self.owned.perception.call_function("ForgetAll")
        if name == "ai-foreign-healing": apply(ability_system(self.actors["AI"]), self.actors["AI"], 5.)

    def prepared(self, name):
        return all(abs(health(actor)-(self.original_health[key]-(5. if name == "ai-foreign-healing" and key == "AI" else 0.))) < .01 for key, actor in self.actors.items())

    def arm(self, name, profile):
        self.name, self.profile, self.target_key = name, profile, self.target(name)
        self.profiles = {key: (profile if key == self.target_key else ("Python" if profile == "BlueprintFallback" else "BlueprintFallback")) for key in self.actors}
        for key, actor in self.actors.items(): ue.set_mixin_profile(actor, self.profiles[key])
        self.before = {key: copy.deepcopy(policy.evidence(actor)) for key, actor in self.actors.items()}
        self.raw_before, self.stimuli_before = {key: len(value) for key, value in self.raw.items()}, len(self.stimuli)

    def produce(self):
        target = self.actors[self.target_key]
        source_pawn = target
        if not self.name.endswith("self"):
            statics = ue.find_class("LyraTeamStatics").get_cdo()
            _, target_team, _ = statics.call_function("FindTeamFromObject", target, False)
            candidates, = ue.find_class("GameplayStatics").get_cdo().call_function("GetAllActorsOfClass", target.get_world(), target.get_class())
            candidates = sorted(candidates, key=path)
            enemies = [actor for actor in candidates if valid(actor) and valid(ability_system(actor)) and
                statics.call_function("FindTeamFromObject", actor, False)[1] not in (-1, target_team)]
            require(target_team != -1 and enemies, "native health fixture requires an actual opposing-team source")
            source_pawn = enemies[0]
        source = ability_system(source_pawn)
        self.source_instigator = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("EffectContextGetOriginalInstigatorActor", source.call_function("MakeEffectContext"))
        self.source_pawn = self.source_instigator.call_function("GetPawn") if valid(self.source_instigator) and self.source_instigator.is_a(ue.find_class("PlayerState")) else None
        self.source_location = vector(self.source_pawn.call_function("K2_GetActorLocation")) if valid(self.source_pawn) else None
        self.producer_before = health(target); apply(source, target, self.amount(self.name))
        require(abs(health(target)-(self.producer_before-self.amount(self.name))) < .01, "real native GAS health mutation differs")

    def seen(self):
        require(not self.errors, "independent health/perception observer failed: "+str(self.errors))
        count = len(self.raw[self.target_key])-self.raw_before[self.target_key]
        require(count <= 1, "duplicate native health delegates before restore")
        amount = self.amount(self.name)
        expected = self.original_health[self.target_key]-(5. if self.name == "ai-foreign-healing" else 0.)-amount
        return count == 1 and abs(health(self.actors[self.target_key])-expected) < .01

    def row(self):
        observations = {}
        for key, actor in self.actors.items():
            stats = policy.evidence(actor)
            observations[key] = dict(profile=str(ue.get_mixin_profile(actor)), native_role=int(actor.call_function("GetLocalRole")),
                authority=bool(actor.call_function("HasAuthority")), health=health(actor), original_health=self.original_health[key],
                counters={name: value-self.before[key][name] for name, value in stats.items() if name != "last_report"},
                last_report=copy.deepcopy(stats["last_report"]), delegates=copy.deepcopy(self.raw[key][self.raw_before[key]:]))
        stimuli = copy.deepcopy(self.stimuli[self.stimuli_before:])
        perceived, memory = False, None
        if self.owned is not None and valid(self.source_pawn):
            perceived, info = self.owned.perception.call_function("GetActorsPerception", self.source_pawn)
            if perceived:
                sensed = [value for value in info.LastSensedStimuli if ue.find_class("AIPerceptionSystem").get_cdo().call_function("GetSenseClassForStimulus", self.owned.pawn.get_world(), value) == ue.find_class("AISense_Damage")]
                require(len(sensed) == 1 and len(stimuli) == 1 and abs(float(sensed[0].Strength)-stimuli[0]["strength"]) < .01,
                    "native AI perception memory differs from independent multicast")
                value = sensed[0]
                memory = dict(source=path(info.Target), strength=float(value.Strength), location=vector(value.StimulusLocation),
                    hit_location=vector(value.ReceiverLocation), tag=str(value.Tag), sense="/Script/AIModule.AISense_Damage")
        return dict(name=self.name, profile=self.profile, target=self.target_key, native_gas_producer_called=self.owned is not None,
            actors=observations, native_stimuli=stimuli, native_ai_perception_memory=bool(perceived),
            native_ai_perception_memory_stimulus=memory,
            native_source_instigator=path(self.source_instigator) if self.owned is not None else None,
            source_instigator_is_playerstate=bool(valid(self.source_instigator) and self.source_instigator.is_a(ue.find_class("PlayerState"))) if self.owned is not None else False,
            source_pawn=path(self.source_pawn) if self.owned is not None else None,
            source_location=self.source_location if self.owned is not None else None)

    def restore(self):
        require(self.owned is not None, "client cannot restore replicated health")
        for key, actor in self.actors.items():
            change=health(actor)-self.original_health[key]
            if abs(change) > .01: apply(ability_system(actor), actor, change)

    def restored(self): return all(abs(health(actor)-self.original_health[key]) < .01 for key, actor in self.actors.items())

    def cleanup(self):
        if self.closed: return self.cleanup_report
        errors = []
        for key, actor in self.actors.items():
            try: ue.set_mixin_profile(actor, self.original_profiles[key])
            except Exception: errors.append(traceback.format_exc())
        try: self.scope.close()
        except Exception: errors.append(traceback.format_exc())
        self.cleanup_report = dict(health_restored=self.restored(), original_profiles_restored=all(str(ue.get_mixin_profile(actor)) == self.original_profiles[key] for key, actor in self.actors.items()),
            original_inventory_restored=all(inventory_state(controller) == self.inventory[key] for key, controller in self.controllers.items()),
            cdo_profile_restored=str(ue.get_mixin_profile(self.cdo)) == self.cdo_profile,
            observer=dict(created=1, closed=int(self.scope.closed), bindings_created=self.bindings, bindings_closed=self.bindings if self.scope.closed else 0,
                active=self.scope.count, health_deliveries=sum(len(value) for value in self.raw.values()), sense_deliveries=len(self.stimuli), errors=list(self.errors)))
        self.closed = True
        if errors: raise RuntimeError("native health observer cleanup failed: "+"\n".join(errors))
        return self.cleanup_report
