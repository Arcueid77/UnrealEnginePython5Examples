"""Native MID/camera/stencil/device observations on both original Explorer classes."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from .explorer_helpers_validation import Validation as Helpers
from .team_cosmetics_validation import DeviceObserver,primitives
from . import explorer_style_mixin as policy
from .team_cosmetics_mixin import FALLBACK
from .explorer_style_contract import require,validate

def rgba(c):return [float(c.r),float(c.g),float(c.b),float(c.a)]
def close(a,b):return all(abs(x-y)<.00001 for x,y in zip(a,b))

class Validation(Helpers):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerStyleProfile=')),'Python');self.report.update(profile=self.profile,hardware_output_tested=False,pixels_tested=False);self.device_observer=None;self.device_props=[]
    def state(self):
        material=self.subject.get_property(policy.FIELD);camera=self.subject.get_property('CameraComponent');require(valid(material),'native Explorer outline MID absent')
        return dict(team=float(material.call_function('K2_GetScalarParameterValue','TeamID')),color=rgba(material.call_function('K2_GetVectorParameterValue','TeamColor')),parent=material.get_property('Parent').get_path_name(),blend_count=len(camera.get_property('PostProcessSettings').WeightedBlendables.Array),stencils=sorted(int(p.get_property('CustomDepthStencilValue')) for p in primitives(self.subject)))
    def start_matrix(self):
        if self.device_observer is None:self.device_observer=DeviceObserver()
        self.style_probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_Explorer'+self.kind.title()+'StyleCallProbe.BP_Explorer'+self.kind.title()+'StyleCallProbe_C'));self.owned.append(self.style_probe);self.row['style_cases']=[];self.device_props=[]
        camera=self.subject.get_property('CameraComponent');settings=camera.get_property('PostProcessSettings').clone();weights=settings.WeightedBlendables.clone();weights.Array=[];settings.WeightedBlendables=weights;camera.set_property('PostProcessSettings',settings);self.subject.set_property(policy.FIELD,None)
        require(self.subject.get_property(policy.FIELD) is None,'owned Explorer fresh outline cache did not clear')
        self.style_probe.call_function('Outline',self.subject,-3,ue.FLinearColor(.2,.4,.6,1.));self.check('fresh',-3,[.2,.4,.6,1.]);first=self.subject.get_property(policy.FIELD)
        self.style_probe.call_function('Outline',self.subject,17,ue.FLinearColor(.8,.3,.1,1.));self.check('reuse',17,[.8,.3,.1,1.]);self.row['existing_mid_reused_without_new_blend']=self.subject.get_property(policy.FIELD)==first and self.state()['blend_count']==1;require(self.row['existing_mid_reused_without_new_blend'],'original Explorer material cache was not reused')
        found,team,display=lib('LyraTeamStatics').call_function('FindTeamFromObject',self.subject,False);require(found and valid(display),'native actual team display required')
        self.row['native_device_count_matches_platform_validity']=True
        for name,requested_team,asset in (('team-null',3,None),('team-display',7,display),('legacy-zero',0,None)):
            before=self.device_observer.marker();user=self.subject.call_function('GetPlatformUserId');expected=bool(lib('InputDeviceLibrary').call_function('IsValidPlatformId',user))
            if name=='legacy-zero':self.style_probe.call_function('Legacy',self.subject)
            else:self.style_probe.call_function('Team',self.subject,requested_team,asset)
            props=self.device_observer.collect(before);require(len(props)==int(expected),'original Explorer device count differs from platform validity');self.device_props.extend(props)
            color=lib('LyraTeamStatics').call_function('GetTeamColorWithFallback',asset,'TeamColor',ue.FLinearColor(*FALLBACK));self.check(name,requested_team,rgba(color));self.row['style_cases'][-1].update(native_device_activations=len(props),platform_user_valid=expected)
        negative=self.world.actor_spawn(self.classes[self.kind],self.pawn.get_actor_location()+ue.FVector(12000.,0.,1000.));self.owned.append(negative);negative.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);before=negative.get_property(policy.FIELD);self.style_probe.call_function('Outline',negative,99,ue.FLinearColor(1.,0.,0.,1.));self.row['nonlocal_outline_is_noop']=not negative.call_function('IsLocallyControlled') and negative.get_property(policy.FIELD)==before;require(self.row['nonlocal_outline_is_noop'],'nonlocal Explorer outline changed');self.enter('style-device')
    def check(self,name,team,color):
        actual=self.state();matches=abs(actual['team']-team)<.0001 and close(actual['color'],color) and actual['parent']==policy.PARENT and actual['blend_count']==1;self.row['style_cases'].append(dict(name=name,native_values_match=matches,actual=actual));require(matches,'native Explorer style state differs: '+name)
    def observe(self):
        if self.phase=='style-device':
            self.silence_owned_ui();require(time.monotonic()-self.phase_started<12.,'native style device retirement timeout')
            if not self.device_observer.observed(self.device_props):return
            self.row['native_device_evaluations_and_retirement_observed']=True;super().start_matrix()
        else:super().observe()
    def cleanup(self):
        if self.device_observer is not None:
            self.device_observer.close();self.report['owned_device_markers_and_roots_released']=self.device_observer.roots_created==self.device_observer.roots_released and self.device_observer.markers_removed()
        super().cleanup()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_STYLE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_STYLE_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerStyleResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
