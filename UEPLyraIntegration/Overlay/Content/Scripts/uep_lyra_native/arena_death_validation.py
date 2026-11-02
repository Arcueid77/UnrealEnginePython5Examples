"""Reuse the real Arena death/task and owned actor lifecycle observation."""
import atexit
import copy
import unreal_engine as ue
from uep_lyra_world import arena_actor_validation as original
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import ability_lifecycle as policy


class Validation(original.Validation):
    def __init__(self, result):
        super().__init__(result)
        self.native_profile = original.arg('UEPNativeArenaDeathProfile')
        self.report['native_profile'] = self.native_profile
        self.report['previous_blueprint_policy_fixed'] = 'Python'

    def team(self):
        if self.team_index == 2 and original.frame()-self.start_frame >= 3:
            pawn = original.policy.lib('GameplayStatics').call_function('GetPlayerController',self.world,0).get_controlled_pawn()
            spec = next(s for s in ability_system(pawn).get_property('ActivatableAbilities').Items
                if valid(s.Ability) and s.Ability.is_a(self.classes['death']))
            ability = next(a for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(a))
            ue.set_mixin_profile(ability,self.native_profile)
            self.native_before = copy.deepcopy(policy.metrics(ability))
        super().team()

    def dying(self):
        super().dying()
        if self.stage != 'death':
            after = policy.metrics(self.death_ability)
            self.report['native_lifecycle_counts'] = {k:after[k]-self.native_before[k] for k in after if k!='trace'}

    def finalize(self):
        super().finalize()
        if self.report['status']=='passed':
            try:
                from .arena_death_contract import validate
                validate(self.report)
            except Exception:
                self.report.update(status='failed',error=original.traceback.format_exc())
        self.write()
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_ARENA_DEATH_SHUTDOWN_'+self.report['status'].upper())


validation=Validation(original.arg('UEPNativeArenaDeathResult'))
atexit.register(validation.finalize)
ticker=ue.add_ticker(validation.tick)
