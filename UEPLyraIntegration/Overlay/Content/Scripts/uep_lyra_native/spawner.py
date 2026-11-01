"""Native spawner orchestration; timer handles/overlaps/replication stay native."""
import unreal_engine as ue
from uep_lyra_world.spawner_mixin import LyraSpawnerPythonProfile as PythonBase,LyraSpawnerBlueprintFallbackProfile as BlueprintBase
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/ShooterCore/Blueprint/B_WeaponSpawner.B_WeaponSpawner_C'
CHILD='/ShooterCore/Blueprint/B_AbilitySpawner.B_AbilitySpawner_C'


def metrics(actor):
    if not hasattr(actor,'_uep_native_spawner_metrics'):actor._uep_native_spawner_metrics={p+k:0 for p in ('python_','native_') for k in ('attempt','reset','complete')}
    return actor._uep_native_spawner_metrics


class SpawnerPythonProfile(PythonBase):
    Construction=PythonBase.Construction
    Begin=PythonBase.Begin
    Tick=PythonBase.Tick
    Pickup=PythonBase.Pickup
    Respawn=PythonBase.Respawn
    Update=PythonBase.Update
    WeaponGive=PythonBase.WeaponGive
    AbilityGive=PythonBase.AbilityGive
    def AttemptPickUpWeapon(self,Pawn):
        metrics(self)['python_attempt']+=1
        if int(self.call_function('GetLocalRole'))!=3 or not self.get_property('bIsWeaponAvailable'):return
        asc=ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('GetAbilitySystemComponent',Pawn)
        if not valid(asc):return
        definition=self.get_property('WeaponDefinition');item=definition.InventoryItemDefinition if valid(definition) else None
        if item is not None and self.call_function('GiveWeapon',item,Pawn):
            self.set_property('bIsWeaponAvailable',False);self.call_function('SetWeaponPickupVisibility',False);self.call_function('PlayPickupEffects');self.call_function('StartCoolDown')

    def ResetCoolDown(self):
        metrics(self)['python_reset']+=1;self.call_function('UEPClearSpawnerCooldown')
        if int(self.call_function('GetLocalRole'))==3:
            self.set_property('bIsWeaponAvailable',True);self.call_function('PlayRespawnEffects');self.call_function('SetWeaponPickupVisibility',True);self.call_function('UEPScheduleSpawnerOverlapCheck')
        self.set_property('CoolDownPercentage',0.)

    def OnCoolDownTimerComplete(self):
        metrics(self)['python_complete']+=1;self.call_function('ResetCoolDown')


class SpawnerNativeFallbackProfile(PythonBase):
    # Compare the C++ rules while retaining the accepted Blueprint Python layer.
    Construction=PythonBase.Construction
    Begin=PythonBase.Begin
    Tick=PythonBase.Tick
    Pickup=PythonBase.Pickup
    Respawn=PythonBase.Respawn
    Update=PythonBase.Update
    WeaponGive=PythonBase.WeaponGive
    AbilityGive=PythonBase.AbilityGive
    def AttemptPickUpWeapon(self,Pawn):
        metrics(self)['native_attempt']+=1;return self.call_mixin_original('AttemptPickUpWeapon',Pawn)
    def ResetCoolDown(self):
        metrics(self)['native_reset']+=1;return self.call_mixin_original('ResetCoolDown')
    def OnCoolDownTimerComplete(self):
        metrics(self)['native_complete']+=1;return self.call_mixin_original('OnCoolDownTimerComplete')
