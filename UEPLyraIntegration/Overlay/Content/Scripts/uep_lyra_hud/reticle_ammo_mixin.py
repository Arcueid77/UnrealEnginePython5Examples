"""0.10 ammo-reticle presentation; native inventory and UMG layout retained."""

import unreal_engine as ue
from unreal_engine.structs import LinearColor

from . import weapon_observer


def render(widget, value):
    # The authored BP uses native safe floating division (zero denominator ->
    # zero), scales to one quarter of the circular material, and puts it in G.
    maximum = value["maximum"]
    fraction = value["magazine"] / maximum if maximum else 0.0
    material = widget.ProgressBorder.call_function("GetDynamicMaterial")
    material.call_function("SetScalarParameterValue", "Segments", float(maximum * 4 + 1))
    material.call_function("SetVectorParameterValue", "ActiveRange", LinearColor(R=0.0, G=fraction * 0.25, B=0.0, A=1.0))
    widget._uep_reticle_updates += 1


def observe(widget):
    if not widget._uep_reticle_disposed and widget._uep_weapon_subscription is None:
        weapon_observer.subscribe(widget, "reticle-ammo", render)
        weapon_observer.refresh(widget)


class LyraReticleAmmoPythonProfile:
    def __init__(self):
        self._uep_weapon_subscription = None
        self._uep_reticle_disposed = False
        self._uep_reticle_updates = 0

    def Construct(self):
        self._uep_reticle_disposed = False
        observe(self)

    def OnWeaponInitialized(self):
        self._uep_reticle_disposed = False
        observe(self)
        weapon_observer.refresh(self)

    def Tick(self, MyGeometry, InDeltaTime):
        observe(self)

    def Destruct(self):
        self._uep_reticle_disposed = True
        weapon_observer.unsubscribe(self)

    def __uep_mixin_teardown__(self):
        self._uep_reticle_disposed = True
        weapon_observer.unsubscribe(self)


class LyraReticleAmmoBlueprintFallbackProfile:
    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)
