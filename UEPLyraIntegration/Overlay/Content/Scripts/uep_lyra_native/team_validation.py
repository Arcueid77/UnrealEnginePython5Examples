"""Natural two/four-team setup followed by explicit reversible player-state fixtures."""
import atexit
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .message_validation import arg
from . import team_creation as policy
from .team_validation_contract import require,validate


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeTeamResult'));self.profile=arg('UEPNativeTeamProfile');self.family=arg('UEPNativeTeamFamily')
        self.started=time.monotonic();self.finished=False;self.saved=[];self.scope=None;self.receipts=[];self.component=None;self.extra_states=[];self.natural_before_fixture=None
        self.report=dict(status='running',error=None,profile=self.profile,family=self.family,world_mode='Standalone',cases=[],
            native_teams_or_experience_callbacks_replaced=False,network_acceptance=False,packaged_acceptance=False)
        for path in policy.CLASSES:
            cls=ue.load_class(path);ue.register_declared_mixin(cls);self.saved.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
            cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        atexit.register(self.finalize)

    def snapshot(self):return [dict(team=int(p.call_function('GetTeamId')),inactive=bool(p.get_property('bIsInactive')),spectator=bool(p.get_property('bOnlySpectator'))) for p in self.players]
    def set_team(self,index,team):self.component.call_function('UEPSetPlayerTeam',self.players[index],team)
    def least(self):return int(self.component.call_function(policy.LEAST))
    def choose(self,index):self.component.call_function(policy.CHOOSE,self.players[index]);return int(self.players[index].call_function('GetTeamId'))

    def setup(self):
        fragment='L_Expanse' if self.family=='Two' else 'L_TopDown'
        cls=ue.load_class(policy.CLASSES[0 if self.family=='Two' else 1])
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or fragment not in world.get_name():continue
            state=policy.lib('GameplayStatics').call_function('GetGameState',world)
            if not valid(state):continue
            components=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==world and c.call_function('GetOwner')==state]
            if len(components)!=1:continue
            players=[p for p in state.get_property('PlayerArray') if valid(p) and p.is_a(ue.find_class('LyraPlayerState'))]
            if self.family=='Four' and players and all(int(p.call_function('GetTeamId'))!=-1 for p in players) and len(players)<4 and not self.extra_states:
                self.natural_before_fixture=copy.deepcopy(policy.metrics(components[0]))
                for _ in range(4-len(players)):
                    player=world.actor_spawn(ue.find_class('LyraPlayerState'),ue.FVector(400000.,400000.,3000.))
                    require(valid(player),'native temporary PlayerState creation failed');self.extra_states.append(player)
                    components[0].call_function(policy.CHOOSE,player)
                self.report['temporary_player_states_created']=len(self.extra_states)
                self.report['four_team_fixture_scope']='One natural local owner; three temporary native PlayerState actors exercise the configured production component. No four-owner network claim.'
                return False
            if len(players)<4 or any(int(p.call_function('GetTeamId'))==-1 for p in players):continue
            self.world=world;self.component=components[0];self.players=sorted(players,key=lambda p:(int(p.call_function('GetPlayerId')),p.get_path_name()))
            self.subsystem=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',world,ue.find_class('LyraTeamSubsystem'))
            self.original_map=dict(self.component.get_property('TeamsToCreate'));self.original_players=self.snapshot()
            self.ids=sorted(self.original_map)
            self.report['natural_metrics']=self.natural_before_fixture or copy.deepcopy(policy.metrics(self.component))
            self.report['natural_component_count']=len(components)
            self.report['configured_teams']={str(k):v.get_path_name() if v is not None else None for k,v in self.original_map.items()}
            self.report['natural_team_counts']={str(team):sum(p['team']==team and not p['inactive'] for p in self.original_players) for team in self.original_map}
            self.report['isolated_bots']=isolate_bots(policy.lib('GameplayStatics'),world,ue.find_class('AIController'))
            self.scope=SubscriptionScope()
            for index,player in enumerate(self.players):
                def changed(obj,old,new,i=index):
                    require(obj==self.players[i],'native team notification source differs');self.receipts.append([i,int(old),int(new)])
                self.scope.bind_event(player,'OnTeamChangedDelegate',changed)
            return True
        return False

    def case(self,name,index=None,query=True):
        self.report['pending_case']=name;self.report['fixture_inputs']=dict(teams=sorted(self.component.get_property('TeamsToCreate')),players=self.snapshot())
        atomic_write(self.path,self.report)
        self.receipts=[];before=copy.deepcopy(policy.metrics(self.component));least=self.least() if query else None
        chosen=self.choose(index) if index is not None else None
        after=policy.metrics(self.component);prefix='python_' if self.profile=='Python' else 'native_'
        row=dict(name=name,least=least,chosen=chosen,events=copy.deepcopy(self.receipts),players=self.snapshot(),least_calls=after[prefix+'least']-before[prefix+'least'])
        self.report['cases'].append(row)

    def reset(self):
        for i,p in enumerate(self.players):
            p.set_property('bIsInactive',False);p.set_property('bOnlySpectator',False);self.set_team(i,-1)

    def execute(self):
        self.reset();self.case('tie',0);self.case('smaller',1)
        self.players[0].set_property('bIsInactive',True);self.case('inactive',2)
        self.players[0].set_property('bIsInactive',False);self.players[0].set_property('bOnlySpectator',True);self.set_team(0,self.ids[1])
        self.case('spectator',0,False)
        four=ue.load_class(policy.CLASSES[1]).get_cdo().get_property('TeamsToCreate')
        self.report['four_team_ids']=sorted(four)
        self.component.set_property('TeamsToCreate',dict(four));self.reset();self.set_team(0,self.report['four_team_ids'][0]);self.set_team(1,self.report['four_team_ids'][1]);self.case('four_teams')
        self.component.set_property('TeamsToCreate',{});self.set_team(3,self.ids[1]);self.case('empty',3)
        self.report['metrics']=copy.deepcopy(policy.metrics(self.component))

    def cleanup(self):
        if self.scope:self.scope.close();self.scope.close();self.report['observer_scope_closed']=self.scope.closed and self.scope.count==0
        if self.component:
            self.component.set_property('TeamsToCreate',self.original_map)
            for i,row in enumerate(self.original_players):
                self.players[i].set_property('bIsInactive',row['inactive']);self.players[i].set_property('bOnlySpectator',row['spectator']);self.set_team(i,row['team'])
            self.report['fixture_state_restored']=self.snapshot()==self.original_players
            self.report['team_configuration_restored']=self.component.get_property('TeamsToCreate')==self.original_map
        for cls,previous in self.saved:cls.get_cdo().set_property('PythonMixinProfile',previous)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==previous for cls,previous in self.saved)
        for player in self.extra_states:
            if valid(player):player.call_function('K2_DestroyActor')
        self.report['temporary_player_states_removed']=all(not valid(p) for p in self.extra_states)

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,'natural team setup timed out')
            if not self.setup():return True
            self.execute();self.finish();return False
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_TEAM_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_TEAM_SHUTDOWN_'+self.report['status'].upper())


if any(v.startswith('-UEPNativeTeamResult=') for v in __import__('sys').argv):
    validation=Validation();ticker=ue.add_ticker(validation.tick)
