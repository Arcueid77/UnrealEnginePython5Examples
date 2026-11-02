"""Actual replicated cosmetic actors/meshes before and after native Reset."""
import atexit
import copy
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from . import reset_network_validation as reset,world_policies

original=reset.original
reset.ORDER=('PartsNative','PartsPython');original.PLAN=('native-reset-live',);original.TRIALS=2;original.TOTAL=4


def array(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value
def model(pawn):
    if not original.valid(pawn):return None
    parts=pawn.get_component_by_type(ue.find_class('LyraPawnComponent_CharacterParts'))
    if not original.valid(parts):return None
    actors=[a for a in array(parts.call_function('GetCharacterPartActors')) if original.valid(a)]
    system=ue.find_class('LyraSystemStatics').get_cdo()
    return dict(pawn=pawn.get_path_name(),classes=sorted(a.get_class().get_path_name() for a in actors),meshes=sum(len(array(system.call_function('FindComponentsByClass',a,ue.find_class('MeshComponent'),True))) for a in actors))


class Client(reset.Client):
    def __init__(self,*args):super().__init__(*args);self.report['part_views']=[]
    def find_pawn(self,player_id):
        pawns=array(self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('LyraCharacter')))
        values=[p for p in pawns if original.valid(p) and original.valid(p.PlayerState) and int(p.PlayerState.PlayerId)==player_id]
        return values[0] if len(values)==1 else None
    def arm(self,command):
        expected=original.token(self.root,'parts-expected.json',self.run,command['position'])
        if expected is None:return
        pawn=self.find_pawn(expected['player_id']);view=model(pawn)
        if view is None or view['classes']!=expected['classes'] or view['meshes']<len(expected['classes']):return
        self.part_expected=expected;self.part_old=pawn;self.part_old_path=view['pawn']
        before=self.position;super().arm(command)
        if self.position!=before:self.report['part_views'].append(dict(position=self.position,profile=reset.ORDER[self.index%2],before=view))
    def after_view(self):
        pawn=self.find_pawn(self.part_expected['player_id']);view=model(pawn)
        if view is None or view['pawn']==self.part_old_path or view['classes']!=self.part_expected['classes'] or view['meshes']<len(view['classes']):return False
        self.report['part_views'][-1].update(after=view,old_pawn_removed=not original.valid(self.part_old))
        return not original.valid(self.part_old)
    def complete_reset(self):
        if not self.after_view():return
        super().complete_reset()
    def before_foreign_ack(self):return self.after_view()
    def finalize(self):
        super().finalize()
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_PARTS_NETWORK_SHUTDOWN_'+self.report['status'].upper())


class Server(reset.Server):
    def __init__(self,*args):super().__init__(*args);self.saved_parts={};self.report['part_cases']=[];self.report['part_restoration_barriers']=0
    def prepare(self):
        super().prepare()
        if self.phase!='armed':return
        self.parts=self.controller.get_component_by_type(ue.find_class('LyraControllerComponent_CharacterParts'))
        entries=list(self.parts.get_property('CharacterParts'));fixture=ue.find_class('UEPNativeWorldPolicyFixture').get_cdo();sources=[int(r.Source) for r in array(fixture.call_function('PartRows',self.parts))]
        original.require(entries,'production controller has no original cosmetic part')
        self.saved_parts[self.target]=(self.parts,entries,sources)
        self.part_before=copy.deepcopy(world_policies.metrics(self.policy_host));fixture.call_function('AddSourcePart',self.parts,entries[0].Part,3)
        expected=sorted([entry.Part.PartClass.get_path_name() for entry in entries]+[entries[0].Part.PartClass.get_path_name()])
        self.part_expected=expected
        atomic_write(self.root/'parts-expected.json',dict(run_id=self.run,position=self.position,player_id=int(self.controller.PlayerState.PlayerId),classes=expected))
    def complete_reset(self):
        rows=array(ue.find_class('UEPNativeWorldPolicyFixture').get_cdo().call_function('PartRows',self.parts))
        original.require(sorted(r.PartClass.get_path_name() for r in rows)==self.part_expected and all(r.bHandleValid for r in rows),'authority cosmetic handles did not rebind to new Pawn')
        after=world_policies.metrics(self.policy_host)
        self.report['part_cases'].append(dict(position=self.position,profile=reset.ORDER[self.index%2],classes=self.part_expected,native_handles_valid=True,policy_calls={k:v-self.part_before['applied'].get(k,0) for k,v in after['applied'].items() if k.startswith('Parts.')}))
        super().complete_reset()
    def restore_parts(self):
        fixture=ue.find_class('UEPNativeWorldPolicyFixture').get_cdo()
        saved,self.saved_parts=self.saved_parts,{}
        for component,entries,sources in saved.values():
            original.require(original.valid(component),'controller disappeared before part restoration')
            component.call_function('RemoveAllCharacterParts')
            for entry,source in zip(entries,sources):fixture.call_function('AddSourcePart',component,entry.Part,source)
    def before_authority_ack(self):
        self.restore_parts();self.report['part_restoration_barriers']+=1
    def finish(self,error=None):
        try:self.restore_parts()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report['part_templates_restored']=not self.saved_parts and error is None;super().finish(error)
    def finalize(self):
        super().finalize()
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_PARTS_NETWORK_SHUTDOWN_'+self.report['status'].upper())


result,peer,run=(original.arg(flag) for flag in ('-UEPAutoRespawnResetNetworkResult=','-UEPJumpPeer=','-UEPJumpRun='))
validation=Server(result,run) if peer=='server' else Client(result,peer,run)
atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
