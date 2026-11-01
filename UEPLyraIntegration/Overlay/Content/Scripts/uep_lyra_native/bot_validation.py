"""Actual production components spawn/destroy bots; only policy inputs are fixtures."""
import atexit
import copy
from pathlib import Path
import re
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .message_validation import arg
from . import bot_creation as policy
from .bot_validation_contract import require,validate


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeBotResult'));self.profile=arg('UEPNativeBotProfile');self.family=arg('UEPNativeBotFamily')
        self.started=time.monotonic();self.finished=False;self.saved=[];self.component=None;self.scope=None;self.deaths=[]
        self.report=dict(status='running',error=None,profile=self.profile,family=self.family,cases=[],removals=[],
            global_rng_replaced=False,health_attribute_writes=False,score_stat_writes=False,native_spawn_or_destroy_replaced=False,
            editor_pie_override_acceptance=False,exact_rng_sequence_claim=False,network_acceptance=False)
        for path in policy.CLASSES:
            cls=ue.load_class(path);ue.register_declared_mixin(cls);self.saved.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        atexit.register(self.finalize)

    def bots(self):return list(self.component.get_property('SpawnedBotList'))
    def names(self,bots):return [str(c.PlayerState.call_function('GetPlayerName')) for c in bots]

    def setup(self):
        fragment='L_Expanse' if self.family=='TDM' else 'L_Convolution'
        cls=ue.load_class(policy.CLASSES[0 if self.family=='TDM' else 1])
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or fragment not in world.get_name():continue
            isolate_bots(policy.lib('GameplayStatics'),world,ue.find_class('AIController'))
            components=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==world and valid(c.call_function('GetOwner'))]
            if len(components)!=1:continue
            bots=list(components[0].get_property('SpawnedBotList'))
            if len(bots)!=3 or any(not valid(c) or not valid(c.PlayerState) or not valid(c.get_controlled_pawn()) for c in bots):continue
            self.world=world;self.component=components[0];self.mode=policy.lib('GameplayStatics').call_function('GetGameMode',world)
            self.original={name:self.component.get_property(name) for name in ('NumBotsToCreate','BotControllerClass','RandomBotNames')}
            self.original_options=str(self.mode.get_property('OptionsString'))
            self.report.update(natural_component_count=1,natural_bot_count=len(bots),natural_names=self.names(bots),natural_metrics=copy.deepcopy(policy.metrics(self.component)),native_editor_context=bool(self.component.call_function('UEPIsEditorBotContext')))
            self.scope=SubscriptionScope();return True
        return False

    def options(self,count):
        value=re.sub(r'\?NumBots=[^?]*','',self.original_options,flags=re.I)
        if count is not None:value+='?NumBots='+str(count)
        self.mode.set_property('OptionsString',value)

    def create(self,name,expected):
        before=self.bots();self.report['pending_case']=name;atomic_write(self.path,self.report)
        self.component.call_function('ServerCreateBots');after=self.bots();added=[c for c in after if c not in before]
        isolate_bots(policy.lib('GameplayStatics'),self.world,ue.find_class('AIController'))
        require(len(added)==expected,'native spawn cardinality differs: '+name)
        self.report['cases'].append(dict(name=name,added=len(added),names=self.names(added)))

    def execute(self):
        self.component.set_property('BotControllerClass',None);self.create('no_controller',0)
        self.component.set_property('BotControllerClass',self.original['BotControllerClass'])
        self.component.set_property('NumBotsToCreate',2);self.component.set_property('RandomBotNames',['UEPFixture-A','UEPFixture-B']);self.options(None);self.create('default',2)
        self.component.set_property('NumBotsToCreate',5);self.component.set_property('RandomBotNames',['UEPFixture-Only']);self.options(1);self.create('url_one',1)
        self.options(0);self.create('url_zero',0);self.options(-1);self.create('url_negative',0)
        self.component.set_property('RandomBotNames',['UEPFixture-First','UEPFixture-Second']);self.options(3);self.create('name_exhaustion',3)
        for controller in self.bots():
            health=controller.get_controlled_pawn().get_component_by_type(ue.find_class('LyraHealthComponent'))
            require(valid(health),'production bot health component absent')
            self.scope.bind_event(health,'OnDeathStarted',lambda actor:self.deaths.append(actor.get_path_name()))
        while self.bots():
            before=self.bots();self.report['pending_case']='native_remove';atomic_write(self.path,self.report)
            self.component.call_function('RemoveOneBot');after=self.bots();removed=[c for c in before if c not in after]
            self.report['removals'].append(dict(before=len(before),after=len(after),removed_controllers=sum(not valid(c) for c in removed)))
        count=copy.deepcopy(policy.metrics(self.component));self.component.call_function('RemoveOneBot')
        self.report['empty_remove_did_not_select']=policy.metrics(self.component)==count
        # Reset to a nonempty name pool without creating an actor, then prove
        # actual native EndPlay invokes the production Python teardown.
        self.component.set_property('RandomBotNames',['Teardown-A','Teardown-B']);self.options(0);self.component.call_function('ServerCreateBots')
        self.report['python_names_before_teardown']=len(policy.remaining(self.component))
        self.report['native_death_callbacks']=len(self.deaths);self.report['metrics']=copy.deepcopy(policy.metrics(self.component))

    def cleanup(self):
        if self.scope:self.scope.close();self.scope.close();self.report['observer_scope_closed']=self.scope.closed and self.scope.count==0
        if self.component:
            for name,value in self.original.items():self.component.set_property(name,value)
            self.mode.set_property('OptionsString',self.original_options)
            self.report['configuration_restored']=all(self.component.get_property(n)==v for n,v in self.original.items()) and self.mode.get_property('OptionsString')==self.original_options
            names=policy.remaining(self.component)
            self.component.call_function('K2_DestroyComponent',self.component.call_function('GetOwner'))
            self.report['native_component_destroyed']=not valid(self.component)
            self.report['python_names_cleared']=not names
        for cls,previous in self.saved:cls.get_cdo().set_property('PythonMixinProfile',previous)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==previous for cls,previous in self.saved)

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,'natural bot creation timed out')
            if not self.setup():return True
            self.execute();self.finish();return False
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_BOT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_BOT_SHUTDOWN_'+self.report['status'].upper())


if any(v.startswith('-UEPNativeBotResult=') for v in __import__('sys').argv):
    validation=Validation();ticker=ue.add_ticker(validation.tick)
