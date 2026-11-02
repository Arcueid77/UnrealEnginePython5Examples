"""Native cost/AdditionalCosts differential using real GAS-owned ability instances."""
import copy
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,UEPCostFixtureSpec
from uep_lyra_native import tag_stack_costs as policy


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def require(value,message):
    if not value:raise AssertionError(message)
def outputs(value):return value if isinstance(value,tuple) else (value,)


def run(stage,kind):
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    world=ue.get_editor_world();cls=ue.load_class('/Game/UEPValidation/GA_TagStackCostWitness.GA_TagStackCostWitness_C');ue.register_declared_mixin(cls);rooted=cls.is_rooted()
    if not rooted:cls.add_to_root()
    library=ue.find_class('UEPNativeCostFixture').get_cdo();case_library=ue.find_class('UEPNativeCostCase').get_cdo();editor=ue.find_class('EditorSubsystemBlueprintLibrary').get_cdo().call_function('GetEditorSubsystem',ue.find_class('EditorActorSubsystem'))
    curve=library.call_function('MakeCurve','CostProbe',1.9,3.9);curve.add_to_root()
    tag='Lyra.ShooterGame.Weapon.MagazineAmmo';failure='Ability.ActivateFail.Cost';player=kind=='player'
    specifications=[
        dict(name='below',available=0,apply=False),dict(name='equal',available=1),dict(name='above',available=4),
        dict(name='fraction',available=4,quantity=1.9),dict(name='zero',available=0,quantity=0.),dict(name='negative',available=4,quantity=-1.9),
        dict(name='no_equipment',available=4,equipment=False),dict(name='no_player_state',available=4,player_state=False),
        dict(name='no_failure_output',available=0,apply=False,failure_output=False),dict(name='invalid_failure_tag',available=0,apply=False,failure=''),
        dict(name='not_authority',available=4,authority=False),dict(name='curve_level_one',available=5,curve=True),dict(name='curve_level_two',available=5,curve=True,level=2),
        dict(name='hit_only_miss',available=4,only_hit=True),dict(name='hit_only_hit',available=4,only_hit=True,hit=True),dict(name='direct_cost_ignores_hit_filter',available=4,only_hit=True,caller=False),
        dict(name='first_failure_stops_costs',available=1,quantity=2.,apply=False,second_cost=True),dict(name='two_costs',available=4,second_cost=True),
    ]
    report=dict(status='running',error=None,kind=kind,cases=[],simulated_native_role_fixture=True,actual_network_acceptance=False,raw_actor_info_exposed=False,fixtures_saved=False,fixture_actors_removed=True)
    try:
        for spec in specifications:
            results=[]
            for profile in ('NativeCostFallback','Python'):
                quantity=float(spec.get('quantity',1.));cost=UEPCostFixtureSpec(bPlayerStack=player,Quantity=quantity,Tag=GameplayTag(TagName=tag),FailureTag=GameplayTag(TagName=spec.get('failure',failure)),bOnlyOnHit=bool(spec.get('only_hit',False)))
                if spec.get('curve'):cost.CurveTable=curve;cost.CurveRow='CostProbe'
                entries=[cost]
                if spec.get('second_cost'):entries.append(UEPCostFixtureSpec(bPlayerStack=player,Quantity=1.,Tag=GameplayTag(TagName=tag),FailureTag=GameplayTag(TagName=failure)))
                library.call_function('Configure',cls,entries)
                case=case_library.call_function('Create',world,cls,int(spec['available']),int(spec.get('level',1)),bool(spec.get('equipment',True)),bool(spec.get('player_state',True)));case.add_to_root();ability=case.Ability;actors=[case.Controller,case.Pawn,case.PlayerState]
                try:
                    # Blueprint construction caches which CDO properties differ
                    # from its native parent. This unsaved test CDO is edited
                    # after compilation, so explicitly initialize the fixture.
                    costs=cls.get_cdo().get_property('AdditionalCosts');require(len(costs)==len(entries),'native fixture CDO cost configuration differs')
                    ability.set_property('AdditionalCosts',costs);require(len(ability.get_property('AdditionalCosts'))==len(entries),'native fixture instance cost configuration differs')
                    ue.set_mixin_profile(ability,profile)
                    result=case.call_function('Probe',bool(spec.get('failure_output',True)),bool(spec.get('apply',True)),bool(spec.get('authority',True)),bool(spec.get('caller',True)),bool(spec.get('hit',False)))
                    outcome=dict(can_pay=bool(result.bCanPay),before=int(result.Before),after=int(result.After),authority=bool(result.bAuthority),failure_tags=sorted(str(t.TagName) for t in result.Failures.GameplayTags))
                    counts=copy.deepcopy(policy.metrics(ability));require(counts['native_routes']>0 if profile=='NativeCostFallback' else counts['python_routes']>0,'native cost owner route was bypassed')
                    require(counts['checks']==counts['applications']==0 if profile=='NativeCostFallback' else counts['checks']>0,'native/Python evaluation route differs')
                    if not spec.get('authority',True):require(outcome['after']==outcome['before'] and counts['applications']==0,'client-role cost wrote tag stacks')
                    if player:require(not outcome['failure_tags'],'original player cost must not add failure tags')
                    if spec['name']=='first_failure_stops_costs':require((counts['native_routes'] if profile=='NativeCostFallback' else counts['checks'])==1,'original AdditionalCosts caller did not fail fast')
                    results.append(outcome);report['cases'].append(dict(name=spec['name'],profile=profile,outcome=outcome,metrics=counts))
                finally:
                    ue.clear_mixin_profile(ability);case.call_function('Clear')
                    for actor in reversed(actors):
                        if actor in world.all_actors():report['fixture_actors_removed']&=bool(editor.call_function('DestroyActor',actor))
                        report['fixture_actors_removed']&=actor not in world.all_actors()
                    case.remove_from_root()
            require(results[0]==results[1],'native/Python cost result differs: '+spec['name'])
        report['status']='passed'
    finally:
        curve.remove_from_root()
        if not rooted:cls.remove_from_root()
        report['class_root_restored']=cls.is_rooted()==rooted;report['curve_root_released']=not curve.is_rooted()
    return report


result=Path(arg('UEPNativeCostResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_costs.py'))).resolve();sys.path.insert(0,str(script.parent));report=run(Path(arg('UEPNativeCostStageRoot')).resolve(),arg('UEPNativeCostKind'))
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_COST_BOUNDARIES_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
