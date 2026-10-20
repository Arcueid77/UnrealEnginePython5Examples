"""Owned LAN host plus real browser rows and two independent native UI joins."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_network_io import read_json,atomic_write
from .experience_screen_validation import Validation as Shared,arg,path
from .host_session_validation import Validation as HostBase
from . import host_session_mixin as host_policy
from . import session_browser_mixin as browser_policy
from . import session_button_mixin as button_policy
from . import session_entry_mixin as policy
from .session_entry_contract import FALSE_FIELDS,require,validate_peer
def count(w,key):return sum(policy.evidence(w)[p+'_'+key] for p in ('python','fallback'))
def host_count(w,key):return sum(host_policy.evidence(w)[p+'_'+key] for p in ('python','fallback'))
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def mode(world):return str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world).call_function('CaptureSnapshot').NetMode)
def fresh_world(original):
    for world in ue.all_worlds():
        if world.get_world_type() not in (1,3) or world==original:continue
        controller=policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
        if not valid(controller):continue
        bridge=policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
        if not valid(bridge):continue
        snap=bridge.call_function('CaptureSnapshot')
        if snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0:return world,controller,snap
    return None
class Finish:
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<600.,'entry peer timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SESSION_ENTRY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate_peer(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SESSION_ENTRY_SHUTDOWN_'+self.report['status'].upper())
    def destroy_session(self,phase):
        self.destroyed=[];proxy=ue.find_class('DestroySessionCallbackProxy').get_cdo().call_function('DestroySession',self.world,self.controller);self.bind(proxy,'OnSuccess',lambda:self.destroyed.append(True),True);self.bind(proxy,'OnFailure',lambda:self.destroyed.append(False));proxy.call_function('Activate');self.enter(phase)
class Host(Finish,HostBase):
    def __init__(self,result):
        super().__init__(result);self.mode='host';self.only_profile='Python';self.require_local_playing_phase=False;self.directory=Path(arg('UEPSessionEntryDirectory',''));self.report=dict(status='running',error=None,role='host');self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.max_players=0
    def observe(self):
        require(time.monotonic()-self.phase_started<(420. if self.phase=='hold' else 100.),'entry host phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if not self.loaded or self.frames<4:return
            self.w.get_property('SessionTypeButton').call_function('HandleButtonClicked')
            if self.w.get_property('BotsEnabled'):self.w.get_property('BotsToggleButton').call_function('HandleButtonClicked')
            require(int(self.w.get_property('Online Mode'))==1 and not self.w.get_property('BotsEnabled'),'native LAN/bots-off choice differs');self.request_before={path(r) for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest'))};self.list.get_property('ExperienceWidgets')[0].get_property('ExperienceTileButton').call_function('HandleButtonClicked');self.original_world=self.world;self.enter('host_request')
        elif self.phase=='host_request':
            if host_count(self.w,'prepared')<1:return
            requests=[r for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest')) if path(r) not in self.request_before];require(len(requests)==1,'owned LAN host request duplicated');self.payload=self.request(requests[0]);require(self.payload['mode']==1 and self.payload['args'].get('NumBots')=='0','native LAN request differs');self.report.update(native_lan_host_choices_and_submit=True,request_mode=1,request_bots='0');self.enter('host_arrival')
        elif self.phase=='host_arrival':
            arrival=fresh_world(self.original_world)
            if not arrival:return
            self.world,self.controller,snap=arrival;self.new_world=self.world;level=policy.lib('GameplayStatics').call_function('GetCurrentLevelName',self.world,True);game_mode=policy.lib('GameplayStatics').call_function('GetGameMode',self.world);experience=policy.lib('GameplayStatics').call_function('ParseOption',game_mode.get_property('OptionsString'),'Experience');require(str(snap.NetMode)=='ListenServer' and level==self.payload['map'][1].rsplit('/',1)[-1] and experience==self.payload['args']['Experience'] and host_count(self.w,'completed')==1,'owned host map/experience/completion differs');self.report.update(native_requested_map_and_experience_ready=True,native_destination_level=level,native_destination_experience=experience,native_destination_mode=str(snap.NetMode));atomic_write(self.directory/'host-ready.json',dict(level=level,experience=experience));self.enter('hold')
        elif self.phase=='hold':
            game_mode=policy.lib('GameplayStatics').call_function('GetGameMode',self.world);self.max_players=max(self.max_players,int(game_mode.call_function('GetNumPlayers')))
            if not (self.directory/'host-stop.token').exists():return
            require(self.max_players>=2,'owned listen host never observed remote client');self.report.update(native_remote_client_observed=True,max_native_players=self.max_players);self.destroy_session('destroy')
        elif self.phase=='destroy':
            if not self.destroyed:return
            require(self.destroyed==[True],'owned native LAN host destruction failed');self.report['owned_native_host_session_destroyed']=True;self.finish()
class Client(Finish,Shared):
    def __init__(self,result):
        super().__init__(result);self.mode='quick';self.only_profile=arg('UEPSessionEntryProfile','Python');self.require_local_playing_phase=False;self.directory=Path(arg('UEPSessionEntryDirectory',''));self.report=dict(status='running',error=None,role='client',profile=self.only_profile,direct_interface_invalid_item_inputs=['null','search request instead of result']);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.extra_cdos={}
    def begin(self):
        for name in (policy.CLASS,browser_policy.CLASS,button_policy.CLASS):
            cls=ue.load_class(name)
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls);self.extra_cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.only_profile)
        super().begin();self.cdos.update(self.extra_cdos);self.host=read_json(self.directory/'host-ready.json');self.original_world=self.world
    def history(self,widget,name):
        file=self.path.parent/(self.only_profile+'-'+name+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(widget,str(file)),'native entry text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return next(line.strip() for line in text.splitlines() if line.strip().startswith('Text='))
    def check_row(self):
        item=self.entry.get_property('SessionEntry');require(item in self.results and count(self.entry,'item')>=1 and count(self.entry,'display_ready')==count(self.entry,'image')==1,'actual native row assignment/primary load missing');fields=native_outputs('CommonSession_SearchResult','GetStringSetting',item.call_function('GetStringSetting','GAMEMODE'));asset=policy.lib('LyraSystemStatics').call_function('GetPrimaryAssetIdFromUserFacingExperienceName',fields['Value']);self.definition=one(policy.lib('KismetSystemLibrary').call_function('GetObjectFromPrimaryAssetId',asset));require(valid(self.definition),'actual advertised experience not loaded');button=self.entry.get_property('SessionButton');names=('GameModeText','MapNameText','PingText','PlayersText','MaxPlayersText');texts=[str(button.get_property(n).call_function('GetText')) for n in names];maximum=int(item.call_function('GetMaxPublicConnections'));players=maximum-int(item.call_function('GetNumOpenPublicConnections'));ping=int(item.call_function('GetPingInMs'));expected=[str(self.definition.get_property('TileTitle'))+' / ',str(self.definition.get_property('TileSubTitle')),str(ping)+'ms',str(players),' / '+str(maximum)];require(texts==expected,'native five text values differ: '+repr((texts,expected)));histories=[self.history(button.get_property(n),n) for n in names];require(all('NSLOCTEXT' in histories[i] for i in (0,1,2,4)),'native localized entry format history missing');self.report.update(native_original_localized_and_numeric_five_texts=True,native_text_values=texts,native_text_histories=histories);material=button.get_property('ButtonBorder').call_function('GetDynamicMaterial');require(one(material.call_function('K2_GetTextureParameterValue','MapTileArt'))==self.definition.get_property('TileIcon'),'actual definition TileIcon differs');self.report['native_definition_texture_identity']=True
        for invalid in (None,self.browser.get_property('SearchRequest')):self.entry.call_function('OnListItemObjectSet',invalid);require(self.entry.get_property('SessionEntry')==item and count(self.entry,'display_ready')==1,'invalid row input changed current native entry')
        self.report['native_invalid_items_preserve_current_row']=True;require(self.healths()==self.health_before,'initial gameplay health changed before native join');self.report['initial_gameplay_health_unchanged_before_join']=True;self.loading_seen=[];self.bind(self.loading,'OnLoadingScreenWidgetChanged',lambda cls:self.loading_seen.append(cls));button.call_function('HandleButtonClicked');self.enter('join_request')
    def observe(self):
        require(time.monotonic()-self.phase_started<110.,'entry client phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if not self.loaded or self.frames<4:return
            self.list.call_function('SelectFirstExperience');self.push('BrowseButton','browse')
        elif self.phase=='browse':
            self.bind_push()
            if not self.afterpush:return
            require(len(self.afterpush)==1,'native browser push duplicated');self.browser=self.afterpush[0];self.widgets.append(self.browser);self.report['native_selection_login_and_browser_afterpush']=True;self.enter('row')
        elif self.phase=='row':
            request=self.browser.get_property('SearchRequest')
            if not valid(request):return
            self.results=list(request.get_property('Results'));entries=list(self.browser.get_property('LyraListView').call_function('GetDisplayedEntryWidgets'));entries=[w for w in entries if path(w.get_class())==policy.CLASS]
            self.report['native_search_diagnostics']=dict(result_count=len(self.results),displayed_entries=len(entries))
            if not entries:return
            require(len(self.results)>=1 and len(entries)==1,'owned LAN browser result/row count differs');self.entry=entries[0]
            if count(self.entry,'image')<1:return
            self.entry.add_to_root();self.roots.append(self.entry);self.widgets.append(self.entry);require(str(ue.get_mixin_profile(self.entry))==self.only_profile,'native generated entry Profile differs');self.report.update(native_actual_nonempty_search_and_list_row=True,native_result_count=len(self.results));self.check_row()
        elif self.phase=='join_request':
            if count(self.entry,'prepared')<1:return
            require(count(self.entry,'spinner')==count(self.entry,'prepared')==1 and valid(self.entry.get_property('JoiningProgressWidget')) and self.loading_seen and self.loading.call_function('GetLoadingScreenContentWidget') is not None,'native spinner/primary/loading macro ordering missing');self.report.update(native_spinner_afterpush_then_primary_and_loading_macro=True,prepared_handler_calls=count(self.entry,'prepared'));self.enter('arrival')
        elif self.phase=='arrival':
            arrival=fresh_world(self.original_world)
            if not arrival:return
            world,controller,snap=arrival;level=policy.lib('GameplayStatics').call_function('GetCurrentLevelName',world,True);experience=path(snap.CurrentExperience);require(str(snap.NetMode)=='Client' and level==self.host['level'] and self.host['experience'] in experience and count(self.entry,'completed')==1 and not self.entry.get_property('JoiningProgressWidget').call_function('IsActivated'),'native join completion/pop/client destination differs');self.world=world;self.controller=controller;self.report.update(native_join_completion_after_unbind_and_spinner_pop=True,native_client_travel_to_owned_host_map_and_experience=True,native_destination_level=level,native_destination_experience=self.host['experience'],native_destination_mode=str(snap.NetMode),completion_handler_calls=count(self.entry,'completed'),native_world_controller_replacement_expected=True);self.destroy_session('destroy')
        elif self.phase=='destroy':
            if not self.destroyed:return
            require(self.destroyed==[True],'owned client session destruction failed');self.report['owned_native_client_session_destroyed']=True;self.finish()
    def cleanup(self):
        super().cleanup()
        for cls,profile in self.extra_cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        self.report.pop('original_gameplay_health_unchanged',None)
    def close(self,widget):
        if widget.is_a(ue.find_class('CommonActivatableWidget')):super().close(widget)
        else:widget.call_function('RemoveFromParent')
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSessionEntryResult=')),None)
if result:
    validation=(Host if arg('UEPSessionEntryRole','client')=='host' else Client)(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
