"""Observe an already registered Character class, without preload/CDO writes."""
import unreal_engine as ue
from .melee_character_default_control import CHARACTER
from .melee_replica_readiness import EarlyWatch


class LazyPawnLifecycleObservation:
    def __init__(self,root,peer,run):
        self.watch=EarlyWatch(root,peer,run);self.cls=None;self.original=None;self.observed=None;self.closed=False
        self.report=dict(class_path=CHARACTER,preloaded=False,cdo_written=False,installed=False,restored=False,event_files=[])
    def install(self,binding):
        self.cls=binding["target_class"];self.original=binding["profiles"]["Python"]["python_class"]
        parent=self.original;watch=self.watch
        begin=parent.__dict__["ReceiveBeginPlay"];construction=parent.__dict__.get("UserConstructionScript")
        def ReceiveBeginPlay(pawn): watch.birth(pawn);return begin(pawn)
        def UserConstructionScript(pawn):
            watch.constructed(pawn)
            if construction is not None: return construction(pawn)
            return pawn.call_mixin_original("UserConstructionScript")
        values={name:value for name,value in parent.__dict__.items() if callable(value)}
        values.update(ReceiveBeginPlay=ReceiveBeginPlay,UserConstructionScript=UserConstructionScript)
        self.observed=type("LazyObservedExistingCharacter",(),values)
        ue.register_mixin_profile(self.cls,"Python",self.observed)
        self.report["installed"]=True
    def poll(self):
        if self.closed: return
        values=[value for value in ue.get_registered_mixins() if value["target_class"].get_path_name()==CHARACTER]
        if self.cls is None:
            if not values: return
            binding,=values;self.install(binding)
        else:
            binding,=values
            if binding["profiles"]["Python"]["python_class"] is not self.observed: raise RuntimeError("lazy Character observation was overwritten")
        self.watch.poll();self.report["event_files"]=list(self.watch.files)
    def close(self):
        if self.closed: return
        self.closed=True
        try: self.watch.close()
        finally:
            if self.cls is not None: ue.register_mixin_profile(self.cls,"Python",self.original)
            self.report.update(restored=True,event_files=list(self.watch.files))
