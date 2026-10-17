"""Explicit diagnostic CDO-profile variant in one disposable game process."""
import unreal_engine as ue

CHARACTER="/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C"
PROPERTY="PythonMixinProfile"
GROUPS=dict(inventory=["AddInitialInventory"],possession=["ReceivePossessed","PythonExperienceReady","PythonInventoryWaitResume"],
    team=["ListenForTeam","PythonObservedTeamChanged","OnTeamOrCosmeticsChanged"],
    possession_factory=["ReceivePossessed"],experience=["PythonExperienceReady","PythonInventoryWaitResume"],
    experience_entry=["PythonExperienceReady"],experience_resume=["PythonInventoryWaitResume"])


def original_methods(python, blueprint, subset):
    names=sorted(name for name in set(python)&set(blueprint) if not name.startswith("__") and callable(python[name]) and callable(blueprint[name]))
    if subset in GROUPS:
        selected=GROUPS[subset]
        if any(name not in names for name in selected): raise ValueError("explicit diagnostic group is not supported by both profiles")
        return list(selected)
    middle=(len(names)+1)//2
    return names[:middle] if subset=="first-half" else names[middle:]


class CharacterDefaultControl:
    def __init__(self, profile, original_begin_play=False, original_subset=None):
        if profile not in ("Python","BlueprintFallback"): raise ValueError("explicit diagnostic Character profile required")
        if original_subset not in (None,"first-half","second-half","refresh-python","clone-python",*GROUPS): raise ValueError("unknown method-isolation subset")
        if (original_begin_play or original_subset) and profile != "Python": raise ValueError("method-isolation control requires matched Python startup")
        if original_begin_play and original_subset: raise ValueError("choose one method-isolation treatment")
        self.profile=profile;self.cdo=ue.load_class(CHARACTER).get_cdo();self.before=str(self.cdo.get_property(PROPERTY));self.closed=False
        self.expected_class=None;selected=[]
        if original_begin_play or original_subset:
            from uep_lyra_characters.death_started_mixin import LyraCharacterDeathStartedPythonProfile as Python, LyraCharacterDeathStartedBlueprintFallbackProfile as Blueprint
            values={name:value for name,value in Python.__dict__.items() if callable(value)}
            selected=["ReceiveBeginPlay"] if original_begin_play else original_methods(Python.__dict__,Blueprint.__dict__,original_subset) if original_subset in ("first-half","second-half",*GROUPS) else []
            for name in selected: values[name]=Blueprint.__dict__[name]
            self.original_python_class=Python
            self.expected_class=Python if original_subset=="refresh-python" else type("DiagnosticCharacterOriginalMethods",(),values)
            ue.register_mixin_profile(ue.load_class(CHARACTER),"Python",self.expected_class)
        self.cdo.set_property(PROPERTY,profile)
        if str(self.cdo.call_function("GetPythonMixinProfile")) != profile: raise RuntimeError("diagnostic Character CDO provider did not select requested profile")
        self.report=dict(profile=profile,original=self.before,class_path=CHARACTER,preloaded_before_validation=True,
            runtime_cdo_only=True,asset_saved=False,health_written=False,restored=False,
            original_methods=selected,original_subset=original_subset,active_handler_class=None)
    def observe_registration(self):
        if self.closed: return
        cls=ue.load_class(CHARACTER)
        binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==cls]
        actual=binding["profiles"]["Python"]["python_class"]
        self.report["active_handler_class"]=actual.__module__+"."+actual.__name__
        if self.expected_class is not None and actual is not self.expected_class: raise RuntimeError("diagnostic Character method treatment was overwritten")
    def observe_births(self, watcher):
        if self.profile != "Python": return
        cls=ue.load_class(CHARACTER)
        bindings=[value for value in ue.get_registered_mixins() if value["target_class"]==cls]
        if bindings:
            binding,=bindings
            parent=binding["profiles"]["Python"]["python_class"]
        elif self.expected_class is not None: parent=self.expected_class
        else:
            # Startup can be inside UObject loading: registrations are queued
            # and are deliberately absent from the published native registry.
            from uep_lyra_characters.death_started_mixin import LyraCharacterDeathStartedPythonProfile
            parent=LyraCharacterDeathStartedPythonProfile
        if self.expected_class is not None and parent is not self.expected_class: raise RuntimeError("diagnostic Character treatment changed before birth observation")
        if self.expected_class is None: self.original_python_class=parent
        begin=parent.__dict__["ReceiveBeginPlay"]
        def ReceiveBeginPlay(pawn):
            watcher.birth(pawn)
            return begin(pawn)
        values={name:value for name,value in parent.__dict__.items() if callable(value)}
        values["ReceiveBeginPlay"]=ReceiveBeginPlay
        self.expected_class=type("DiagnosticCharacterBirthObservation",(),values)
        ue.register_mixin_profile(cls,"Python",self.expected_class)
        self.report["native_begin_play_observer"]=True
    def restore(self):
        if not self.closed:
            if self.expected_class is not None: ue.register_mixin_profile(ue.load_class(CHARACTER),"Python",self.original_python_class)
            self.cdo.set_property(PROPERTY,self.before);self.closed=True
            self.report["restored"] = str(self.cdo.get_property(PROPERTY)) == self.before
        return self.report["restored"]
