"""Compare actual Native NullRHI spawn failure with original cached nulls."""
import sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayCueNotify_SpawnResult
from .spawning_cue_validation import Validation as Fixtures
from . import spawning_cue_mixin as policy
from .spawning_null_effect_contract import FALSE,require,validate
from uep_lyra_world.effect_pad_mixin import valid

class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[],null_rhi='-NullRHI' in sys.argv)
        self.report.update(dict.fromkeys(FALSE,False))
    def snapshot(self,cue,target):
        effects=list(cue.get_property('SpawnedEffects'));mapping=dict(cue.get_property('SpawnedEffectMap'))
        return dict(array_count=len(effects),map_count=len(mapping),array_all_null=all(e is None for e in effects),map_all_null=all(e is None for e in mapping.values()),expected_mesh_keys=set(mapping)=={target['meshes'][0],target['meshes'][2]},ignored_mesh_absent=target['meshes'][1] not in mapping)
    def start_pair(self):
        require(self.report['null_rhi'],'Actual NullRHI is required;no spawn-result injection')
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls]
        self.report['mixin_profile_method_counts']={p:len(v['functions']) for p,v in row['profiles'].items()}
        self.targets=[];self.current=[]
        for profile in ('BlueprintFallback','Python'):
            target=self.make_target(False,0);self.targets.append(target)
            cue=self.world.actor_spawn(self.cls);self.cues.append(cue);self.current.append(cue);ue.set_mixin_profile(cue,profile)
            cue.set_property('TargetActor',target['actor']);cue.set_property('TemplateToUse',self.system)
            before=dict(policy.evidence(cue));cue.call_function('SpawnEffectForEachMeshComponent');initial=self.snapshot(cue,target)
            cue.call_function('SpawnEffectForEachMeshComponent');repeat=self.snapshot(cue,target)
            prefix='python_' if profile=='Python' else 'fallback_';other='fallback_' if profile=='Python' else 'python_';counts=policy.evidence(cue)
            cue.call_function('OnRemoval',target['actor'],self.params(.35,False),GameplayCueNotify_SpawnResult())
            self.report['cases'].append(dict(profile=profile,initial=initial,repeat=repeat,selected_spawn_entries=counts[prefix+'spawn']-before[prefix+'spawn'],other_spawn_entries=counts[other+'spawn']-before[other+'spawn'],
                spawn_attempts=counts['spawns']-before['spawns'],existing_meshes=counts['existing_meshes']-before['existing_meshes'],diagnostic_fallbacks=counts['diagnostic_fallbacks']-before['diagnostic_fallbacks'],removal_cleared_caches=not cue.get_property('SpawnedEffects') and not cue.get_property('SpawnedEffectMap')))
        self.finish()
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'Null result fixture timeout')
            self.ready();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SPAWNING_NULL_EFFECT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SPAWNING_NULL_EFFECT_SHUTDOWN_'+self.report['status'].upper())
