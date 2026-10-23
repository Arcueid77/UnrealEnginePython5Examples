"""Read-only native replica bindings; never initialize, repair or write Health."""
import copy
import json
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid, ability_system


def path(value): return value.get_path_name() if valid(value) else None


def change_fingerprint(value):
    def stable(data):
        if isinstance(data,dict): return {key:stable(item) for key,item in data.items() if key not in ("world_seconds","actor_age_seconds")}
        if isinstance(data,list): return [stable(item) for item in data]
        return data
    return json.dumps(stable(value),sort_keys=True)


def asc_state(asc):
    if not valid(asc): return None
    attributes = []
    for value in asc.get_property("SpawnedAttributes"):
        if valid(value) and value.is_a(ue.find_class("LyraHealthSet")):
            health, maximum = value.get_property("Health"), value.get_property("MaxHealth")
            attributes.append(dict(object=path(value), health=float(health.CurrentValue), health_base=float(health.BaseValue),
                max_health=float(maximum.CurrentValue), max_health_base=float(maximum.BaseValue)))
    return dict(object=path(asc), owner=path(asc.get_property("OwnerActor")), avatar=path(asc.get_property("AvatarActor")), health_attributes=attributes)


def snapshot(pawn, health):
    state = pawn.get_property("PlayerState")
    extension = pawn.get_component_by_type(ue.find_class("LyraPawnExtensionComponent"))
    actor_asc = ability_system(pawn); health_asc = health.get_property("AbilitySystemComponent")
    state_asc = state.get_property("AbilitySystemComponent") if valid(state) else None
    features = pawn.call_function("GetComponentsByInterface", ue.find_class("GameFrameworkInitStateInterface"))
    feature_states = [dict(component=path(value), cls=path(value.get_class()), feature=str(value.call_function("GetFeatureName")),
        state=str(value.call_function("GetInitState").TagName)) for value in features]
    row=dict(actor=path(pawn), actor_class=path(pawn.get_class()), role=int(pawn.call_function("GetLocalRole")),
        character_profile_property=str(pawn.get_property("PythonMixinProfile")),
        destroying=bool(pawn.call_function("IsActorBeingDestroyed")), health=float(health.call_function("GetHealth")),
        hidden=bool(pawn.get_property("bHidden")), tear_off=bool(pawn.get_property("bTearOff")), life_span=float(pawn.call_function("GetLifeSpan")),
        controller=path(pawn.get_property("Controller")), input_component=path(pawn.get_property("InputComponent")),
        locally_controlled=bool(pawn.call_function("IsLocallyControlled")),
        lifecycle=copy.deepcopy(getattr(pawn,"_uep_character_lifecycle",None)),
        inventory_wait=copy.deepcopy(getattr(pawn,"_uep_character_inventory_wait",None)),
        inventory_ready=copy.deepcopy(getattr(pawn,"_uep_character_inventory_ready",None)),
        possessed=copy.deepcopy(getattr(pawn,"_uep_character_possessed",None)),
        max_health=float(health.call_function("GetMaxHealth")), death_state=int(health.call_function("GetDeathState")),
        health_set=path(health.get_property("HealthSet")), health_asc=asc_state(health_asc), actor_asc=asc_state(actor_asc),
        player_state=path(state), player_state_pawn=path(state.call_function("GetPawn")) if valid(state) else None,
        player_state_asc=asc_state(state_asc), extension=path(extension),
        extension_asc=path(extension.get_property("AbilitySystemComponent")) if valid(extension) else None,
        init_features=sorted(feature_states,key=lambda value:value["feature"]),
        pawn_data=path(extension.get_property("PawnData")) if valid(extension) else None,
        net_dormancy=int(pawn.get_property("NetDormancy")), always_relevant=bool(pawn.get_property("bAlwaysRelevant")),
        net_cull_distance_squared=float(pawn.get_property("NetCullDistanceSquared")))
    if "-UEPRequireNetworkIdentity" in sys.argv:
        from .network_identity import read
        row["network_identity"]=read(pawn)
        row["player_state_network_identity"]=read(state)
    return row


def view_state(controller):
    camera = controller.get_property("PlayerCameraManager")
    location = camera.call_function("GetCameraLocation") if valid(camera) else None
    eye, _ = controller.call_function("GetPlayerViewPoint")
    return dict(view_target=path(controller.call_function("GetViewTarget")), view_point=[float(getattr(eye,name)) for name in ("x","y","z")],
        camera_location=[float(getattr(location,name)) for name in ("x","y","z")] if location is not None else None)


class EarlyWatch:
    """Bounded change-only snapshots before local combat readiness, no repair."""
    def __init__(self, root, peer, run):
        self.root,self.peer,self.run=root,peer,run; self.scopes={}; self.closed=False
        self.started=time.monotonic();self.last={};self.files=[];self.watched=set()
        self.native_stack_capture=None
        if '-UEPReplicaNativeConstructionStacks' in sys.argv:
            from .native_construction_stack import capture
            self.native_stack_capture=capture
    def native_stack(self,row):
        if self.native_stack_capture is not None:
            try:row['native_callstack']=self.native_stack_capture()
            except Exception:row['native_callstack_error']=traceback.format_exc()
    def publish(self, kind, data):
        if self.closed: return
        if len(self.files) >= 2048: raise RuntimeError("bounded native early-readiness history exhausted")
        name=self.peer+"-early-readiness-"+str(len(self.files))+".json"
        atomic_write(self.root/name,dict(run_id=self.run,kind=kind,elapsed=time.monotonic()-self.started,data=data));self.files.append(name)
    def ended(self, actor_path, reason, actor=None):
        # Detach while the Actor's delegate property still exists. Keeping one
        # process-wide scope retains dead wrappers until native class teardown.
        scope=self.scopes.pop(actor_path,None)
        if scope is not None: scope.close()
        row=dict(actor=actor_path,reason=int(reason),python_stack=traceback.format_stack(limit=16))
        self.native_stack(row)
        if "-UEPRequireNetworkIdentity" in sys.argv:
            from .network_identity import read
            row["network_identity"]=read(actor)
        self.publish("native-end-play",row)
    def destroyed(self,actor_path,actor=None):
        scope=self.scopes.pop(actor_path,None)
        if scope is not None: scope.close()
        row=dict(actor=actor_path,python_stack=traceback.format_stack(limit=16))
        self.native_stack(row)
        if "-UEPRequireNetworkIdentity" in sys.argv:
            from .network_identity import read
            row["network_identity"]=read(actor)
        self.publish("native-destroyed-before-end-play",row)
    def watch(self, pawn, actor_path, construction=False):
        scope=SubscriptionScope()
        scope.bind_event(pawn,"OnEndPlay",lambda actor,reason,key=actor_path:self.ended(key,reason,actor))
        if construction: scope.bind_event(pawn,"OnDestroyed",lambda actor,key=actor_path:self.destroyed(key,actor))
        self.scopes[actor_path]=scope;self.watched.add(actor_path)
    def constructed(self,pawn):
        if self.closed: return
        actor_path=path(pawn)
        if actor_path not in self.watched: self.watch(pawn,actor_path,construction=True)
        row=dict(actor=actor_path,actor_class=path(pawn.get_class()),role=int(pawn.call_function("GetLocalRole")),python_stack=traceback.format_stack(limit=16))
        self.native_stack(row)
        if "-UEPRequireNetworkIdentity" in sys.argv:
            from .network_identity import read
            row["network_identity"]=read(pawn)
        self.publish("native-construction",row)
    def birth(self, pawn):
        if self.closed: return
        actor_path=path(pawn)
        if actor_path not in self.watched: self.watch(pawn,actor_path)
        health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        self.publish("native-begin-play",snapshot(pawn,health) if valid(health) else dict(actor=actor_path))
    def poll(self):
        if self.closed: return
        statics=ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3,5) or "L_Expanse" not in world.get_name(): continue
            actors,=statics.call_function("GetAllActorsOfClass",world,ue.find_class("LyraCharacter"))
            for pawn in actors:
                health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
                if not valid(health): continue
                actor_path=path(pawn)
                if actor_path not in self.watched:
                    self.watch(pawn,actor_path)
                row=snapshot(pawn,health);fingerprint=change_fingerprint(row)
                if self.last.get(actor_path)!=fingerprint:
                    self.last[actor_path]=fingerprint;self.publish("native-binding-change",row)
    def close(self):
        if self.closed: return
        self.closed=True
        scopes,self.scopes=self.scopes,{}
        errors=[]
        for scope in scopes.values():
            try: scope.close()
            except Exception as error: errors.append(error)
        if errors: raise RuntimeError("early-readiness listener cleanup failed") from errors[0]
