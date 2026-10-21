"""Owned local Characters in a real client/listen server; native lifetime only."""
import atexit,copy,hashlib,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer
from uep_lyra_network_io import read_json,atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_abilities.melee_trace_mixin import break_hit
from .outline_validation import canon
from .hero_default_ragdoll_validation import primary_state
from .hero_default_stencil_validation import CLASSES,path
from .hero_parent_test_profiles import defaults
from . import hero_default_motion_mixin as policy
from uep_lyra_weapons import footstep_mixin as downstream
from .hero_default_motion_contract import KINDS,FALSE_FIELDS,require,validate

def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def dead(a):return not valid(a) or bool(a.call_function('IsActorBeingDestroyed'))
def vec(a):return [float(a.x),float(a.y),float(a.z)]
def payload(args):
    bone,tag,component,offset,rotation,animation,hit,result,contexts,scale,volume,pitch=args
    return [str(bone),str(tag.TagName),path(component),vec(offset),[float(rotation.pitch),float(rotation.yaw),float(rotation.roll)],path(animation),bool(hit),canon(break_hit(result)),canon(contexts),vec(scale),float(volume),float(pitch)]

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.role=arg('UEPHeroMotionRole');self.run=arg('UEPHeroMotionRun');self.root=Path(result).parent;self.report=dict(status='running',error=None,role=self.role,run_id=self.run,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.actors=[];self.feet=[];self.roots=[];self.rows=[];self.observed={};self.no_fx={};self.original_classes={};self.selector=None;self.cleaned=False
    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3):continue
            bridge=policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot');self.report['readiness']=dict(experience=bool(snap.bExperienceLoaded),input=bool(snap.bHeroInputReady),health_ready=bool(snap.bHealthReady),health=float(snap.Health),immune=bool(snap.bDamageImmune))
            if not(snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
            controller=self.statics.call_function('GetPlayerController',world,0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):continue
            self.world,self.controller,self.pawn=world,controller,controller.get_controlled_pawn();self.report['native_mode']=str(snap.NetMode);self.report['native_is_server']=bool(policy.lib('KismetSystemLibrary').call_function('IsServer',world));self.begin();return
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.primary_before=primary_state(self.pawn);self.shooter_owner=ue.describe_function(self.pawn.get_class(),'AnimMotionEffect')['owner'];self.cls=ue.load_class(policy.CLASS);self.selector=self.cls.get_cdo().get_property(policy.SELECTOR);ue.register_declared_mixin(self.cls);self.classes={k:ue.load_class(v) for k,v in CLASSES.items()};self.caller=ue.load_class('/Game/UEPValidation/BP_HeroDefaultMotionCaller.BP_HeroDefaultMotionCaller_C').get_cdo();self.foot_cls=ue.load_class(policy.FOOTSTEP);ue.register_declared_mixin(self.foot_cls);self.mesh_asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset');self.animation=ue.load_object(ue.find_class('AnimSequenceBase'),'/Game/Characters/Heroes/Mannequin/Animations/Actions/AM_MM_Death_Back_01.AM_MM_Death_Back_01')
        for obj in (self.cls,self.caller,self.foot_cls,self.mesh_asset,self.animation)+tuple(self.classes.values()):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        binding,=[r for r in ue.get_registered_mixins() if r['target_class']==self.foot_cls];self.original_classes={p:v['python_class'] for p,v in binding['profiles'].items()};owner=self
        for profile,base in self.original_classes.items():
            def wrap(fn):
                def invoke(actor,*args):
                    key=path(actor);owner.observed.setdefault(key,[]).append(payload(args));result=fn(actor,*args);owner.no_fx[key]=owner.no_fx.get(key,True) and not valid(actor.get_property('NS_FootPrint'));return result
                return invoke
            attrs={n:v for n,v in vars(base).items() if not n.startswith('__')};attrs['AnimMotionEffect']=wrap(base.__dict__['AnimMotionEffect']);ue.register_mixin_profile(self.foot_cls,profile,type('ObservedMotion'+profile,(),attrs))
        for profile in ('BlueprintFallback','Python'):
            for kind in KINDS:self.spawn(profile,kind)
        if self.role=='server':self.complete();return
        self.last_call=self.game_time();self.max_delta=0.;self.enter('retrigger')
    def spawn(self,profile,kind):
        with defaults(self.classes[kind],profile):a=self.world.actor_spawn(self.classes[kind],ue.FVector(200000.+len(self.actors)*1000.,200000.,5000.))
        self.actors.append(a);a.call_function('SetReplicates',False);a.get_property('CharacterMovement').call_function('SetMovementMode',5,0);mesh=a.get_property('Mesh');mesh.call_function('SetSkeletalMeshAsset',self.mesh_asset);ue.set_mixin_profile(a,profile);function_owner=ue.describe_function(a.get_class(),'AnimMotionEffect')['owner'];empty=kind=='explorer-hero';row=dict(profile=profile,kind=kind,typed_second_blueprint_caller=True,actual_function_owner_preserved=(function_owner==CLASSES[kind] and a.find_function('AnimMotionEffect').get_class().get_name()!='PythonFunction') if empty else function_owner==policy.CLASS and a.find_function('AnimMotionEffect').get_class().get_name()=='PythonFunction',expected_payloads=[]);self.report['cases'].append(row);entry=dict(actor=a,row=row,mesh=mesh,foot=None)
        for step in range(2):self.call(entry,step)
        foot=a.get_property('FootStep');client=self.role=='client' and not empty
        if client:
            require(valid(foot),'real client motion did not create footstep');entry['foot']=foot;entry['first_path']=path(foot);self.feet.append(foot);root=foot.get_property('RootComponent');row.update(native_exposed_properties_match_source=foot.get_property('Skeletal Mesh Component')==mesh and str(foot.get_property('FootStepRightFootBone'))=='foot_r',native_keep_relative_attachment_matches=foot.get_property('RootComponent').call_function('GetAttachParent')==mesh and vec(root.get_property('RelativeLocation'))==[0.,0.,0.] and vec(root.get_property('RelativeScale3D'))==[1.,1.,1.],same_footstep_reused=len(self.observed.get(path(foot),[]))==2,native_original_delay_seconds=3.)
        else:row['no_footstep_spawned_or_forwarded']=not valid(foot) and not self.observed.get(path(foot),[])
        self.rows.append(entry)
    def call(self,entry,step):
        args=('foot_l' if step%2 else 'foot_r',GameplayTag(TagName='Gameplay.Damage.FellOutOfWorld'),self.pawn.get_property('Mesh'),ue.FVector(1.25,-2.5,3.75),ue.FRotator(10.,20.,30.),self.animation,False,ue.find_struct('HitResult')(),GameplayTagContainer(GameplayTags=[GameplayTag(TagName='Gameplay.Damage.FellOutOfWorld')]),ue.FVector(2.,3.,4.),.25,1.5);entry['row']['expected_payloads'].append(payload(args));self.caller.call_function('CallMotion',entry['actor'],*args)
    def observe(self):
        if self.phase=='release':
            release=read_json(self.root/'release.json')
            if release and release.get('run_id')==self.run:self.finish()
            return
        self.max_delta=max(self.max_delta,float(self.statics.call_function('GetWorldDeltaSeconds',self.world)));elapsed=self.game_time()-self.last_call;active=[e for e in self.rows if e['foot'] is not None]
        if self.phase=='retrigger':
            if elapsed<.4:return
            for e in active:self.call(e,2);e['row']['same_footstep_reused'] &= e['actor'].get_property('FootStep')==e['foot']
            self.last_call=self.game_time();self.enter('before-deadline');return
        if self.phase=='before-deadline':
            if elapsed<2.75:return
            for e in active:e['row']['native_retrigger_preserved_actor_before_deadline']=not dead(e['foot'])
            self.enter('destroy');return
        if self.phase=='destroy':
            for e in active:
                if dead(e['foot']) and 'native_destruction_elapsed' not in e['row']:e['row']['native_destruction_elapsed']=elapsed
            if not all(dead(e['foot']) for e in active):require(elapsed<4.,'native retriggerable3s cleanup did not destroy footstep');return
            for e in active:
                e['row']['native_destroyed_after_delay']=True;old=e['first_path'];self.call(e,3);new=e['actor'].get_property('FootStep');require(valid(new),'expired footstep was not recreated');e['replacement']=new;e['replacement_path']=path(new);self.feet.append(new);e['row']['replacement_is_new_actor']=path(new)!=old;e['row']['observed_payloads']=self.observed.get(old,[])+self.observed.get(path(new),[])
            self.last_call=self.game_time();self.enter('replacement');return
        if self.phase=='replacement':
            if not all(dead(e['replacement']) for e in active):require(elapsed<4.,'native replacement cleanup timeout');return
            for e in active:e['row'].update(replacement_naturally_destroyed=True,all_twelve_payloads_match=e['row']['observed_payloads']==e['row']['expected_payloads'],downstream_calls=len(e['row']['observed_payloads']),native_downstream_no_footprint_component=self.no_fx.get(e['first_path'],False) and self.no_fx.get(e['replacement_path'],False),maximum_world_delta=self.max_delta)
            self.complete()
    def complete(self):
        for e in self.rows:e['row']['counts']=copy.deepcopy(policy.evidence(e['actor']))
        self.cleanup();self.report['status']='awaiting_release';self.write();atomic_write(self.root/('ready-'+self.role+'.json'),dict(run_id=self.run));self.enter('release')
    def cleanup(self):
        if self.cleaned:return
        self.cleaned=True
        for a in self.feet:
            if not dead(a):ue.clear_mixin_profile(a);a.actor_destroy()
        for a in self.actors:
            if valid(a):ue.clear_mixin_profile(a);a.actor_destroy()
        for p,base in self.original_classes.items():ue.register_mixin_profile(self.foot_cls,p,base)
        if self.selector is not None:self.cls.get_cdo().set_property(policy.SELECTOR,self.selector)
        for obj in self.roots:obj.remove_from_root()
        self.report.update(primary_inventory_health_and_physics_unchanged=capture(self.controller)==self.player_before and self.healths()==self.health_before and primary_state(self.pawn)==self.primary_before,existing_shooter_child_router_owner_preserved=ue.describe_function(self.pawn.get_class(),'AnimMotionEffect')['owner']==self.shooter_owner,owned_actors_profiles_roots_and_selectors_restored=all(dead(a) for a in self.actors+self.feet) and all(not obj.is_rooted() for obj in self.roots) and self.cls.get_cdo().get_property(policy.SELECTOR)==self.selector,original_downstream_profile_classes_restored=all(next(r for r in ue.get_registered_mixins() if r['target_class']==self.foot_cls)['profiles'][p]['python_class'] is cls for p,cls in self.original_classes.items()))
        hashes=read_json(Path(arg('UEPHeroMotionHashes')));self.report['descendant_and_downstream_asset_hashes_unchanged']=bool(hashes) and all(hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()==h.upper() for p,h in hashes.items())
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<360.,'motion network/readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HERO_PARENT_MOTION_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HERO_PARENT_MOTION_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroParentMotionResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
