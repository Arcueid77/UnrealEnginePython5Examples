"""Two original local-player owners; natural fuse, self-death and real HUD.

The input owner starts at its original spawn,then moves by original IA_Move
into a free adjacent blast cell. No damage/phase/death callback,position setter,
attribute or bomb lifetime is written by this observer.
"""
import atexit,copy,math,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import EObjectTypeQuery
from uep_lyra_network_io import atomic_write
from uep_lyra_world import arena_actor_mixin as actors,arena_mode_mixin as modes,arena_phases_mixin as phases
from uep_lyra_hud import arena_hud_mixin as hud,arena_player_tile_mixin as tile,arena_player_ui_mixin as player_ui,arena_powerup_stat_mixin as stats
from .arena_local_input_validation import Validation as InputValidation,arg,path,dead,valid,base,drop
from .melee_trace_mixin import native_outputs
from .arena_natural_bomb_contract import validate


class Validation(InputValidation):
    def __init__(self):
        self.last_health=[]
        self.widget_profiles=[];self.move_input=None
        self.fixture_restarted=False
        self.timing_sources=[]
        super().__init__(arg('UEPArenaNaturalResult'),arg('UEPArenaNaturalProfile'))
        self.report.update(test_bombs_destroyed_before_fuse=False,natural_explosion_tested=True,damage_applied_by_fixture=False,explosion_called_by_fixture=False,death_called_by_fixture=False,natural_gameplay_state_reverted=False,hud={},images=[])
        selected=[(actors.HERO,actors.SELECTOR),(actors.DEATH,'PythonMixinProfile')]
        selected += [(p,'PythonMixinProfile') for p in (modes.BASE,modes.LIVES,modes.LOCAL,*phases.CLASSES.values(),hud.LIST,hud.TIMER,tile.CLASS,player_ui.CLASS,stats.CLASS)]
        for class_path,selector in selected:
            cls=ue.load_class(class_path)
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            self.selectors.append((cls,selector,cls.get_cdo().get_property(selector)))
            cls.get_cdo().set_property(selector,self.profile)
        self.death_class=ue.load_class(actors.DEATH);self.stat_class=ue.load_class(stats.CLASS)
        self.report['profile_families_selected_before_experience']=['drop','base bomb','standard bomb','Arena hero/death','Arena mode/phase','Arena player registration/list/tile/stat/clock']
        self.report['native_timing_mode']='variable' if '-UEPArenaNativeVariableTiming' in sys.argv else 'fixed60'
        if self.report['native_timing_mode']=='variable':self.install_timing_observers()

    def install_timing_observers(self):
        self.report['native_timing_events']=[]
        groups=[('bomb',self.classes['base'],('UEPArenaBombBegin','UEPArenaBombTrigger','UEPArenaBombIncrement','UEPArenaBombDestroyed')),
                ('death',self.death_class,('Activate','AfterWait'))]
        owner=self
        def observed(function,scope,name,profile):
            def call(obj,*args):
                # Capture POD metadata before the real handler can retire obj.
                owner.report['native_timing_events'].append(dict(scope=scope,method=name,profile=profile,object=path(obj),frame=int(drop.lib('KismetSystemLibrary').call_function('GetFrameCount')),game_seconds=float(owner.statics.call_function('GetTimeSeconds',obj)),world_delta_seconds=float(owner.statics.call_function('GetWorldDeltaSeconds',obj))))
                return function(obj,*args)
            if hasattr(function,'override'):call.override=function.override
            return call
        for scope,cls,names in groups:
            ue.register_declared_mixin(cls)
            entry=next(row for row in ue.get_registered_mixins() if row['target_class']==cls)
            for profile,row in entry['profiles'].items():
                source=row['python_class'];self.timing_sources.append((cls,profile,source))
                methods={name:value for name,value in source.__dict__.items() if callable(value) and not name.startswith('_')}
                for name in names:methods[name]=observed(getattr(source,name),scope,name,profile)
                ue.register_mixin_profile(cls,profile,type('ObservedArenaNatural'+scope+profile,(),methods))

    def discover_players(self):
        super().discover_players()
        if self.phase!='settle' or self.fixture_restarted:return
        found=self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('LyraPlayerStart'))
        starts=native_outputs('GameplayStatics','GetAllActorsOfClass',found)['OutActors']
        starts=sorted(starts,key=lambda a:tuple(float(getattr(a.call_function('K2_GetActorLocation'),k)) for k in ('x','y','z')))
        self.require(len(starts)>=2,'two original native Arena player starts required')
        chosen=[starts[0],starts[-1]];controllers=[p['controller'] for p in self.players]
        self.report['native_fixture_restart_starts']=[[float(getattr(a.call_function('K2_GetActorLocation'),k)) for k in ('x','y','z')] for a in chosen]
        for player in self.players:
            player['controller'].call_function('UnPossess')
            player['pawn'].call_function('K2_DestroyActor')
        mode=self.statics.call_function('GetGameMode',self.world)
        for controller,start in zip(controllers,chosen):mode.call_function('RestartPlayerAtPlayerStart',controller,start)
        self.fixture_restarted=True;self.players=[];self.last_health=[];self.enter('players')

    def health(self):
        result=[]
        for index,p in enumerate(self.players):
            previous=self.last_health[index] if index<len(self.last_health) else 0.
            component=p['pawn'].get_component_by_type(ue.find_class('LyraHealthComponent')) if valid(p['pawn']) else None
            result.append(float(component.call_function('GetHealth')) if valid(component) else previous)
        self.last_health=result;return result

    def hud_state(self):
        rows=[];prefix='python_' if self.profile=='Python' else 'fallback_'
        for widget in ue.tobject_iterator(self.stat_class):
            if not valid(widget) or not valid(widget.call_function('GetOwningPlayer')):continue
            if widget.call_function('GetOwningPlayer').get_world()!=self.world or not widget.call_function('IsVisible'):continue
            if str(widget.get_property('Attribute').AttributeName)!='BombsRemaining':continue
            target=widget.get_property('Ability Target');owner=next((i for i,p in enumerate(self.players) if p['state']==target),None)
            if owner is None:continue
            value,found=stats.query(widget)
            text=drop.lib('KismetTextLibrary').call_function('Conv_TextToString',widget.get_property('BonusText').call_function('GetText'))
            counts=stats.evidence(widget)
            rows.append(dict(target_owner=owner,native_attribute_found=bool(found),value=float(value),text=str(text),effective_profile_matches=str(ue.get_mixin_profile(widget))==self.profile,selected_profile_callback=counts[prefix+'update']>0))
        return sorted(rows,key=lambda row:(row['target_owner'],row['text']))

    def capture(self,phase):
        filename=self.path.parent/(phase+'.png')
        drop.lib('KismetSystemLibrary').call_function('ExecuteConsoleCommand',self.world,'Shot showui -nosuffix filename="'+str(filename)+'"',self.players[0]['controller'])
        self.report['images'].append(dict(phase=phase,path=str(filename)))

    def scores(self):
        return [[int(p['state'].call_function('GetStatTagStackCount',GameplayTag(TagName='ShooterGame.Score.'+name))) for name in ('Eliminations','Deaths','Assists')] for p in self.players]

    def start_case(self):
        # Designer-created widget instances have serialized template defaults.
        # Select their live profiles before gameplay; native construction itself
        # is not claimed as an original-BP comparison in this scenario.
        for widget in ue.tobject_iterator(self.stat_class):
            if not valid(widget) or not valid(widget.call_function('GetOwningPlayer')):continue
            if widget.call_function('GetOwningPlayer').get_world()!=self.world:continue
            if not any(old[0]==widget for old in self.widget_profiles):
                self.widget_profiles.append((widget,str(ue.get_mixin_profile(widget))))
                ue.set_mixin_profile(widget,self.profile)
        rows=self.hud_state()
        if {r['target_owner'] for r in rows}!={0,1} or any(r['text']!='1' for r in rows):return
        self.report['hud']['before']=rows;self.capture('before')
        self.report['hud_profiles_selected_after_native_construction_before_input']=True
        blocks=self.statics.call_function('GetAllActorsOfClass',self.world,ue.load_class(base.BLOCK))
        self.report['original_destructible_layout_before_input']=sorted([float(getattr(a.call_function('K2_GetActorLocation'),k)) for k in ('x','y','z')] for a in native_outputs('GameplayStatics','GetAllActorsOfClass',blocks)['OutActors'])
        spec=next(s for s in self.players[0]['asc'].get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(self.death_class))
        ability,=[a for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(a)]
        self.death_ability=ability;self.death_counts=actors.evidence(ability)
        self.before_scores=self.scores();self.death_started=None;self.death_finished=None
        self.game_spawned=None;self.first_damage=None;super().start_case()

    def observe_spawn(self):
        super().observe_spawn()
        if self.phase!='repeat':return
        self.game_spawned=float(self.statics.call_function('GetTimeSeconds',self.world))
        self.first_observed_bomb_age=float(self.bomb.call_function('GetGameTimeSinceCreation'))
        self.bomb_counts=base.evidence(self.bomb)
        self.original_fuse=float(self.bomb.get_property('BombLifespan'))
        self.report['drop']=copy.deepcopy(self.current)
        self.report['natural']=dict(health_before=list(self.initial_health),original_fuse_seconds=self.original_fuse,original_minimum_burn_seconds=float(self.bomb.get_property('MinBurnTimeEvenIfShortened')),bomb_age_at_first_observation_seconds=self.first_observed_bomb_age,observed_world_delta_seconds=[])
        self.prepare_move()
        self.enter('armed')

    def cell_actors(self,position):
        value=drop.lib('KismetSystemLibrary').call_function('BoxOverlapActors',WorldContextObject=self.world,BoxPos=position,BoxExtent=ue.FVector(48.,48.,48.),ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery2,EObjectTypeQuery.ObjectTypeQuery1,EObjectTypeQuery.ObjectTypeQuery3],ActorClassFilter=None,ActorsToIgnore=[self.bomb])
        return native_outputs('KismetSystemLibrary','BoxOverlapActors',value)['OutActors']

    def prepare_move(self):
        player=self.players[0];pawn=player['pawn'];position=self.bomb.call_function('K2_GetActorLocation')
        self.move_origin=pawn.call_function('K2_GetActorLocation')
        directions=sorted(((1,0),(-1,0),(0,1),(0,-1)),key=lambda d:d[0]*position.x+d[1]*position.y)
        for dx,dy in directions:
            cell=ue.FVector(position.x+dx*100.,position.y+dy*100.,50.)
            blocked=any(a.is_a(ue.find_class('StaticMeshActor')) or a.is_a(ue.load_class(base.BLOCK)) for a in self.cell_actors(cell))
            if not blocked:self.blast_cell=cell;self.move_direction=(dx,dy);break
        else:raise AssertionError('original spawn has no free adjacent blast cell')
        data=player['state'].get_property('PawnData').get_property('InputConfig')
        self.move_action=data.call_function('FindNativeInputActionForTag',GameplayTag(TagName='InputTag.Move'),True)
        self.require(valid(self.move_action),'original movement action missing')
        self.move_input=drop.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',player['controller'],ue.find_class('EnhancedInputLocalPlayerSubsystem'))
        yaw=math.radians(float(player['controller'].call_function('GetControlRotation').yaw));dx,dy=self.move_direction
        self.move_vector=ue.FVector(-math.sin(yaw)*dx+math.cos(yaw)*dy,math.cos(yaw)*dx+math.sin(yaw)*dy,0.)
        self.move_done=False
        self.report['natural'].update(native_move_action=path(self.move_action),native_move_vector=[float(self.move_vector.x),float(self.move_vector.y)],pawn_at_spawn=[float(getattr(self.move_origin,k)) for k in ('x','y','z')],bomb_location=[float(getattr(position,k)) for k in ('x','y','z')],selected_blast_cell=[float(getattr(self.blast_cell,k)) for k in ('x','y','z')])

    def move(self):
        if self.move_done:return
        pawn=self.players[0]['pawn'];position=pawn.call_function('K2_GetActorLocation')
        distance=math.hypot(position.x-self.move_origin.x,position.y-self.move_origin.y)
        if distance>=85. or self.health()[0]==0.:
            self.move_input.call_function('InjectInputVectorForAction',self.move_action,ue.FVector())
            self.move_done=True
            self.report['natural'].update(native_move_distance=distance,original_blast_query_contains_owner=pawn in self.cell_actors(self.blast_cell),pawn_after_move=[float(getattr(position,k)) for k in ('x','y','z')])
        else:self.move_input.call_function('InjectInputVectorForAction',self.move_action,self.move_vector)

    def observe_natural(self):
        now=float(self.statics.call_function('GetTimeSeconds',self.world));health=self.health()
        self.report['natural']['observed_world_delta_seconds'].append(float(self.statics.call_function('GetWorldDeltaSeconds',self.world)))
        self.move()
        prefix='python_' if self.profile=='Python' else 'fallback_';other='fallback_' if self.profile=='Python' else 'python_'
        if self.death_counts[prefix+'death'] and self.death_started is None:self.death_started=now
        if self.death_counts[prefix+'finish'] and self.death_finished is None:self.death_finished=now
        if health[0]==0 and self.first_damage is None:self.first_damage=now
        self.report['natural'].update(last_health=health,death_counts=copy.deepcopy(self.death_counts),bomb_counts=copy.deepcopy(self.bomb_counts),bomb_destroyed=dead(self.bomb),remaining_now=self.remaining())
        self.require(now-self.game_spawned<10.,'native natural bomb/death expectations unmet; inspect collision and profile observations')
        if self.phase=='armed':
            rows=self.hud_state()
            if rows and all(r['text']==('0' if r['target_owner']==0 else '1') for r in rows):
                self.report['hud']['spent']=rows;self.capture('spent');self.enter('natural')
        if not dead(self.bomb) or self.death_finished is None:return
        rows=self.hud_state()
        if {r['target_owner'] for r in rows}!={0,1} or any(r['text']!='1' for r in rows):return
        self.report['hud']['refunded']=rows
        elapsed=self.first_damage-self.game_spawned if self.first_damage is not None else -1.
        self.report['natural'].update(health_after=health,bomb_destroyed_naturally=True,remaining_after_refund=self.remaining(),native_death_started=self.death_started is not None,native_death_finished=self.death_finished is not None,selected_death_callbacks=[self.death_counts[prefix+'death'],self.death_counts[prefix+'finish']],other_death_callbacks=[self.death_counts[other+'death'],self.death_counts[other+'finish']],selected_bomb_destroyed_callback=self.bomb_counts[prefix+'destroyed'],damage_after_observation_seconds=elapsed,damage_after_creation_seconds=elapsed+self.first_observed_bomb_age,death_task_seconds=self.death_finished-self.death_started if self.death_started is not None else -1.,scores_before=self.before_scores,scores_after=self.scores())
        self.capture('refunded');self.enter('images')

    def cleanup(self):
        self.report.setdefault('natural',{})['bombs_destroyed_by_cleanup']=sum(not dead(b) for b in self.bombs_owned)
        if valid(self.move_input):self.move_input.call_function('InjectInputVectorForAction',self.move_action,ue.FVector())
        for widget,previous in self.widget_profiles:
            if valid(widget):ue.set_mixin_profile(widget,previous)
        for cls,profile,source in self.timing_sources:ue.register_mixin_profile(cls,profile,source)
        if self.timing_sources:
            self.report['native_timing_observer_profiles_restored']=all(next(row for row in ue.get_registered_mixins() if row['target_class']==cls)['profiles'][profile]['python_class'] is source for cls,profile,source in self.timing_sources)
        super().cleanup()

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_ARENA_NATURAL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_NATURAL_SHUTDOWN_'+self.report['status'].upper())

    def tick(self,delta):
        try:
            self.require(time.monotonic()-self.started<180.,'Arena natural observation timed out in '+self.phase)
            if self.phase=='world':self.discover_world()
            elif self.phase=='players':self.discover_players()
            elif self.phase=='settle':
                if time.monotonic()-self.since>=1.:self.start_case()
            elif self.phase=='press':
                self.press(self.frames<3);self.frames+=1
                if self.frames>=6:self.enter('spawn')
            elif self.phase=='spawn':self.observe_spawn()
            elif self.phase in ('armed','natural'):self.observe_natural()
            elif self.phase=='images':
                if all(Path(r['path']).exists() for r in self.report['images']) and time.monotonic()-self.since>=.3:self.finish()
            atomic_write(self.path,self.report)
        except Exception:self.finish(traceback.format_exc())
        return not self.finished


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
