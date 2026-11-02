"""Initial stat application; native inventory creation and tag replication remain."""
CLASSES=(
    '/ShooterCore/Items/HealthPickup_Unused/ID_HealPickup.ID_HealPickup_C',
    '/ShooterCore/Weapons/NetShooter_PROTO/ID_NetShooter.ID_NetShooter_C',
    '/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C',
    '/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C',
    '/ShooterCore/Weapons/Shotgun/ID_Shotgun.ID_Shotgun_C',
)


def metrics(owner):
    if not hasattr(owner,'_uep_initial_stats'):owner._uep_initial_stats=dict(python_selected=0,native_selected=0,python_applied=0,applied_rows=[])
    return owner._uep_initial_stats


class InitialStatsPythonProfile:
    def UEPUsesPythonInitialStats(self):metrics(self)['python_selected']+=1;return True
    def UEPInitializeItemStats(self,fragment,instance):
        state=metrics(self);state['python_applied']+=1
        for row in fragment.call_function('UEPGetInitialStats'):
            state['applied_rows'].append((str(row.Tag.TagName),int(row.Count)))
            instance.call_function('AddStatTagStack',row.Tag,int(row.Count))


class InitialStatsNativeFallbackProfile:
    def UEPUsesPythonInitialStats(self):metrics(self)['native_selected']+=1;return self.call_mixin_original('UEPUsesPythonInitialStats')
    def UEPInitializeItemStats(self,fragment,instance):raise AssertionError('Native stat loop must be selected before entering Python mutation')
