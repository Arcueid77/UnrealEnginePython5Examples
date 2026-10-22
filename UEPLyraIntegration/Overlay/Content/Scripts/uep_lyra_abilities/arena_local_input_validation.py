"""Opt-in real Arena local-player input/cost/instigator isolation observation.

Create the second local player through the native service. Use its naturally
granted ability and original input action; retain real spawn locations. Test
bombs are destroyed before their fuse to isolate input/ownership from damage.
"""
import atexit,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world import arena_bomb_base_mixin as base
from uep_lyra_world import arena_bomb_visual_mixin as visual
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import arena_drop_bomb_mixin as drop
from .arena_local_input_contract import validate


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def path(value):return value.get_path_name() if valid(value) else None
def dead(value):return not valid(value) or value.call_function('IsActorBeingDestroyed')


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPArenaLocalInputResult'));self.profile=arg('UEPArenaLocalInputProfile')
        self.started=time.monotonic();self.phase='world';self.finished=False;self.created=None
        self.roots=[];self.selectors=[];self.players=[];self.bombs_owned=[];self.index=0
        self.report=dict(status='running',error=None,profile=self.profile,cases=[],input_entry='PlayerController.inject_enhanced_input_for_action',test_bombs_destroyed_before_fuse=True,natural_explosion_tested=False)
        for key in ('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written','pawn_position_written','physical_input_tested','network_acceptance','packaged_runtime','full_acceptance'):self.report[key]=False
        self.classes={k:ue.load_class(p) for k,p in dict(drop=drop.CLASS,base=base.CLASS,visual=visual.CLASS).items()}
        for key,cls in self.classes.items():
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            selectors=(base.SELECTOR,) if key=='base' else ('PythonMixinProfile',base.SELECTOR) if key=='visual' else ('PythonMixinProfile',)
            for selector in selectors:
                self.selectors.append((cls,selector,cls.get_cdo().get_property(selector)))
                cls.get_cdo().set_property(selector,self.profile)
        self.attributes=ue.load_class('/Game/UEPValidation/BP_ArenaBombBaseProbe.BP_ArenaBombBaseProbe_C')
        if not self.attributes.is_rooted():self.attributes.add_to_root();self.roots.append(self.attributes)
        self.attributes=self.attributes.get_cdo();self.statics=drop.lib('GameplayStatics')

    def require(self,value,message):
        if not value:raise AssertionError(message)

    def enter(self,phase):self.phase=phase;self.since=time.monotonic();self.report['phase']=phase
    def remaining(self):
        values=[]
        for player in self.players:
            value,found=self.attributes.call_function('ReadBombsRemaining',player['state'])
            self.require(found,'original Arena BombsRemaining attribute missing');values.append(float(value))
        return values

    def health(self):
        return [float(p['pawn'].get_component_by_type(ue.find_class('LyraHealthComponent')).call_function('GetHealth')) for p in self.players]

    def bombs(self):
        result=self.statics.call_function('GetAllActorsOfClass',self.world,self.classes['base'])
        return set(native_outputs('GameplayStatics','GetAllActorsOfClass',result)['OutActors'])

    def discover_world(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or world.get_name()!='L_TopDown_LocalMultiplayer':continue
            phase=drop.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',world,ue.find_class('LyraGamePhaseSubsystem'))
            controller=self.statics.call_function('GetPlayerController',world,0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()) or not phase.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.Playing')):continue
            self.world=world
            self.require(not valid(self.statics.call_function('GetPlayerController',world,1)),'fresh lane requires one initial local player')
            # A real second device would establish its Slate user before joining.
            # Use an unhandled NUL character for that native process-local setup;
            # the gameplay tests still enter the original Enhanced Input action.
            handled=ue.FSlateApplication.process_key_char_event(ue.FCharacterEvent('',False,ue.FModifierKeysState(),1))
            self.require(not handled,'neutral Slate bootstrap unexpectedly handled input')
            self.report['synthetic_slate_user_bootstrap']='unhandled NUL character for user index 1 before native CreatePlayer'
            self.created=self.statics.call_function('CreatePlayer',world,-1,True)
            self.require(valid(self.created),'native CreatePlayer did not create second local player')
            bridge=drop.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            self.report.update(map=world.get_name(),native_mode=str(bridge.call_function('CaptureSnapshot').NetMode),local_player_creation='GameplayStatics.CreatePlayer')
            self.enter('players');return

    def discover_players(self):
        players=[]
        for index in (0,1):
            controller=self.statics.call_function('GetPlayerController',self.world,index)
            pawn=controller.get_controlled_pawn() if valid(controller) else None
            if not valid(pawn) or not valid(ability_system(pawn)):return
            state=pawn.get_property('PlayerState');asc=ability_system(pawn)
            spec=next((s for s in asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(self.classes['drop'])),None)
            if spec is None:return
            data=state.get_property('PawnData');config=data.get_property('InputConfig')
            granted=[a for ability_set in data.get_property('AbilitySets') for a in ability_set.get_property('GrantedGameplayAbilities') if a.Ability==self.classes['drop']]
            self.require(len(granted)==1,'original PawnData does not grant exactly one Arena drop ability')
            tag=str(granted[0].InputTag.TagName)
            action=config.call_function('FindAbilityInputActionForTag',GameplayTag(TagName=tag),True)
            self.require(valid(action),'original input config has no drop ability action')
            players.append(dict(controller=controller,pawn=pawn,state=state,asc=asc,action=action,tag=tag,ability=spec.Ability))
        self.players=players
        self.require(players[0]['controller'].get_property('Player')!=players[1]['controller'].get_property('Player') and players[0]['state']!=players[1]['state'] and players[0]['asc']!=players[1]['asc'],'two distinct real local-player owners required')
        self.initial_health=self.health();self.require(all(v>0 for v in self.initial_health),'players must start alive')
        self.require(self.remaining()==[1.,1.],'original Arena one-bomb cost expected')
        self.report.update(local_players=2,distinct_player_owners=True,ability_granted_by_original_experience=True,input_action_from_original_pawn_data=True,owners=[dict(controller=path(p['controller']),player_state=path(p['state']),pawn=path(p['pawn']),input_action=path(p['action']),input_tag=p['tag']) for p in players])
        self.enter('settle')

    def press(self,value):
        p=self.players[self.index];p['controller'].inject_enhanced_input_for_action(p['action'],value)

    def abilities(self,index):
        asc=self.players[index]['asc'];spec=next(s for s in asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(self.classes['drop']))
        return [spec.Ability]+list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances)

    def counts(self,index):
        rows=[drop.evidence(a) for a in self.abilities(index) if valid(a)]
        return {k:sum(row[k] for row in rows) for k in rows[0]}

    def start_case(self):
        self.before_bombs=self.bombs();self.before_counts=self.counts(self.index)
        self.current=dict(owner=self.index,remaining_before=self.remaining())
        self.frames=0;self.enter('press')

    def observe_spawn(self):
        created=self.bombs()-self.before_bombs
        if not created:
            self.require(time.monotonic()-self.since<3.,'native enhanced input did not spawn a bomb');return
        self.require(len(created)==1,'one input spawned multiple bombs');self.bomb,=created;self.bombs_owned.append(self.bomb)
        prefix='python_' if self.profile=='Python' else 'fallback_'
        self.current.update(new_bombs=1,instigator_matches_owner=self.bomb.get_property('Instigator')==self.players[self.index]['pawn'],saved_state_matches_owner=self.bomb.get_property('InstigatingPlayerState')==self.players[self.index]['state'],remaining_after=self.remaining(),bomb_profiles_match=str(ue.get_mixin_profile(self.bomb))==self.profile and self.bomb.get_property(base.SELECTOR)==self.profile and base.evidence(self.bomb)[prefix+'begin']==1 and visual.evidence(self.bomb)[prefix+'construct']==1)
        self.current['foreign_owner_unchanged']=self.current['remaining_after'][1-self.index]==self.current['remaining_before'][1-self.index]
        self.frames=0;self.enter('repeat')

    def observe_repeat(self):
        self.current.update(repeat_input_new_bombs=len(self.bombs()-self.before_bombs)-1,repeat_input_keeps_cost=self.remaining())
        counts=self.counts(self.index);chosen='python_' if self.profile=='Python' else 'fallback_';other='fallback_' if chosen=='python_' else 'python_'
        self.current.update(selected_profile_callbacks=sum(counts[k]-self.before_counts[k] for k in counts if k.startswith(chosen)),other_profile_callbacks=sum(counts[k]-self.before_counts[k] for k in counts if k.startswith(other)))
        self.require(not dead(self.bomb),'test bomb reached fuse before controlled cleanup')
        self.bomb.call_function('K2_DestroyActor');self.enter('refund')

    def observe_refund(self):
        if self.remaining()!=[1.,1.]:
            self.require(time.monotonic()-self.since<2.,'native bomb destruction did not refund original owner');return
        self.current['native_destroy_refund']=self.remaining();self.report['cases'].append(self.current)
        if self.index==0:self.index=1;self.enter('settle')
        else:self.finish()

    def cleanup(self):
        for p in self.players:p['controller'].inject_enhanced_input_for_action(p['action'],False)
        for bomb in self.bombs_owned:
            if not dead(bomb):bomb.call_function('K2_DestroyActor')
        self.report['health_unchanged']=not self.players or self.health()==self.initial_health
        if valid(self.created):self.statics.call_function('RemovePlayer',self.created,True)
        self.report['native_local_player_removed']=not hasattr(self,'world') or not valid(self.statics.call_function('GetPlayerController',self.world,1))
        for cls,selector,value in self.selectors:cls.get_cdo().set_property(selector,value)
        for cls in self.roots:
            if cls.is_valid() and cls.is_rooted():cls.remove_from_root()
        self.report['cleanup_complete']=all(dead(b) for b in self.bombs_owned) and all(cls.get_cdo().get_property(selector)==value for cls,selector,value in self.selectors) and all(not cls.is_rooted() for cls in self.roots)

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_ARENA_LOCAL_INPUT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_LOCAL_INPUT_SHUTDOWN_'+self.report['status'].upper())

    def tick(self,delta):
        try:
            self.require(time.monotonic()-self.started<180.,'Arena local input timed out in '+self.phase)
            if self.phase=='world':self.discover_world()
            elif self.phase=='players':self.discover_players()
            elif self.phase=='settle':
                if time.monotonic()-self.since>=1.:self.start_case()
            elif self.phase in ('press','repeat'):
                self.press(self.frames<3);self.frames+=1
                if self.frames>=6:self.enter('spawn' if self.phase=='press' else 'repeat-observe')
            elif self.phase=='spawn':self.observe_spawn()
            elif self.phase=='repeat-observe':self.observe_repeat()
            elif self.phase=='refund':self.observe_refund()
            atomic_write(self.path,self.report)
        except Exception:self.finish(traceback.format_exc())
        return not self.finished


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
