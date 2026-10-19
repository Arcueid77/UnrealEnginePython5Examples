"""Actual parent field/Chaos solver events; no break callback or Tick replay."""
import atexit
import math
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead
from uep_lyra_world.effect_pad_mixin import valid
from . import physics_field_mixin as policy
from .physics_field_contract import PLAN,require,validate


def total(actor,name):return sum(policy.evidence(actor)[p+'_'+name] for p in ('python','fallback'))
def path(obj):return obj.get_path_name() if valid(obj) else None


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,pairs=[]);self.sources={};self.fields=[];self.spheres=[];self.index=0;self.callbacks={}
        for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','break_callbacks_replayed','tick_callbacks_replayed','native_timer_properties_written','health_properties_written','identical_random_physics_fragments_claimed'):self.report[key]=False
    def begin(self):
        self.report['native_mode']=str(ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        for kind,cls in self.classes.items():
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[kind]={p:r['python_class'] for p,r in row['profiles'].items()}
        owner=self
        for profile,source in self.sources['sphere'].items():
            methods={n:v for n,v in vars(source).items() if not n.startswith('__') and callable(v)}
            def around(handler):
                def invoke(actor,BreakEvent):
                    key=path(actor)
                    if key in owner.callbacks:owner.callbacks[key].append(dict(component_matches=BreakEvent.Component==actor.get_property('GeometryCollectionComponent'),mass=float(BreakEvent.Mass),location_finite=all(math.isfinite(float(v)) for v in (BreakEvent.Location.x,BreakEvent.Location.y,BreakEvent.Location.z))))
                    return handler(actor,BreakEvent)
                return invoke
            methods['SphereIsBroken']=around(source.SphereIsBroken);ue.register_mixin_profile(self.classes['sphere'],profile,type('ObservedPhysicsBreak'+profile,(),methods))
        self.start_pair()
    def spawn(self,kind,profile,location,controlled):
        transform=ue.FTransform();transform.translation=ue.FVector(*location)
        actor=self.statics.call_function('BeginDeferredActorSpawnFromClass',self.world,self.classes[kind],transform,1,None);self.actors.append(actor);ue.set_mixin_profile(actor,profile)
        if kind=='example' and controlled:actor.set_property('Field Active',False);actor.set_property('FieldLifespan',2.)
        self.statics.call_function('FinishSpawningActor',actor,transform)
        if kind=='example':self.fields.append(actor)
        else:self.spheres.append(actor)
        return actor
    def state(self,actor):
        component=actor.get_property('GeometryCollectionComponent');materials=[actor.get_property(n) for n in ('DynaMat1','DynaMat2')]
        return dict(target=float(actor.get_property('TargetGlowAmt')),current=float(actor.get_property('CurrentGlowAmt')),material_valid=[valid(m) for m in materials],material_slots_match=all(valid(m) and component.call_function('GetMaterial',i)==m for i,m in enumerate(materials)),
            glow=[float(m.call_function('K2_GetScalarParameterValue','GlowAmount')) if valid(m) else None for m in materials],notify_breaks=bool(component.get_property('bNotifyBreaks')),root_broken=bool(component.call_function('IsRootBroken')))
    def start_pair(self):
        self.name,self.controlled,self.switch=PLAN[self.index];self.current=[];self.current_fields=[];self.start=self.game_time();self.switched=False;self.triggered=False
        for i,profile in enumerate(('BlueprintFallback','Python')):
            location=(150000.+self.index*20000.+i*6000.,150000.,3000.);sphere=self.spawn('sphere',profile,location,False);self.current.append(sphere);self.callbacks[path(sphere)]=[]
            field_location=(location[0]+5000.,location[1],location[2]) if self.controlled else location
            field=self.spawn('example',profile,field_location,self.controlled);self.current_fields.append(field)
            if self.controlled:field.call_function('SetActorTickEnabled',True)
        self.field_counts=[policy.evidence(f) for f in self.current_fields];self.initial=[self.state(a) for a in self.current]
        self.row=dict(name=self.name,controlled_native_strain=self.controlled,switch=self.switch,initial_states=self.initial,initial_sphere_begin_entries=[total(a,'begin') for a in self.current],initial_material_entries=[total(a,'materials') for a in self.current],parent_trigger_calls=0,natural_samples=0,all_shaders_and_current_glow_unchanged=True,profile_switch_observed=False)
        self.report['pending_pair']=self.row
        if not self.controlled:
            for field in self.current_fields:field.call_function('CE_Trigger');self.row['parent_trigger_calls']+=1
            self.triggered=True
        self.enter('pair')
    def pair(self):
        elapsed=self.game_time()-self.start
        if self.controlled and not self.triggered and elapsed>=.1:
            if self.switch:
                for field,sphere,profile in zip(self.current_fields,self.current,('Python','BlueprintFallback')):
                    ue.set_mixin_profile(field,profile);ue.set_mixin_profile(sphere,profile);field.call_function('SetActorTickEnabled',True)
                self.switched=True;self.row['profile_switch_observed']=True
            for sphere in self.current:
                component=sphere.get_property('GeometryCollectionComponent');root=int(component.call_function('GetRootIndex'));component.call_function('ApplyExternalStrain',root,sphere.get_actor_location(),1000.,0,1.,1000000000000.)
            self.triggered=True
        self.row['natural_samples']+=1;states=[self.state(a) for a in self.current]
        self.row['all_shaders_and_current_glow_unchanged'] &= all(state['glow']==before['glow'] and state['current']==before['current'] for state,before in zip(states,self.initial))
        events=[self.callbacks[path(a)] for a in self.current]
        if not all(events) or elapsed<.35:
            require(elapsed<6.,'native Chaos break notifications absent: '+self.name);return
        self.row.update(final_states=states,chaos_event_counts=[len(e) for e in events],chaos_payloads_valid=all(e['component_matches'] and e['location_finite'] and e['mass']>0 for values in events for e in values),
            break_handler_counts=[total(a,'break') for a in self.current],field_evidence=self.field_counts,final_profiles=[str(ue.get_mixin_profile(a)) for a in self.current])
        self.report['pairs'].append(self.row)
        for actor in self.current+self.current_fields:
            if not dead(actor):ue.clear_mixin_profile(actor);actor.actor_destroy()
        self.index+=1
        if self.index<len(PLAN):self.start_pair()
        else:self.finish()
    def cleanup(self):
        for kind,sources in self.sources.items():
            for profile,source in sources.items():ue.register_mixin_profile(self.classes[kind],profile,source)
        for actor in self.actors:
            if not dead(actor):ue.clear_mixin_profile(actor);actor.actor_destroy()
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),original_health_unchanged=self.healths()==self.health_before,production_profiles_restored=all(any(r['target_class']==self.classes[k] and all(r['profiles'][p]['python_class'] is source and len(r['profiles'][p]['functions'])==3 for p,source in sources.items()) for r in ue.get_registered_mixins()) for k,sources in self.sources.items()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native physics total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='pair':self.pair()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_PHYSICS_FIELD_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_PHYSICS_FIELD_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPPhysicsFieldResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
