"""Opt-in native world-bounds death; original respawn and fresh owner input."""
import atexit,copy,math,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture,services
from uep_lyra_abilities import reload_magazine_mixin as ammo
from .hero_burst_cue_mixin import lib
from .weapon_lethal_network_validation import ability_for,WEAPONS,firing
from .weapon_respawn_network_validation import SELECTORS
from .weapon_respawn_standalone_contract import FORBIDDEN,require,validate

def path(value):return value.get_path_name() if valid(value) else None

class Validation:
    def __init__(self,result,profile):
        self.path=Path(result);self.profile=profile;self.started=time.monotonic();self.phase='ready';self.finished=False
        self.scope=SubscriptionScope();self.selectors=[];self.roots=[];self.sources={};self.actions=[];self.pressed=False
        self.fires=[];self.events=[];self.death=None;self.ended=False
        self.report=dict(schema_version=1,status='running',error=None,profile=profile)
        self.report.update(dict.fromkeys(FORBIDDEN,False))
        for name in (*SELECTORS,firing.CLASS,WEAPONS['pistol']):
            cls=ue.load_class(name)
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            cdo=cls.get_cdo()
            if 'PythonMixinProfile' in cdo.properties():
                self.selectors.append((cls,cdo.get_property('PythonMixinProfile')));cdo.set_property('PythonMixinProfile',profile)

    def state(self,pawn):
        if not valid(pawn):return None
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'));asc=ability_system(pawn)
        state=self.controller.PlayerState;state_asc=state.get_property('AbilitySystemComponent')
        if not valid(health) or not valid(asc) or not valid(state_asc):return None
        attributes=[a for a in state_asc.get_property('SpawnedAttributes') if valid(a) and a.is_a(ue.find_class('LyraHealthSet'))]
        if len(attributes)!=1:return None
        return dict(pawn=path(pawn),player_state=path(state),native_class=pawn.get_class().get_path_name(),
            health=float(health.call_function('GetHealth')),attribute_health=float(attributes[0].get_property('Health').CurrentValue),
            death_state=int(health.call_function('GetDeathState')),native_role=int(pawn.call_function('GetLocalRole')),
            asc_bound=asc==state_asc and health.get_property('AbilitySystemComponent')==asc and valid(health.get_property('HealthSet')),
            avatar=path(state_asc.get_property('AvatarActor')),profile=str(ue.get_mixin_profile(pawn)))

    def living(self,pawn):
        row=self.state(pawn)
        return row if row and row['health']==row['attribute_health']==100. and row['asc_bound'] and row['avatar']==row['pawn'] and row['death_state']==0 else None

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3):continue
            bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.bAbilitySystemReady and not snap.bDamageImmune):continue
            self.world=world;self.controller=lib('GameplayStatics').call_function('GetPlayerController',world,0)
            pawn=self.controller.get_controlled_pawn();row=self.living(pawn)
            if row is None or not valid(ability_for(pawn,ue.load_class(WEAPONS['pistol']))):continue
            self.report['native_mode']=str(snap.NetMode);require(str(snap.NetMode)=='Standalone','Standalone world required')
            bots,=lib('GameplayStatics').call_function('GetAllActorsOfClass',world,ue.find_class('LyraPlayerBotController'))
            self.report['native_bot_controllers']=len(bots);require(not bots,'Isolated authored KillZ case requires zero native bots')
            self.old=pawn;self.before=row;self.health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
            settings=[a for a in world.all_actors() if valid(a) and a.is_a(ue.find_class('WorldSettings'))]
            require(len(settings)==1,'One authored WorldSettings required');self.settings=settings[0]
            self.kill_z=float(self.settings.get_property('KillZ'))
            require(bool(self.settings.get_property('bEnableWorldBoundsChecks')) and math.isfinite(self.kill_z),'Authored world KillZ checks must be enabled')
            self.original_control=self.controller.call_function('GetControlRotation')
            self.scope.bind_event(self.health,'OnDeathStarted',self.on_death);self.scope.bind_event(pawn,'OnEndPlay',self.on_end)
            self.actions=[ue.load_object(ue.find_class('InputAction'),'/Game/Input/Actions/'+n+'.'+n) for n in ('IA_Weapon_Fire','IA_Weapon_Fire_Auto')]
            self.observe_fire();self.begin_fire(pawn,'fire-before');return

    def observe_fire(self):
        self.weapon_cls=ue.load_class(firing.CLASS);ue.register_declared_mixin(self.weapon_cls)
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.weapon_cls]
        self.sources={p:v['python_class'] for p,v in row['profiles'].items()}
        for profile,base in self.sources.items():
            attrs={k:v for k,v in vars(base).items() if not k.startswith('__')}
            def observe(handler,selected,kind):
                def invoke(ability,*args):
                    source=path(ability.call_function('GetAvatarActorFromActorInfo'))
                    if self.phase in ('fire-before','fire-after') and source==self.fire_pawn:
                        self.events.append(dict(kind=kind,source=source,profile=selected,authority=bool(ability.call_function('K2_HasAuthority'))))
                    return handler(ability,*args)
                invoke.override='K2_ActivateAbility' if kind=='activate' else 'OnRangedWeaponTargetDataReady';return invoke
            attrs['Activate']=observe(base.Activate,profile,'activate');attrs['TargetData']=observe(base.TargetData,profile,'target-data')
            ue.register_mixin_profile(self.weapon_cls,profile,type('ObservedStandaloneLifeFire'+profile,(),attrs))

    def begin_fire(self,pawn,phase):
        self.phase=phase;self.fire_started=time.monotonic();self.fire_pawn=path(pawn);self.events=[];self.gestures=0
        model=capture(self.controller);require(model and 'ID_Pistol' in model['definition'],'Original native pistol inventory required')
        self.item=services(self.controller)[1].call_function('GetActiveSlotItem');self.ammo_before=ammo.ammo(self.item)[0]
        origin=self.controller.get_property('PlayerCameraManager').call_function('GetCameraLocation')
        self.controller.call_function('SetControlRotation',lib('KismetMathLibrary').call_function('FindLookAtRotation',origin,ue.FVector(origin.x,origin.y,origin.z+10000.)))

    def inject(self,pressed):
        for action in self.actions:self.controller.inject_enhanced_input_for_action(action,pressed)
        self.pressed=pressed

    def fire_tick(self):
        if self.pressed:self.inject(False)
        elif not self.gestures:self.inject(True);self.gestures=1
        current=ammo.ammo(self.item)[0]
        if current==self.ammo_before or not any(e['kind']=='target-data' for e in self.events):
            require(time.monotonic()-self.fire_started<12.,'Real owner fire did not reach native ammo/target data');return
        require(self.ammo_before-current==1,'Owner gesture consumed more than one native round')
        if self.pressed:return
        self.fires.append(dict(pawn=self.fire_pawn,definition_is_pistol=True,ammo_before=self.ammo_before,ammo_after=current,
            gestures=self.gestures,input_released=True,events=copy.deepcopy(self.events)))
        if self.phase=='fire-before':
            self.phase='death';self.death_started=time.monotonic();point=self.old.get_actor_location()
            accepted=bool(self.old.call_function('K2_TeleportTo',ue.FVector(point.x,point.y,self.kill_z-1000.),self.old.get_actor_rotation()))
            self.hazard=dict(kill_z=self.kill_z,world_bounds_enabled=True,placement_accepted=accepted,placed_z=float(self.old.get_actor_location().z))
            require(accepted,'Native below-KillZ placement rejected')
        else:
            self.final=self.living(self.controller.get_controlled_pawn());require(self.final is not None,'Fresh Pawn health/ASC changed after owner input')
            self.report['result']=dict(before_death=self.before,after_respawn=self.after,after_new_life_fire=self.final,death=self.death,
                old_pawn_end_play_observed=self.ended,respawn_seconds=self.respawn_seconds,fires=self.fires,
                hazard=dict(self.hazard,kill_z_after=float(self.settings.get_property('KillZ')),
                    world_bounds_enabled_after=bool(self.settings.get_property('bEnableWorldBoundsChecks'))))
            self.finish()

    def on_death(self,pawn):
        self.death=dict(observed=True,pawn=path(pawn),health=float(self.health.call_function('GetHealth')))

    def on_end(self,pawn,reason):self.ended=True;self.scope.close()

    def respawn_tick(self):
        self.report['death_observation']=self.death
        require(time.monotonic()-self.death_started<45.,'Native KillZ death/respawn did not complete')
        pawn=self.controller.get_controlled_pawn();row=self.living(pawn)
        if not self.death or not self.ended or row is None or row['pawn']==self.before['pawn']:return
        if not valid(pawn.get_property('InputComponent')) or not valid(ability_for(pawn,ue.load_class(WEAPONS['pistol']))):return
        model=capture(self.controller)
        if not model or 'ID_Pistol' not in model['definition']:return
        self.after=row;self.respawn_seconds=time.monotonic()-self.death_started;self.begin_fire(pawn,'fire-after')

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<150.,'Standalone death/respawn total timeout: '+self.phase)
            if self.phase=='ready':self.ready()
            elif self.phase in ('fire-before','fire-after'):self.fire_tick()
            elif self.phase=='death':self.respawn_tick()
            self.report['phase']=self.phase;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def cleanup(self):
        self.scope.close();self.report['observer_scope_closed']=self.scope.closed
        if self.actions:self.inject(False)
        self.report['input_released']=not self.pressed
        if hasattr(self,'original_control'):self.controller.call_function('SetControlRotation',self.original_control)
        for profile,source in self.sources.items():ue.register_mixin_profile(self.weapon_cls,profile,source)
        self.report['profile_classes_restored']=not self.sources or all(next(r for r in ue.get_registered_mixins() if r['target_class']==self.weapon_cls)['profiles'][p]['python_class'] is s for p,s in self.sources.items())
        for cls,profile in self.selectors:cls.get_cdo().set_property('PythonMixinProfile',profile)
        self.report['boot_selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==profile for cls,profile in self.selectors)
        for cls in self.roots:cls.remove_from_root()
        self.report['probe_roots_removed']=all(not cls.is_rooted() for cls in self.roots)

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_WEAPON_RESPAWN_STANDALONE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_WEAPON_RESPAWN_STANDALONE_SHUTDOWN_'+self.report['status'].upper())

if any(v.startswith('-UEPWeaponRespawnStandaloneResult=') for v in sys.argv):
    result=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPWeaponRespawnStandaloneResult='))
    profile=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPWeaponRespawnProfile='))
    validation=Validation(result,profile);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
