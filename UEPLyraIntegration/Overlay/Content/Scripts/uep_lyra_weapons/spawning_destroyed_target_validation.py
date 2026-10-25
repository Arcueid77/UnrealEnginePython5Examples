"""Opt-in destroyed-target observer selected by the validation startup router."""
import atexit,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayCueNotify_SpawnResult
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons import spawning_cue_mixin as policy
from uep_lyra_weapons.spawning_cue_validation import Validation as Fixtures,count
from uep_lyra_weapons.spawning_destroyed_target_contract import PLAN,FORBIDDEN,require,close,validate

class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.plan=PLAN
        self.report=dict(status='running',error=None,pairs=[],expected_cue_class=policy.CLASS,entrypoint='validation-startup-router')
        self.report.update(dict.fromkeys(FORBIDDEN,False))
    def start_pair(self):
        super().start_pair();old=self.row
        keys=('name','duration','initial_application_entries','initial_team_entries','initial_fx_counts','watchers_native_active','initial_system_configuration')
        self.row={k:old[k] for k in keys};self.report['pending_pair']=self.row
        self.row.update(profiles=[str(ue.get_mixin_profile(c)) for c in self.current],actual_cue_classes=[c.get_class().get_path_name() for c in self.current],natural_samples=0,paired_native_state_matches=True,native_clocks_match=True)
    def pair(self):
        elapsed=self.game_time()-self.start
        states=[self.state(c,t) for c,t in zip(self.current,self.targets)]
        positions=[float(c.get_property('SpawnTimeline').call_function('GetPlaybackPosition')) for c in self.current]
        self.row['natural_samples']+=1;self.row['paired_native_state_matches'] &= close(states[0],states[1]);self.row['native_clocks_match'] &= abs(positions[0]-positions[1])<.0001
        if elapsed<(.12 if self.index==0 else self.duration+.12):return
        self.row['native_clock_playing_at_destroy']=[bool(c.get_property('SpawnTimeline').call_function('IsPlaying')) for c in self.current]
        retained=[(c.get_property('TeamColorWatcherHandle'),c.get_property('PawnCosmeticSystem')) for c in self.current]
        self.update_before=[count(c,'update') for c in self.current];removal_before=[count(c,'removal') for c in self.current]
        for target in self.targets:target['actor'].actor_destroy()
        self.row['native_target_destroyed']=[not valid(t['actor']) or bool(t['actor'].call_function('IsActorBeingDestroyed')) for t in self.targets]
        self.row['invalid_cached_target_reproduced']=[c.get_property('TargetActor') is not None and not valid(c.get_property('TargetActor')) for c in self.current]
        require(self.row['invalid_cached_target_reproduced']==[True,True],'Native cache did not retain the destroyed target;cannot claim the invalid-cache regression')
        # The authored removal reads its retained TargetActor field. Both native
        # event calls receive the same null input rather than marshalling a dead
        # UObject as an argument; the source cached field is never overwritten.
        for cue in self.current:cue.call_function('OnRemoval',None,self.params(self.duration,False),GameplayCueNotify_SpawnResult())
        self.row.update(removal_target_argument_null=True,removal_entries=[count(c,'removal')-b for c,b in zip(self.current,removal_before)],
            cached_target_identity_retained=[c.get_property('TargetActor')==t['actor'] for c,t in zip(self.current,self.targets)],
            removal_cleared_caches=all(not c.get_property('SpawnedEffects') and not c.get_property('SpawnedEffectMap') for c in self.current),
            removal_cancelled_watchers=all(not valid(w) or not w.call_function('IsActive') for w,_ in retained),
            removal_retained_source_handles=all(c.get_property('TeamColorWatcherHandle')==w and c.get_property('PawnCosmeticSystem')==p for c,(w,p) in zip(self.current,retained)),
            native_clock_flags_after_removal=[bool(c.get_property('SpawnTimeline').call_function('IsPlaying')) for c in self.current])
        self.enter('quiet')
    def quiet(self):
        if time.monotonic()-self.phase_started<.9:return
        self.row.update(quiet_seconds=time.monotonic()-self.phase_started,effects_stayed_empty=all(not c.get_property('SpawnedEffects') and not c.get_property('SpawnedEffectMap') for c in self.current),
            post_destroy_updates=[count(c,'update')-b for c,b in zip(self.current,self.update_before)],final_spawn_times=[float(c.get_property('Spawn Linear Time')) for c in self.current],diagnostic_fallbacks=[policy.evidence(c)['diagnostic_fallbacks'] for c in self.current])
        self.report['pairs'].append(self.row)
        for cue in self.current:
            ue.clear_mixin_profile(cue);cue.set_property('NiagaraSystemTemplates',list(self.cls.get_cdo().get_property('NiagaraSystemTemplates')));cue.set_property('SpawningDuration',self.cls.get_cdo().get_property('SpawningDuration'));cue.call_function('K2_EndGameplayCue')
        self.index+=1
        if self.index<len(self.plan):self.start_pair()
        else:self.finish()
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'Destroyed-target spawning timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='pair':self.pair()
            elif self.phase=='quiet':self.quiet()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SPAWNING_DESTROYED_TARGET_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SPAWNING_DESTROYED_TARGET_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSpawningDestroyedResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
