"""Actual Arena HUD plus owned tile calls and real native team changes."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from . import arena_player_tile_mixin as policy
from .arena_player_tile_contract import validate
PROBE='/Game/UEPValidation/BP_ArenaPlayerTileProbe.BP_ArenaPlayerTileProbe_C'
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(obj):return obj.get_path_name() if valid(obj) else None
def text(widget):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',widget.call_function('GetText'))
def tint(widget):
    color=widget.get_property('Image_82').get_property('Brush').TintColor.SpecifiedColor;return [float(getattr(color,k)) for k in ('r','g','b','a')]
def observer(widget):return widget.get_property('MonitorTeamChangeAsync')
def active(obj):return valid(obj) and bool(obj.call_function('IsActive'))

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.mode=arg('UEPArenaPlayerTileMode');self.started=time.monotonic();self.finished=False;self.world=None;self.roots=[];self.owned=None;self.bare=None;self.selector=None;self.phase='natural';self.frames=0;self.proxies=[]
        self.report=dict(status='running',error=None,mode=self.mode,natural_tiles=[],cases=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,team_callbacks_replayed=False,native_delegate_broadcast_by_fixture=False,child_stat_business_migrated=False,typed_bp_caller=True)
        self.cls=ue.load_class(policy.CLASS);self.probe_cls=ue.load_class(PROBE)
        for obj in (self.cls,self.probe_cls):self.root(obj)
        if self.mode!='Baseline':self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(self.cls)
        self.probe=self.probe_cls.get_cdo()
    def root(self,obj):
        if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
    def write(self):atomic_write(self.path,self.report)
    def state(self,widget,ps):
        stats=[]
        for name in policy.STATS:
            child=widget.get_property(name+'Stat');attribute=child.get_property('Attribute');stats.append(dict(attribute=str(attribute.AttributeName),target=path(child.get_property('Ability Target')),text=text(child.get_property('BonusText'))))
        return dict(name=text(widget.get_property('PlayerName')),expected_name=ps.call_function('GetPlayerName'),expected_target=path(ps),tint=tint(widget),team=int(ps.call_function('GetTeamId')),proxy_active=active(observer(widget)),stats=stats,counts=copy.deepcopy(policy.evidence(widget)),in_viewport=bool(widget.call_function('IsInViewport')),native_owner=path(widget.call_function('GetOwningPlayer')),native_parent=path(widget.call_function('GetParent')),visible=bool(widget.call_function('IsVisible')))
    def snapshot(self,name,**fields):
        row=self.state(self.owned,self.ps);row.update(case=name,**fields);self.report['cases'].append(row);return row
    def set_team(self,team):
        self.cheats.call_function('SetTeam',team)
        if int(self.ps.call_function('GetTeamId'))!=team:raise RuntimeError('native cheat did not change actual team')
    def discover(self):
        for world in ue.all_worlds():
            if world.get_world_type() in (1,3) and 'TopDown' in world.get_name():self.world=world;break
        if self.world is None:return
        controller=policy.lib('GameplayStatics').call_function('GetPlayerController',self.world,0)
        if not valid(controller):return
        ps=controller.get_property('PlayerState')
        if not valid(ps) or int(ps.call_function('GetTeamId')) not in (1,2,3,4):return
        natural=[]
        for widget in ue.tobject_iterator(self.cls):
            if not valid(widget) or not valid(widget.call_function('GetOwningPlayer')):continue
            if widget.call_function('GetOwningPlayer').get_world()!=self.world or not widget.call_function('IsVisible') or not valid(observer(widget)):continue
            target=widget.get_property('BombStat').get_property('Ability Target')
            if valid(target) and active(observer(widget)):natural.append((widget,target))
        if not natural:return
        self.frames+=1
        if self.frames<4:return
        self.report['natural_tiles']=[self.state(w,target) for w,target in natural];self.controller=controller;self.ps=ps;self.original_team=int(ps.call_function('GetTeamId'));manager=ue.new_object(ue.find_class('CheatManager'),controller);self.root(manager);self.cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);self.root(self.cheats)
        self.owned=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,controller);self.root(self.owned);self.owned.call_function('AddToPlayerScreen',0);self.probe.call_function('Configure',self.owned,ps);self.phase='settle';self.frames=0
    def exercise(self):
        self.snapshot('initial-configure');self.proxies.append(observer(self.owned))
        for team in (1,2,3,4):self.set_team(team);self.snapshot('team-'+str(team))
        old=observer(self.owned);self.probe.call_function('Configure',self.owned,self.ps);new=observer(self.owned);self.proxies.append(new);self.snapshot('repeat-configure',previous_proxy_cancelled=not active(old),replacement_distinct=new!=old)
        self.bare=self.world.actor_spawn(ue.find_class('LyraPlayerState'));bare_team=int(self.bare.call_function('GetTeamId'))
        if bare_team!=-1:raise RuntimeError('bare test-owned native PlayerState must have no team')
        old=observer(self.owned);self.probe.call_function('Monitor',self.owned,self.bare);self.proxies.append(observer(self.owned));self.snapshot('unset-monitor',previous_proxy_cancelled=not active(old),observed_team=bare_team)
        before=copy.deepcopy(policy.evidence(self.owned));team=1 if int(self.ps.call_function('GetTeamId'))!=1 else 2;self.set_team(team);self.snapshot('old-target-change',old_target_really_changed_team=int(self.ps.call_function('GetTeamId'))==team,callback_count_unchanged=policy.evidence(self.owned)['payloads']==before['payloads'])
        self.set_team(self.original_team);self.probe.call_function('Configure',self.owned,self.ps);self.proxies.append(observer(self.owned));self.snapshot('restore-configure');self.finish()
    def cleanup(self):
        if hasattr(self,'original_team') and valid(self.ps):self.set_team(self.original_team)
        for proxy in self.proxies:
            if valid(proxy):proxy.call_function('Cancel')
        if valid(self.owned):
            proxy=observer(self.owned)
            if valid(proxy):proxy.call_function('Cancel')
            for name in policy.STATS:
                child=self.owned.get_property(name+'Stat');proxy=child.get_property('AsyncAttributeChanged')
                if valid(proxy):proxy.call_function('Cancel')
            self.owned.call_function('RemoveFromParent')
        if valid(self.bare):self.bare.actor_destroy()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        self.report['owned_observers_cancelled']=all(not active(p) for p in self.proxies);self.report['owned_widget_removed']=not valid(self.owned) or not self.owned.call_function('IsInViewport');self.report['team_restored']=not hasattr(self,'original_team') or int(self.ps.call_function('GetTeamId'))==self.original_team
        for obj in reversed(self.roots):obj.remove_from_root()
        self.report['cleanup_complete']=self.report['owned_observers_cancelled'] and self.report['owned_widget_removed'] and self.report['team_restored'] and all(not obj.is_rooted() for obj in self.roots) and (self.selector is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector)
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>150.:raise RuntimeError('Arena tile native observation timeout: '+self.phase)
            if self.phase=='natural':self.discover()
            else:
                self.frames+=1
                if self.frames>=4:self.exercise()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_PLAYER_TILE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_PLAYER_TILE_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPlayerTileResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
