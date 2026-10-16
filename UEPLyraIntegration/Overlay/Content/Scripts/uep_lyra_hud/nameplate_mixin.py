"""Nameplate business on the retained BP class; native indicators stay native.

Init-state dynamic delegates use two typed VM transport functions. Those
functions contain no visibility/team/health policy. No new Tick or pool sampler
is needed: native IndicatorWidget Bind/Unbind owns this widget's binding epoch.
"""
import copy
import unreal_engine as ue
from unreal_engine.structs import SlateBrush
from uep_runtime import SubscriptionScope
from .weapon_observer import valid
from .nameplate_refs import optional_ref

CLASS = "/Game/UI/Indicators/W_Nameplate.W_Nameplate_C"
INIT_BIND = "UEPRegisterNameplateInitState"
INIT_UNBIND = "UEPUnregisterNameplateInitState"
ORIGINAL_HEALTH_CLEANUP = "UEPRemoveOriginalNameplateHealthBindings"
ORIGINAL_TEAM_PROXY = "UEPOriginalNameplateTeamProxy"
RESUME = "UEPResumeNameplateObservation"
_active = {}
# Empty during normal gameplay. Native differential probes may observe an
# actual Bind before either side registers its immediate init-state callback.
# They must never mutate/rebind the production object or registry here.
_validation_bind_observers = []
_validation_release_observers = []
_stats = {"binds": 0, "unbinds": 0, "init_callbacks": 0, "health_callbacks": 0,
          "death_callbacks": 0, "team_callbacks": 0, "scopes_created": 0,
          "scopes_closed": 0, "team_proxies_created": 0, "team_proxies_cancelled": 0,
          "init_bound": 0, "init_unbound": 0, "init_owner_released": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()))


def release_validation_pair(widget):
    # Only opt-in probes install observers. Release their rooted BP comparator
    # in the same native Unbind/Destruct epoch, not on a later polling tick.
    for observer in tuple(_validation_release_observers):
        observer(widget)


def health_for(pawn):
    return ue.find_class("LyraHealthComponent").get_cdo().call_function("FindHealthComponent", pawn)


def extension_for(pawn):
    return ue.find_class("LyraPawnExtensionComponent").get_cdo().call_function("FindPawnExtensionComponent", pawn)


def subsystem(context):
    return ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
        "GetWorldSubsystem", context, ue.find_class("LyraTeamSubsystem"))


def compare_teams(context, first, second):
    # The reflected overload returns the enum plus two out team IDs. The
    # non-reflected C++ convenience overload is not available to ProcessEvent.
    comparison, _first_team, _second_team = subsystem(context).call_function("CompareTeams", first, second)
    return int(comparison)


def material(path):
    return ue.load_object(ue.find_class("MaterialInterface"), path)


def replace_resource(image, resource):
    # Match the original MakeSlateBrush, including its deliberate preservation
    # of designer layout/tint/outline. Do not replace the entire designer brush
    # with SetBrushFromMaterial's defaults.
    old = image.Brush
    image.call_function("SetBrush", SlateBrush(
        TintColor=old.TintColor, DrawAs=old.DrawAs, Tiling=old.Tiling,
        Mirroring=old.Mirroring, ImageSize=old.ImageSize, Margin=old.Margin,
        ResourceObject=resource, OutlineSettings=old.OutlineSettings))


def close_scope(scope):
    if scope is not None:
        scope.close()
        _stats["scopes_closed"] += 1


def unregister_init_state(widget, extension):
    if not valid(extension):
        return False
    owner = extension.call_function("GetOwner")
    if not valid(owner):
        return False
    manager = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
        "GetGameInstanceSubsystem", owner, ue.find_class("GameFrameworkComponentManager"))
    if not valid(manager):
        # The native GameInstance subsystem has already gone away. Calling
        # its interface helper now would ensure in GetForActor; there is no
        # live manager through which this weak UObject delegate can deliver.
        return False
    widget.call_function(INIT_UNBIND, extension)
    return True


def close(widget):
    # Disarm before any native cancellation/unregister can reenter.
    extension, health_scope, team_scope, proxy = (widget._uep_np_extension, widget._uep_np_health_scope,
                                                 widget._uep_np_team_scope, widget._uep_np_team_proxy)
    widget._uep_np_live = False
    widget._uep_np_extension = widget._uep_np_health_scope = widget._uep_np_health = None
    widget._uep_np_team_scope = widget._uep_np_team_proxy = None
    _active.pop(id(widget), None)
    errors = []
    if extension is not None:
        try:
            kind = "init_unbound" if unregister_init_state(widget, extension) else "init_owner_released"
            _stats[kind] += 1
        except Exception as error:
            errors.append(error)
    for scope in (health_scope, team_scope):
        try:
            close_scope(scope)
        except Exception as error:
            errors.append(error)
    if valid(proxy):
        try:
            proxy.call_function("Cancel")
            _stats["team_proxies_cancelled"] += 1
        except Exception as error:
            errors.append(error)
    if errors:
        _stats["errors"].extend(str(error) for error in errors)
        raise RuntimeError("nameplate owned binding cleanup failed") from errors[0]


def observe_team(widget):
    # Every original InitializeNameplate creates/activates an observation and
    # receives its immediate team event. Replace only our own previous one;
    # deduplicating the activation would lose that authored refresh.
    old_scope, old_proxy = widget._uep_np_team_scope, widget._uep_np_team_proxy
    widget._uep_np_team_scope = widget._uep_np_team_proxy = None
    try:
        close_scope(old_scope)
    finally:
        if valid(old_proxy):
            old_proxy.call_function("Cancel")
            _stats["team_proxies_cancelled"] += 1
    proxy = ue.find_class("AsyncAction_ObserveTeam").get_cdo().call_function("ObserveTeam", widget.Pawn)
    if not valid(proxy):
        return  # Original async node has no callback for a non-team agent.
    scope = SubscriptionScope()
    widget._uep_np_team_scope, widget._uep_np_team_proxy = scope, proxy
    _stats["scopes_created"] += 1
    _stats["team_proxies_created"] += 1
    try:
        scope.bind_event(proxy, "OnTeamChanged", lambda team_set, team_id: team_changed(widget, team_set, team_id))
        proxy.call_function("Activate")
    except Exception:
        close(widget)
        raise


def team_changed(widget, team_set, team_id):
    if not widget._uep_np_live:
        return
    _stats["team_callbacks"] += 1
    widget._uep_np_team_callbacks += 1
    if team_set:
        widget.set_property("TeamId", int(team_id))
        widget.call_function("SetTeamVisuals")
    # Original callback does NOT recompute visibility here.


def observe_health(widget):
    health = health_for(widget.Pawn)
    if not valid(health):
        return
    if health != widget._uep_np_health:
        close_scope(widget._uep_np_health_scope)
        widget._uep_np_health_scope = None
        widget._uep_np_health = health
        scope = SubscriptionScope()
        widget._uep_np_health_scope = scope
        _stats["scopes_created"] += 1
        try:
            scope.bind_event(health, "OnHealthChanged", lambda component, old, new, instigator:
                             widget.call_function("Health Changed", component, old, new, instigator))
            scope.bind_event(health, "OnDeathStarted", lambda actor: widget.call_function("DeathStarted", actor))
        except Exception:
            close(widget)
            raise
    widget.call_function("SetHealthBarPercent", health.call_function("GetHealthNormalized"))


def close_original(widget):
    proxy = optional_ref(widget, ORIGINAL_TEAM_PROXY)
    setattr(widget, ORIGINAL_TEAM_PROXY, None)
    errors = []
    if valid(proxy):
        try:
            proxy.call_function("Cancel")
        except Exception as error:
            errors.append(error)
    pawn = optional_ref(widget, "Pawn")
    if valid(pawn):
        for getter, helper in ((health_for, ORIGINAL_HEALTH_CLEANUP), (extension_for, INIT_UNBIND)):
            try:
                source = getter(pawn)
                if valid(source):
                    if helper == INIT_UNBIND:
                        unregister_init_state(widget, source)
                    else:
                        widget.call_function(helper, source)
            except Exception as error:
                errors.append(error)
    if errors:
        _stats["errors"].extend(str(error) for error in errors)
        raise RuntimeError("nameplate original binding cleanup failed") from errors[0]


class LyraNameplatePythonProfile:
    def __init__(self):
        self._uep_np_live = False
        self._uep_np_extension = self._uep_np_health_scope = self._uep_np_health = None
        self._uep_np_team_scope = self._uep_np_team_proxy = None
        self._uep_np_team_callbacks = self._uep_np_health_callbacks = self._uep_np_init_callbacks = 0

    def BindIndicator(self, Indicator):
        close(self)
        self.set_property("Indicator", Indicator)
        pawn = Indicator.call_function("GetDataObject") if valid(Indicator) else None
        self.set_property("Pawn", pawn if valid(pawn) and pawn.is_a(ue.find_class("Pawn")) else None)
        if valid(Indicator):
            Indicator.call_function("SetDesiredVisibility", False)
        for observer in tuple(_validation_bind_observers):
            observer(self, Indicator)
        extension = extension_for(self.Pawn)
        if valid(extension):
            # Store ownership BEFORE the native immediate callback.
            self._uep_np_live, self._uep_np_extension = True, extension
            _active[id(self)] = self.get_path_name()
            _stats["init_bound"] += 1
            try:
                self.call_function(INIT_BIND, extension)
            except Exception:
                close(self)
                raise
        _stats["binds"] += 1

    def PawnReadyEvent(self, Params):
        if self._uep_np_live:
            self._uep_np_init_callbacks += 1
            _stats["init_callbacks"] += 1
            self.call_function("PawnReady")

    def PawnReady(self):
        pawn = self.Pawn
        if valid(pawn):
            player_state = pawn.PlayerState
            name = player_state.call_function("GetPlayerName") if valid(player_state) else ""
            self.call_function("InitializeNameplate", pawn, name)

    def InitializeNameplate(self, Pawn, Name):
        self.set_property("Pawn", Pawn)
        self.set_property("NameText", Name)
        self._uep_np_live = True
        _active[id(self)] = self.get_path_name()
        self.Indicator.call_function("SetDesiredVisibility", True)
        self.call_function("SetVisibility", 0)
        self.call_function("SetNameText", self.NameText)
        observe_team(self)
        observe_health(self)
        self.call_function("UpdateVisibility")

    def SetNameText(self, PlayerName):
        text = ue.find_class("KismetTextLibrary").get_cdo().call_function("Conv_StringToText", PlayerName)
        self.Name.call_function("SetText", text)

    def SetHealthBarPercent(self, HealthPercent):
        value = self.Health.call_function("GetDynamicMaterial")
        if valid(value):
            value.call_function("SetScalarParameterValue", "Progress", float(HealthPercent))

    def HealthChanged(self, HealthComponent, OldValue, NewValue, Instigator):
        if self._uep_np_live:
            self.call_function("SetHealthBarPercent", HealthComponent.call_function("GetHealthNormalized"))
            self._uep_np_health_callbacks += 1
            _stats["health_callbacks"] += 1

    HealthChanged.override = "Health Changed"

    def DeathStarted(self, OwningActor):
        if self._uep_np_live and valid(self.Indicator):
            self.Indicator.call_function("UnregisterIndicator")
            _stats["death_callbacks"] += 1

    def SetTeamVisuals(self):
        index = int(self.TeamId)
        # K2 Select's compiled switch uses Option 0 for an unmatched index.
        # That is a null Health resource here, not a blue-team substitute.
        index = index if index in (1, 2) else 0
        health = material("/Game/UI/Menu/Art/MI_UI_Teams_" + ("RedTeam" if index == 1 else "BlueTeam") + "_HealthBar") if index else None
        replace_resource(self.Health, health)
        for target, function in ((self.Name, "GetDynamicFontMaterial"), (self.Glow, "GetDynamicMaterial")):
            value = target.call_function(function)
            if valid(value):
                value.call_function("SetScalarParameterValue", "Animate_ActiveToInactive", 1.0 if index == 1 else 0.0)
        health_component = health_for(self.Pawn)
        if valid(health_component):
            self.call_function("SetHealthBarPercent", health_component.call_function("GetHealthNormalized"))
        # Original TeamIcon SetBrush has NO execution connection. It is not
        # executed by SetTeamVisuals. Do not manufacture an icon update.

    def UpdateVisibility(self):
        controller = self.Pawn.call_function("GetController") if valid(self.Pawn) else None
        owner = self.call_function("GetOwningPlayer")
        if self.HideOwnerName and controller == owner:
            self.call_function("SetVisibility", 1)
        elif self.ShowTeamNamesOnly:
            if compare_teams(self, self.Pawn, owner) != 0:  # OnSameTeam returns without restoring visibility.
                self.call_function("SetVisibility", 1)

    def UnbindIndicator(self, Indicator):
        release_validation_pair(self)
        close(self)
        self.set_property("Pawn", None)
        self.set_property("Indicator", None)
        _stats["unbinds"] += 1

    def ResumeObservation(self):
        if not self._uep_np_live and valid(self.Indicator):
            self.call_function("BindIndicator", self.Indicator)

    ResumeObservation.override = RESUME

    def Destruct(self):
        release_validation_pair(self)
        close(self)

    def __uep_mixin_teardown__(self):
        release_validation_pair(self)
        close(self)


class LyraNameplateBlueprintFallbackProfile:
    def __init__(self):
        pass

    def BindIndicator(self, Indicator):
        close_original(self)
        self.call_mixin_original("BindIndicator", Indicator)

    def InitializeNameplate(self, Pawn, Name):
        # Cancel only the previous async observation before the preserved BP
        # creates another. Health delegates use the original unique binding.
        proxy = optional_ref(self, ORIGINAL_TEAM_PROXY)
        if valid(proxy):
            proxy.call_function("Cancel")
        setattr(self, ORIGINAL_TEAM_PROXY, None)
        self.call_mixin_original("InitializeNameplate", Pawn, Name)

    def UnbindIndicator(self, Indicator):
        close_original(self)
        self.call_mixin_original("UnbindIndicator", Indicator)

    def ResumeObservation(self):
        if valid(self.Indicator):
            self.call_function("BindIndicator", self.Indicator)

    ResumeObservation.override = RESUME

    def Destruct(self):
        close_original(self)

    def __uep_mixin_teardown__(self):
        close_original(self)
