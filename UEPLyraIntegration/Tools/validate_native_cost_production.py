"""Check all five unchanged configured item-cost subobjects via native virtuals."""
import copy
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from uep_lyra_native import tag_stack_costs as policy

ABILITIES=(
    '/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol.GA_Weapon_Fire_Pistol_C',
    '/ShooterCore/Weapons/Rifle/GA_Weapon_Fire_Rifle_Auto.GA_Weapon_Fire_Rifle_Auto_C',
    '/ShooterCore/Weapons/Shotgun/GA_Weapon_Fire_Shotgun.GA_Weapon_Fire_Shotgun_C',
    '/ShooterCore/Items/HealthPickup_Unused/GA_HealPickup.GA_HealPickup_C',
    '/ShooterCore/Weapons/NetShooter_PROTO/GA_WeaponNetShooter.GA_WeaponNetShooter_C',
)


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def require(value,message):
    if not value:raise AssertionError(message)


def run(stage):
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    classes=[ue.load_class(p) for p in ABILITIES];roots=[]
    for target,_,_ in policy.OWNERS:ue.register_declared_mixin(ue.load_class(target))
    for cls in classes:
        if not cls.is_rooted():cls.add_to_root();roots.append(cls)
    world=ue.get_editor_world();library=ue.find_class('UEPNativeCostCase').get_cdo();editor=ue.find_class('EditorSubsystemBlueprintLibrary').get_cdo().call_function('GetEditorSubsystem',ue.find_class('EditorActorSubsystem'))
    report=dict(status='running',error=None,cases=[],configured_consumers=5,original_cost_subobjects_preserved=True,fixture_actors_removed=True,fixtures_saved=False,natural_unused_prototype_activation_claimed=False)
    try:
        for cls in classes:
            costs=cls.get_cdo().get_property('AdditionalCosts');require(len(costs)==1 and costs[0].is_a(ue.find_class('LyraAbilityCost_ItemTagStack')),'configured original cost differs')
            for available in (0,4):
                pairs=[]
                for profile in ('NativeCostFallback','Python'):
                    case=library.call_function('Create',world,cls,available,1,True,True);case.add_to_root();ability=case.Ability;actors=[case.Controller,case.Pawn,case.PlayerState]
                    try:
                        instance_costs=ability.get_property('AdditionalCosts');require(len(instance_costs)==1 and instance_costs[0].is_a(ue.find_class('LyraAbilityCost_ItemTagStack')),'saved original cost was not instanced naturally')
                        ue.set_mixin_profile(ability,profile);result=case.call_function('Probe',True,available>0,True,False,False)
                        outcome=dict(can_pay=bool(result.bCanPay),before=int(result.Before),after=int(result.After),failure_tags=sorted(str(t.TagName) for t in result.Failures.GameplayTags));expected=dict(can_pay=available>0,before=available,after=max(0,available-1),failure_tags=[] if available else ['Ability.ActivateFail.Cost'])
                        require(outcome==expected,'original item-cost configured result differs');counts=copy.deepcopy(policy.metrics(ability));require(counts['checks']>0 if profile=='Python' else counts['native_routes']>0,'configured native cost owner route bypassed')
                        pairs.append(outcome);report['cases'].append(dict(ability=cls.get_path_name(),profile=profile,available=available,outcome=outcome,metrics=counts))
                    finally:
                        ue.clear_mixin_profile(ability);case.call_function('Clear')
                        for actor in reversed(actors):
                            if actor in world.all_actors():report['fixture_actors_removed']&=bool(editor.call_function('DestroyActor',actor))
                            report['fixture_actors_removed']&=actor not in world.all_actors()
                        case.remove_from_root()
                require(pairs[0]==pairs[1],'configured native/Python cost differs')
        report['status']='passed'
    finally:
        for cls in roots:cls.remove_from_root()
        report['class_roots_restored']=all(not c.is_rooted() for c in roots)
    return report


result=Path(arg('UEPNativeCostResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_cost_production.py'))).resolve();sys.path.insert(0,str(script.parent));report=run(Path(arg('UEPNativeCostStageRoot')).resolve())
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_COST_PRODUCTION_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
