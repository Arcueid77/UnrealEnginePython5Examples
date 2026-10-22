"""Client native fire input, native target data/damage and original score/relay path."""
import atexit, copy, math, sys, time, traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_abilities.melee_trace_mixin import break_hit
from uep_lyra_abilities import reload_magazine_mixin as ammo
from uep_lyra_hud.weapon_validation_helpers import set_stat
from uep_lyra_hud.notification_relays_network_validation import identity
from .hero_burst_cue_mixin import lib
from .tdm_lethal_network_validation import Network as Lethal, arg
from .weapon_ability_fire_network_validation import ability_for, line_of_sight
from .weapon_ability_fire_contract import WEAPONS
from . import weapon_ability_fire_mixin as firing
from .weapon_lethal_network_contract import require, validate


class Network(Lethal):
    def __init__(self, result, peer, run):
        attacker=next((value.split('=',1)[1] for value in sys.argv if value.startswith('-UEPWeaponLethalAttacker=')), 'A')
        super().__init__(result, peer, run, attacker=attacker)
        self.report.update(fixture_damage_spec_applied=False, native_weapon_damage_observed=False,
            weapon_input_released=False, weapon_profile_classes_restored=False, weapon_owner_schema=2)
        self.weapon_boot_roots=[]
        for path in (firing.CLASS, WEAPONS['pistol']):
            cls=ue.load_class(path)
            if not cls.is_rooted():cls.add_to_root();self.weapon_boot_roots.append(cls)
            if 'PythonMixinProfile' in cls.get_cdo().properties():
                self.boot_selectors.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
                cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.weapon_sources={};self.weapon_profiles=[];self.weapon_events=[];self.weapon_data=[];self.foreign_weapon_events=[]
        self.actions=[];self.gestures=0;self.pressed=False;self.last_shot=0.;self.pose_attempt=0

    def arm(self):
        super().arm()
        self.weapon_cls=ue.load_class(firing.CLASS)
        ue.register_declared_mixin(self.weapon_cls)
        row,=[row for row in ue.get_registered_mixins() if row['target_class']==self.weapon_cls]
        self.weapon_sources={name:value['python_class'] for name,value in row['profiles'].items()}
        owner=self
        for profile,base in self.weapon_sources.items():
            def activate(handler, selected):
                def invoke(ability):
                    source=identity(ability.call_function('GetAvatarActorFromActorInfo'))
                    watched=owner.armed and source==owner.roster[owner.attacker]['pawn_wire']
                    if owner.armed and source==owner.roster[owner.victim]['pawn_wire']:owner.foreign_weapon_events.append(dict(profile=selected,source_wire=source))
                    if watched:owner.weapon_events.append(dict(profile=selected,authority=bool(ability.call_function('K2_HasAuthority')),source_wire=source))
                    return handler(ability)
                invoke.override='K2_ActivateAbility';return invoke
            def target(handler, selected):
                def invoke(ability,TargetData):
                    source=identity(ability.call_function('GetAvatarActorFromActorInfo'))
                    watched=owner.armed and source==owner.roster[owner.attacker]['pawn_wire']
                    if watched:
                        count=int(lib('AbilitySystemBlueprintLibrary').call_function('GetDataCountFromTargetData',TargetData))
                        hits=[break_hit(lib('AbilitySystemBlueprintLibrary').call_function('GetHitResultFromTargetData',TargetData,index)) for index in range(count)]
                        event=dict(profile=selected,authority=bool(ability.call_function('K2_HasAuthority')),source_wire=source,target_hits=sum(identity(hit['HitActor'])==owner.roster[owner.victim]['pawn_wire'] for hit in hits))
                    result=handler(ability,TargetData)
                    if watched:owner.weapon_data.append(event)
                    return result
                invoke.override='OnRangedWeaponTargetDataReady';return invoke
            attrs={name:value for name,value in vars(base).items() if not name.startswith('__')}
            attrs['Activate']=activate(base.Activate,profile);attrs['TargetData']=target(base.TargetData,profile)
            ue.register_mixin_profile(self.weapon_cls,profile,type('ObservedNaturalLethalWeapon'+self.peer+profile,(),attrs))
        if self.peer in ('server',self.attacker):
            self.source_pawn=self.players[self.attacker]['pawn']
            self.source_controller=self.players[self.attacker].get('controller',self.controller if self.peer==self.attacker else None)
            self.weapon_item=services(self.source_controller)[1].call_function('GetActiveSlotItem')
            self.ammo_before=ammo.ammo(self.weapon_item)[0]
            require(self.ammo_before>=5 and 'ID_Pistol' in capture(self.source_controller)['definition'],'actual original pistol inventory required')
            ability=ability_for(self.source_pawn,ue.load_class(WEAPONS['pistol']));require(valid(ability),'native equipped pistol ability missing')
            self.weapon_profiles.append((ability,str(ue.get_mixin_profile(ability))));ue.set_mixin_profile(ability,self.profile)
        if self.peer in ('server',self.victim):
            foreign_controller=self.players[self.victim]['controller'] if self.peer=='server' else self.controller
            self.foreign_item=services(foreign_controller)[1].call_function('GetActiveSlotItem')
            require(valid(self.foreign_item), 'other owner native inventory missing')
            self.foreign_ammo_before=ammo.ammo(self.foreign_item)[0]
        if self.peer=='server':
            self.original_poses={peer:(value['pawn'].get_actor_location(),value['pawn'].get_actor_rotation()) for peer,value in self.players.items()}
            self.place_target()
        elif self.peer==self.attacker:
            self.original_control=self.controller.call_function('GetControlRotation')
            self.actions=[ue.load_object(ue.find_class('InputAction'),'/Game/Input/Actions/'+name+'.'+name) for name in ('IA_Weapon_Fire','IA_Weapon_Fire_Auto')]
            self.aim_started=time.monotonic();self.clear_line=False

    def place_target(self):
        source=self.players[self.attacker]['pawn'];victim=self.players[self.victim]['pawn'];location=source.get_actor_location();forward=source.call_function('GetActorForwardVector')
        while self.pose_attempt<16:
            angle=math.radians(45.*(self.pose_attempt%8));distance=350. if self.pose_attempt<8 else 450.
            x=forward.x*math.cos(angle)-forward.y*math.sin(angle);y=forward.x*math.sin(angle)+forward.y*math.cos(angle)
            destination=ue.FVector(location.x+x*distance,location.y+y*distance,location.z)
            if victim.call_function('K2_TeleportTo',destination,victim.get_actor_rotation()):
                victim.call_function('ForceNetUpdate');self.pose_position=[float(destination.x),float(destination.y),float(destination.z)]
                atomic_write(self.root/'weapon-placement.json',dict(run_id=self.run,attempt=self.pose_attempt,position=self.pose_position));return
            self.pose_attempt+=1
        raise RuntimeError('bounded clear native weapon target placements exhausted')

    def apply_lethal(self):
        self.fired_at=time.monotonic()
        atomic_write(self.root/'native-lethal-fired.json',dict(run_id=self.run))

    def inject(self, pressed):
        for action in self.actions:self.controller.inject_enhanced_input_for_action(action,pressed)
        self.pressed=pressed

    def drive_weapon(self):
        if self.peer!=self.attacker or self.stage!='observe' or not self.token('native-lethal-fired.json'):return
        if self.pressed:self.inject(False);return
        victim=self.players[self.victim]['state'].call_function('GetPawn')
        if self.attribute_health(self.players[self.victim]['state'])<=0. or not valid(victim):return
        camera=self.controller.get_property('PlayerCameraManager');point=victim.get_property('Mesh').call_function('GetSocketLocation','spine_03')
        self.controller.call_function('SetControlRotation',lib('KismetMathLibrary').call_function('FindLookAtRotation',camera.call_function('GetCameraLocation'),point))
        placement=self.token('weapon-placement.json')
        position=victim.get_actor_location()
        settled=placement and math.dist([float(position.x),float(position.y),float(position.z)],placement['position'])<3.
        self.clear_line=bool(settled) and line_of_sight(self.source_pawn,camera.call_function('GetCameraLocation'),point,victim)
        if time.monotonic()-self.aim_started<.6:return
        if not self.clear_line:
            atomic_write(self.root/'weapon-aim-blocked.json',dict(run_id=self.run,attempt=placement['attempt'] if placement else -1));return
        if time.monotonic()-self.last_shot<.45:return
        require(self.gestures<self.ammo_before,'original native pistol magazine exhausted without lethal target damage')
        self.inject(True);self.gestures+=1;self.last_shot=time.monotonic()

    def record(self):
        row=super().record()
        row['foreign_weapon_activation_entries']=len(self.foreign_weapon_events)
        if self.peer in ('server',self.victim):
            row['foreign_weapon_ammo']=dict(before=self.foreign_ammo_before,after=ammo.ammo(self.foreign_item)[0])
        if self.peer in ('server',self.attacker):
            self.report['native_weapon_damage_observed']=bool(self.weapon_data) and any(event['target_hits']>0 for event in self.weapon_data)
            row['weapon']=dict(native_pistol_definition='ID_Pistol' in capture(self.source_controller)['definition'],ammo_before=self.ammo_before,
                ammo_after=ammo.ammo(self.weapon_item)[0],activation_entries=len(self.weapon_events),target_data_entries=len(self.weapon_data),
                target_hits=sum(event['target_hits'] for event in self.weapon_data),only_requested_weapon_profile=all(event['profile']==self.profile for event in self.weapon_events+self.weapon_data),
                input_gestures=self.gestures,input_entry='PlayerController.inject_enhanced_input_for_action',native_clear_line_of_sight=getattr(self,'clear_line',True),
                native_activation_events=copy.deepcopy(self.weapon_events),native_target_data_events=copy.deepcopy(self.weapon_data))
        return row

    def server_tick(self):
        if self.stage=='observe' and not self.weapon_data:
            blocked=self.token('weapon-aim-blocked.json')
            if blocked and blocked['attempt']==self.pose_attempt:
                self.pose_attempt+=1;self.place_target()
        super().server_tick()

    def client_tick(self):
        self.drive_weapon();super().client_tick()

    def cleanup(self):
        if getattr(self,'cleanup_done',False):return
        self.armed=False
        if self.actions:self.inject(False)
        if self.peer==self.attacker and hasattr(self,'original_control'):self.controller.call_function('SetControlRotation',self.original_control)
        for ability,profile in self.weapon_profiles:
            if valid(ability):ue.set_mixin_profile(ability,profile)
        if self.weapon_sources:
            for profile,source in self.weapon_sources.items():ue.register_mixin_profile(self.weapon_cls,profile,source)
        if self.peer=='server' and hasattr(self,'weapon_item'):
            set_stat(self.weapon_item,ammo.MAGAZINE,self.ammo_before)
            for peer,(location,rotation) in self.original_poses.items():
                state=self.players[peer]['state']
                if not valid(state):continue
                pawn=state.call_function('GetPawn')
                if valid(pawn) and identity(pawn)==self.roster[peer]['pawn_wire']:pawn.call_function('K2_TeleportTo',location,rotation)
        self.report['weapon_input_released']=not self.pressed
        self.report['weapon_profile_classes_restored']=not self.weapon_sources or all(next(row for row in ue.get_registered_mixins() if row['target_class']==self.weapon_cls)['profiles'][profile]['python_class'] is source for profile,source in self.weapon_sources.items())
        super().cleanup()
        for cls in self.weapon_boot_roots:cls.remove_from_root()
        self.report['weapon_profile_classes_restored']=self.report['weapon_profile_classes_restored'] and all(not cls.is_rooted() for cls in self.weapon_boot_roots)

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_WEAPON_LETHAL_NETWORK_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_WEAPON_LETHAL_NETWORK_SHUTDOWN_'+self.report['status'].upper())


if any(value.startswith('-UEPWeaponLethalNetworkResult=') for value in sys.argv):
    validation=Network(arg('UEPWeaponLethalNetworkResult'),arg('UEPTDMNetworkPeer'),arg('UEPTDMNetworkRun'));atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
