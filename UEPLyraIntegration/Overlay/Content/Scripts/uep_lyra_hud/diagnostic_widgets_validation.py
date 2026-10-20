"""Paired real UMG ticks/native format cases without performance cache writes."""
import atexit
import hashlib
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import diagnostic_widgets_mixin as policy
from .diagnostic_widgets_contract import FALSE_FIELDS,require,validate

PROFILES=('BlueprintFallback','Python')
SCALES=(-2.,0.,1.,1000.)
PLAYERS=(0,-1,17,2147483647)
def count(w,k,m):return sum(policy.evidence(w)[p+'_'+k+'_'+m] for p in ('python','fallback'))
def display(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.call_function('GetText'))
def digest(v):return hashlib.sha256(v.encode('utf-8')).hexdigest()

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,native_performance_tick_observations=0,same_frame_performance_cases=0,native_format_value_cases=0,native_watermark_player_cases=0);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.widgets=[];self.pairs={};self.scale_index=0;self.player_index=0;self.performance_rows=[];self.watermark_rows=[]
    def create(self,k,profile):
        cls=self.classes[k];cls.get_cdo().set_property('PythonMixinProfile',profile);w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,profile);w.call_function('AddToPlayerScreen',0);return w
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.pairs={k:{p:self.create(k,p) for p in PROFILES} for k in policy.CLASSES};self.user_subsystem=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('CommonUserSubsystem'));user=self.user_subsystem.call_function('GetUserInfoForLocalPlayerIndex',0);self.report['native_valid_user_branch_exercised']=policy.valid(user);self.start_scale()
    def history(self,label,tag):
        file=self.path.parent/(tag+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'diagnostic native FText export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]
    def start_scale(self):
        self.tick_start={w:count(w,k,'tick') for k in ('graph','text') for w in self.pairs[k].values()}
        for k in ('graph','text'):
            for w in self.pairs[k].values():w.set_property('ScaleFactor',SCALES[self.scale_index])
        self.frames=0;self.enter('performance')
    def format_cases(self):
        rows=[]
        for k in ('graph','text'):
            a,b=[self.pairs[k][p] for p in PROFILES]
            for digits in (0,1,3):
                for w in (a,b):w.set_property('FractionalDigits',digits);w.call_function('PreConstruct',False)
                require(display(a.get_property('StatLabelWidget'))==display(b.get_property('StatLabelWidget')) and display(a.get_property('StatValueWidget'))==display(b.get_property('StatValueWidget')),'native preconstruct label/zero format differs')
                if k=='text':
                    for w in (a,b):w.set_property('ValuePaddingWidth',73.);w.call_function('PreConstruct',False);require(float(w.get_property('StatValueSizer').get_property('WidthOverride'))==73.,'native text width override differs')
                for index,value in enumerate((-1234.56789,0.,.125,1234.56789)):
                    for w in (a,b):w.call_function(policy.NATIVE_VALUE,value)
                    text_a=display(a.get_property('StatValueWidget'));text_b=display(b.get_property('StatValueWidget'));require(text_a==text_b and text_a.endswith('ms'),'native grouping/rounding/value format differs');history_a=self.history(a.get_property('StatValueWidget'),k+'-format-'+str(digits)+'-'+str(index)+'-fallback');history_b=self.history(b.get_property('StatValueWidget'),k+'-format-'+str(digits)+'-'+str(index)+'-python');require(history_a==history_b and any('NSLOCTEXT' in s for s in history_a),'native format localization history differs');rows.append(dict(widget=k,digits=digits,value=value,display=text_a));self.report['native_format_value_cases']+=1
        self.report['format_cases']=rows;self.report['native_format_fractional_digit_variants']=3
    def build_case(self):
        a,b=[self.pairs['build'][p] for p in PROFILES];label_a=a.get_property('BuildVersionTextWidget');label_b=b.get_property('BuildVersionTextWidget');text_a=display(label_a);text_b=display(label_b);system=policy.lib('KismetSystemLibrary');expected=system.call_function('GetBuildVersion')+' ('+system.call_function('GetBuildConfiguration')+')';require(text_a==text_b==expected and count(a,'build','construct')>0 and count(b,'build','construct')>0,'actual native build constructor strings differ');history_a=self.history(label_a,'build-fallback');history_b=self.history(label_b,'build-python');require(history_a==history_b and any('NSLOCTEXT' in s and 'C85074294F02CC433E62618A82E030EF' in s for s in history_a),'native build localized format history differs');self.report['native_build_text_and_localized_history_match']=True
    def start_player(self):
        self.player_tick_start={w:count(w,'watermark','tick') for w in self.pairs['watermark'].values()}
        for w in self.pairs['watermark'].values():w.set_property('PlayerNumber',PLAYERS[self.player_index])
        self.frames=0;self.enter('watermark')
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'diagnostic widget phase timeout: '+self.phase)
        if self.phase=='performance':
            self.frames+=1
            if self.frames<4:return
            for k in ('graph','text'):
                a,b=[self.pairs[k][p] for p in PROFILES];ticks=[count(w,k,'tick')-self.tick_start[w] for w in (a,b)];require(min(ticks)>=3,'real native performance ticks missing');self.report['native_performance_tick_observations']+=min(ticks);text_a=display(a.get_property('StatValueWidget'));text_b=display(b.get_property('StatValueWidget'));require(text_a==text_b,'same-frame native/Python stat display differs');require(all(policy.valid(w.get_property('CachedStatSubsystem')) for w in (a,b)),'actual native cached stats subsystem missing');self.performance_rows.append(dict(widget=k,scale=SCALES[self.scale_index],display=text_a,ticks=ticks));self.report['same_frame_performance_cases']+=1
            self.scale_index+=1
            if self.scale_index<len(SCALES):self.start_scale()
            else:self.report.update(same_frame_performance_pairs_match=True,native_cached_stat_subsystem_valid=True,performance_cases=self.performance_rows);self.format_cases();self.build_case();self.start_player()
        elif self.phase=='watermark':
            self.frames+=1
            if self.frames<4:return
            a,b=[self.pairs['watermark'][p] for p in PROFILES];require(all(count(w,'watermark','tick')-self.player_tick_start[w]>=3 for w in (a,b)),'real native watermark ticks missing');names=[display(w.get_property('PlayerNameWidget')) for w in (a,b)];ids=[display(w.get_property('PlayerIDWidget')) for w in (a,b)];require(names[0]==names[1] and ids[0]==ids[1],'native/Python user display branch differs');histories=[self.history(w.get_property('PlayerNameWidget'),'watermark-'+str(self.player_index)+'-'+p) for p,w in zip(PROFILES,(a,b))];require(histories[0]==histories[1] and any('NSLOCTEXT' in s and '6FF399B649D8DB469410EF991342FFB4' in s for s in histories[0]),'native watermark name format history differs')
            if self.player_index>0:require('Not logged in' in names[0] and ids[0]=='','missing controller must use original localized status/empty ID');require(any('196F8C0F4536584BF2CA3C96EA7DA858' in s for s in histories[0]),'missing-user localization key lost');self.report['native_missing_controller_localized_status_verified']=True
            self.watermark_rows.append(dict(player=PLAYERS[self.player_index],name_sha256=digest(names[0]),id_sha256=digest(ids[0])));self.report['native_watermark_player_cases']+=1;self.player_index+=1
            if self.player_index<len(PLAYERS):self.start_player()
            else:self.report.update(native_watermark_available_and_missing_controller_cases_match=True,watermark_cases=self.watermark_rows);self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native diagnostic widget timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_DIAGNOSTIC_WIDGETS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_DIAGNOSTIC_WIDGETS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPDiagnosticWidgetsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
