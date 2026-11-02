"""Exercise bounded diagnostic history through repeated native cost callbacks."""
import json
from pathlib import Path
import sys
import traceback


def require(value,message):
    if not value:raise AssertionError(message)
def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def gate(report):
    require(report['status']=='passed' and report['error'] is None and len(report['cases'])==2,'native cost history lane failed')
    require({c['kind'] for c in report['cases']}=={'item','player'},'native cost history target coverage differs')
    for c in report['cases']:require(c['checks']==160 and c['applications']==0 and c['history_size']==128 and c['first_available']==c['last_available']==4,'native cost history bound differs')
    require(report['fixture_actors_removed'] and report['class_root_restored'],'native cost history fixture leaked')
    return dict(status='passed',native_checks=320,history_limit=128,cpp_compile_executed=False)


def run(stage):
    import unreal_engine as ue
    from unreal_engine.structs import GameplayTag,UEPCostFixtureSpec
    from uep_lyra_native import tag_stack_costs as policy
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    cls=ue.load_class('/Game/UEPValidation/GA_TagStackCostWitness.GA_TagStackCostWitness_C');ue.register_declared_mixin(cls);rooted=cls.is_rooted()
    if not rooted:cls.add_to_root()
    world=ue.get_editor_world();library=ue.find_class('UEPNativeCostFixture').get_cdo();factory=ue.find_class('UEPNativeCostCase').get_cdo();editor=ue.find_class('EditorSubsystemBlueprintLibrary').get_cdo().call_function('GetEditorSubsystem',ue.find_class('EditorActorSubsystem'));tag=GameplayTag(TagName='Lyra.ShooterGame.Weapon.MagazineAmmo')
    report=dict(status='running',error=None,cases=[],fixture_actors_removed=True,simulated_native_role_fixture=True,actual_network_acceptance=False)
    try:
        for player in (False,True):
            library.call_function('Configure',cls,[UEPCostFixtureSpec(bPlayerStack=player,Quantity=1.,Tag=tag)]);case=factory.call_function('Create',world,cls,4,1,True,True);case.add_to_root();ability=case.Ability;actors=[case.Controller,case.Pawn,case.PlayerState]
            try:
                ability.set_property('AdditionalCosts',cls.get_cdo().get_property('AdditionalCosts'));ue.set_mixin_profile(ability,'Python');target=case.PlayerState if player else case.Item
                for i in range(160):
                    r=case.call_function('Probe',True,False,True,False,False);require(r.bCanPay and int(r.Before)==int(r.After)==4,'native check result differs: '+json.dumps(dict(player=player,iteration=i,can_pay=bool(r.bCanPay),before=int(r.Before),after=int(r.After),contexts=policy.metrics(ability)['contexts'][-2:])))
                m=policy.metrics(ability);report['cases'].append(dict(kind='player' if player else 'item',checks=m['checks'],applications=m['applications'],history_size=len(m['contexts']),first_available=m['contexts'][0]['available'],last_available=m['contexts'][-1]['available']))
            finally:
                ue.clear_mixin_profile(ability);case.call_function('Clear')
                for actor in reversed(actors):
                    if actor in world.all_actors():report['fixture_actors_removed']&=bool(editor.call_function('DestroyActor',actor))
                    report['fixture_actors_removed']&=actor not in world.all_actors()
                case.remove_from_root()
        report['status']='passed'
    finally:
        if not rooted:cls.remove_from_root()
        report['class_root_restored']=cls.is_rooted()==rooted
    gate(report);return report


if '--check-report' in sys.argv:print(json.dumps(gate(json.loads(Path(sys.argv[sys.argv.index('--check-report')+1]).read_text(encoding='utf-8-sig'))),indent=2))
else:
    import unreal_engine as ue
    result=Path(arg('UEPNativeCostResult'))
    try:
        script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_cost_diagnostics.py'))).resolve();sys.path.insert(0,str(script.parent));report=run(Path(arg('UEPNativeCostStageRoot')).resolve())
    except Exception:report=dict(status='failed',error=traceback.format_exc())
    result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_COST_DIAGNOSTICS_'+report['status'].upper())
    if report['status']!='passed':raise RuntimeError(report['error'])
