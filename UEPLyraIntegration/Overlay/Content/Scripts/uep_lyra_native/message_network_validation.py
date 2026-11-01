"""Native GAS damage produces all messages; production relays reach actual peers."""
import atexit
import copy
import faulthandler
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_hud.notification_relays_network_validation import Network as Relays,identity,tags
from uep_lyra_weapons.tdm_lethal_network_validation import Network as Lethal
from . import message_processors as policy
from .message_validation import arg
from .message_network_contract import EXPECTED,validate,require

DAMAGE='/Game/GameplayEffects/Damage/GE_Damage_Basic_SetByCaller.GE_Damage_Basic_SetByCaller_C'


class Network(Relays):
    attribute_health=Lethal.attribute_health

    def __init__(self):
        super().__init__(arg('UEPNativeMessageNetworkResult'),arg('UEPNativeMessageNetworkPeer'),arg('UEPNativeMessageNetworkRun'))
        self.watchdog=(self.root/(self.peer+'-python-stack.log')).open('w',encoding='utf-8')
        faulthandler.dump_traceback_later(30,repeat=True,file=self.watchdog)
        self.profile=arg('UEPNativeMessageNetworkProfile');require(self.profile in ('Python','NativeFallback'),'explicit native profile required')
        self.boot=[];self.native_components={};self.native_events=[];self.native_deaths=[];self.applied=[];self.next_isolation=0.
        self.report=dict(status='running',error=None,peer=self.peer,run_id=self.run,profile=self.profile,
            actual_native_damage_spec_applied=False,synthetic_verb_messages=False,health_attribute_writes=False,
            score_stat_writes=False,damage_immunity_writes=False,server_waited_for_client_process_exit=False)
        for path in policy.CLASSES.values():
            cls=ue.load_class(path);ue.register_declared_mixin(cls)
            self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
            cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.team_profile=next((v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPNativeTeamProfile=')),None)
        if self.team_profile is not None:
            from . import team_creation
            require(self.team_profile==self.profile,'paired native team/message profile required')
            for path in team_creation.CLASSES:
                cls=ue.load_class(path);ue.register_declared_mixin(cls)
                self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
                cls.get_cdo().set_property('PythonMixinProfile',self.team_profile)
            self.report.update(validate_team=True,team_profile=self.team_profile)
        self.bot_profile=next((v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPNativeBotProfile=')),None)
        if self.bot_profile is not None:
            from . import bot_creation
            require(self.bot_profile==self.profile,'paired native bot/message profile required')
            for path in bot_creation.CLASSES:
                cls=ue.load_class(path);ue.register_declared_mixin(cls)
                self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
                cls.get_cdo().set_property('PythonMixinProfile',self.bot_profile)
            self.report.update(validate_bots=True,bot_profile=self.bot_profile)
        self.spawning_profile=next((v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPNativeSpawnProfile=')),None)
        if self.spawning_profile is not None:
            from . import spawning
            require(self.spawning_profile==self.profile,'paired native spawning/message profile required')
            cls=ue.load_class(spawning.CLASS);ue.register_declared_mixin(cls)
            self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
            cls.get_cdo().set_property('PythonMixinProfile',self.spawning_profile)
            self.report.update(validate_spawning=True,spawning_profile=self.spawning_profile)
        atexit.register(self.finalize)

    def world_ready(self):
        # Stop native bot brains during normal startup, before owners finish
        # connecting. Never change health, immunity, teams, or score statistics.
        if self.peer=='server' and time.monotonic()>=self.next_isolation:
            self.next_isolation=time.monotonic()+.5
            for world in ue.all_worlds():
                if world.get_world_type() in (1,3,5) and 'L_Expanse' in world.get_name():
                    isolate_bots(self.statics,world,ue.find_class('AIController'))
        return super().world_ready()

    def setup(self):
        super().setup()
        counts={}
        for kind,path in policy.CLASSES.items():
            cls=ue.load_class(path)
            components=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==self.world and valid(c.call_function('GetOwner'))]
            counts[kind]=len(components)
            require(len(components)==(1 if self.peer=='server' else 0),'production authority processor role differs: '+kind)
            if components:
                self.native_components[kind]=components[0];ue.set_mixin_profile(components[0],self.profile)
        self.report['native_processor_counts']=counts
        if self.team_profile is not None:
            from . import team_creation
            cls=ue.load_class(team_creation.CLASSES[0])
            natural=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==self.world and c.call_function('GetOwner')==self.state]
            self.report['native_team_component_count']=len(natural)
            require(len(natural)==(1 if self.peer=='server' else 0),'natural team authority role differs')
            if natural:
                component=natural[0]
                require(str(ue.get_mixin_profile(component))==self.team_profile,'natural team profile differs')
                self.report['natural_team_metrics']=copy.deepcopy(team_creation.metrics(component))
                ids=component.get_property('TeamsToCreate')
                players=[p for p in self.state.get_property('PlayerArray') if valid(p) and p.is_a(ue.find_class('LyraPlayerState')) and not p.get_property('bIsInactive')]
                self.report['natural_team_populations']={str(team):sum(int(p.call_function('GetTeamId'))==team for p in players) for team in ids}
        if self.bot_profile is not None:
            from . import bot_creation
            cls=ue.load_class(bot_creation.CLASSES[0])
            natural=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==self.world and c.call_function('GetOwner')==self.state]
            self.report['native_bot_component_count']=len(natural)
            require(len(natural)==(1 if self.peer=='server' else 0),'natural bot authority role differs')
            if natural:
                self.report['natural_bot_metrics']=copy.deepcopy(bot_creation.metrics(natural[0]))
                self.report['natural_bot_count']=len(natural[0].get_property('SpawnedBotList'))
        if self.spawning_profile is not None:
            from . import spawning
            cls=ue.load_class(spawning.CLASS)
            natural=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==self.world and c.call_function('GetOwner')==self.state]
            self.report['native_spawning_component_count']=len(natural)
            require(len(natural)==(1 if self.peer=='server' else 0),'natural spawning authority role differs')
            if natural:self.report['natural_spawning_metrics']=copy.deepcopy(spawning.metrics(natural[0]))
        if self.peer=='server':
            self.report['isolated_bots']=isolate_bots(self.statics,self.world,ue.find_class('AIController'))
            scope=SubscriptionScope();self.scopes.append(scope)
            self.verb_adapter=ue.load_class(policy.ADAPTER).get_cdo()
            channels={'Lyra.Damage.Message','Lyra.Elimination.Message','Lyra.Assist.Message'}
            for kind,field in (('streak','ElimStreakTags'),('chain','ElimChainTags')):
                channels.update(str(t.TagName) for t in self.native_components[kind].get_property(field).values())
            def reader(proxy):
                value,ok=self.verb_adapter.call_function('ReadVerb',proxy);require(ok,'native damage/reward typed read failed');return value
            for channel in sorted(channels):scope.listen_gameplay_message(self.world,channel,ue.find_struct('LyraVerbMessage'),reader,self.on_native_message)

    def label(self,obj):
        if obj is None:return None
        ps=policy.player_from_object(obj)
        return next((role for role,data in self.players.items() if data['state']==ps),'other')

    def on_native_message(self,channel,p):
        if self.armed:self.native_events.append(dict(verb=str(p.Verb.TagName),instigator=self.label(p.Instigator),target=self.label(p.Target),
            magnitude=float(p.Magnitude),instigator_tags=tags(p.InstigatorTags),target_tags=tags(p.TargetTags),context_tags=tags(p.ContextTags)))

    def stats(self):
        def value(role,name):return int(self.players[role]['state'].call_function('GetStatTagStackCount',GameplayTag(TagName='ShooterGame.Score.'+name)))
        def team(role):return int(self.team.call_function('GetTeamTagStackCount',self.roster[role]['team'],GameplayTag(TagName='ShooterGame.Score.Eliminations')))
        return dict(kills=value('A','Eliminations'),deaths=value('B0','Deaths'),assists=value('helper','Assists'),team=team('A'),other=team('B0'))

    def bind_death(self):
        scope=SubscriptionScope();self.scopes.append(scope)
        health=self.players['B0']['pawn'].get_component_by_type(ue.find_class('LyraHealthComponent'))
        require(valid(health),'native victim HealthComponent required')
        scope.bind_event(health,'OnDeathStarted',lambda actor:self.native_deaths.append(identity(actor)))

    def arm(self):
        self.baseline_stats=self.stats();self.before={k:copy.deepcopy(policy.metrics(c)) for k,c in self.native_components.items()}
        self.entries=dict(kill=0,award=0);self.receipts=[];self.kill_messages=[];self.award_messages=[]
        require(self.attribute_health(self.players['A']['state'])==self.attribute_health(self.players['B0']['state'])==100.,'native human health not ready')
        self.bind_death();self.armed=True

    def roster_server(self):
        ready={p:self.token(p+'-ready.json') for p in ('A','B0')}
        if not all(ready.values()):return False
        controllers,=self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('LyraPlayerController'))
        self.roster={};self.players={}
        for peer,receipt in ready.items():
            controller=next((c for c in controllers if valid(c.PlayerState) and int(c.PlayerState.call_function('GetPlayerId'))==receipt['player_id']),None)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):return False
            state,pawn=controller.PlayerState,controller.get_controlled_pawn()
            self.roster[peer]=dict(player_id=receipt['player_id'],state_wire=identity(state),pawn_wire=identity(pawn),name=state.call_function('GetPlayerName'),team=self.team_id(pawn))
            self.players[peer]=dict(state=state,pawn=pawn)
        require(self.roster['A']['team']!=self.roster['B0']['team'],'two actual owners must be opposing native teams')
        bots,=self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('AIController'))
        helpers=[];victims=[]
        for controller in bots:
            state=controller.PlayerState;pawn=controller.get_controlled_pawn()
            if not valid(state) or not valid(pawn) or self.attribute_health(state)!=100.:continue
            (helpers if self.team_id(pawn)==self.roster['A']['team'] else victims).append((state,pawn))
        if len(helpers)<1 or len(victims)<4:return False
        for role,(state,pawn) in zip(('helper','enemy1','enemy2','enemy3','enemy4'),[helpers[0],*victims[:4]]):
            self.roster[role]=dict(state_wire=identity(state),pawn_wire=identity(pawn),team=self.team_id(pawn))
            self.players[role]=dict(state=state,pawn=pawn)
        self.arm();atomic_write(self.root/'native-rules-roster.json',dict(run_id=self.run,roster=self.roster));return True

    def resolve_client(self,roster):
        states=[p for p in self.world.all_actors() if valid(p) and p.is_a(ue.find_class('LyraPlayerState'))]
        players={}
        for role,row in roster.items():
            state=next((p for p in states if identity(p)==row['state_wire']),None)
            if not valid(state):return False
            pawn=state.call_function('GetPawn')
            if role in ('A','B0') and (not valid(pawn) or identity(pawn)!=row['pawn_wire'] or self.attribute_health(state)!=100.):return False
            players[role]=dict(state=state,pawn=pawn)
        self.roster=roster;self.players=players;self.arm();return True

    def apply_damage(self,source_role,target_role,amount):
        source=ability_system(self.players[source_role]['pawn']);target=ability_system(self.players[target_role]['pawn'])
        spec=source.call_function('MakeOutgoingSpec',ue.load_class(DAMAGE),1.,source.call_function('MakeEffectContext'))
        spec=policy.lib('AbilitySystemBlueprintLibrary').call_function('AssignTagSetByCallerMagnitude',spec,GameplayTag(TagName='SetByCaller.Damage'),amount)
        source.call_function('BP_ApplyGameplayEffectSpecToTarget',spec,target)
        self.applied.append(dict(source=source_role,target=target_role,amount=amount))

    def fire(self):
        self.apply_damage('helper','B0',25.);self.apply_damage('A','B0',75.)
        for i in range(1,5):self.apply_damage('A','enemy'+str(i),100.)
        self.report.update(actual_native_damage_spec_applied=True,applied_specs=self.applied)
        self.fired_at=time.monotonic();atomic_write(self.root/'native-rules-fired.json',dict(run_id=self.run))

    def record(self):
        stats=self.stats()
        return dict(stat_delta={k:stats[k]-self.baseline_stats[k] for k in stats},native_messages=self.native_events,
            kill_notifications=self.kill_messages,award_messages=self.award_messages,native_death_started=len(self.native_deaths))

    def server_tick(self):
        if self.stage=='roster':
            if self.roster_server():self.stage='armed'
        elif self.stage=='armed':
            if all(self.token(p+'-native-rules-armed.json') for p in ('A','B0')):self.fire();self.stage='observe'
        elif self.stage=='observe':
            row=self.record();self.report['pending_result']=row
            require(time.monotonic()-self.fired_at<15.,'actual native damage, rewards or client replication missing')
            if row['stat_delta']!=EXPECTED or not all(self.token(p+'-native-rules-observed.json') for p in ('A','B0')):return
            self.report['result']=row
            self.report['processor_metrics']={k:{n:v-self.before[k][n] for n,v in policy.metrics(c).items()} for k,c in self.native_components.items()}
            self.cleanup();self.report['status']='awaiting_release';atomic_write(self.root/'ready-server.json',dict(run_id=self.run));self.stage='release'
        elif self.stage=='release':
            release=self.token('server-release.json')
            if release:
                require(release['client_exit_codes']=={'A':0,'B0':0},'both real client exits required')
                self.report['server_waited_for_client_process_exit']=True;self.finish()

    def client_tick(self):
        if self.stage=='roster':
            token=self.token('native-rules-roster.json')
            if token and self.resolve_client(token['roster']):
                atomic_write(self.root/(self.peer+'-native-rules-armed.json'),dict(run_id=self.run));self.stage='observe'
        elif self.stage=='observe':
            if not self.token('native-rules-fired.json'):return
            if not hasattr(self,'fired_at'):self.fired_at=time.monotonic()
            row=self.record();self.report['pending_result']=row
            ready=row['stat_delta']==EXPECTED and len(row['kill_notifications'])==5 and len(row['award_messages'])==(4 if self.peer=='A' else 0)
            require(time.monotonic()-self.fired_at<15.,'actual replicated score/owner notifications missing')
            if not ready:return
            self.report['result']=row;atomic_write(self.root/(self.peer+'-native-rules-observed.json'),dict(run_id=self.run))
            self.cleanup();self.report['status']='awaiting_release';atomic_write(self.root/('ready-'+self.peer+'.json'),dict(run_id=self.run));self.stage='release'
        elif self.stage=='release' and self.token('release.json'):self.finish()

    def cleanup(self):
        if getattr(self,'cleanup_done',False):return
        super().cleanup()
        for cls,previous in self.boot:cls.get_cdo().set_property('PythonMixinProfile',previous)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==previous for cls,previous in self.boot)
        self.report['relay_profiles_restored']=self.report['profile_classes_restored'] and self.report['profile_overrides_cleared']
        self.report.pop('original_scores_restored',None)

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'native rule network readiness timed out')
            if not self.ready:
                if self.world_ready():self.setup()
            elif self.peer=='server':self.server_tick()
            else:self.client_tick()
            self.report['stage']=self.stage;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_RULE_NETWORK_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        faulthandler.cancel_dump_traceback_later()
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report)
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_RULE_SHUTDOWN_'+self.report['status'].upper())


network=Network()
ticker=ue.add_ticker(network.tick)
