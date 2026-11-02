"""Exercise native inventory creation, Const owner routing and staged map fixtures."""
import copy
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,UEPInitialItemStat
from uep_lyra_native import item_stats as policy


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def require(value,message):
    if not value:raise AssertionError(message)
def stats(item,rows):return {str(r.Tag.TagName):int(item.call_function('GetStatTagStackCount',r.Tag)) for r in rows}
def row(tag,value):return UEPInitialItemStat(Tag=GameplayTag(TagName=tag),Count=value)


def run(stage):
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    classes=[ue.load_class(p) for p in policy.CLASSES];roots=[];overrides=[];actor=None;fixture=None;fixture_originals=None
    report=dict(status='running',error=None,production_cases=[],boundary_cases=[],detached_cases=[],direct_policy_calls=False,fixture_assets_saved=False,native_inventory_creation_used=True,native_replication_replaced=False,exception_injection_tested=False)
    try:
        for cls in classes:
            if not cls.is_rooted():cls.add_to_root();roots.append(cls)
            ue.register_declared_mixin(cls)
        world=ue.get_editor_world();actor=world.actor_spawn(ue.find_class('Actor'))
        inventory=actor.add_actor_component(ue.find_class('LyraInventoryManagerComponent'),'UEPInitialStatInventory')
        def create(cls,profile,expected,name,kind):
            cdo=cls.get_cdo();ue.set_mixin_profile(cdo,profile);overrides.append(cdo);before=copy.deepcopy(policy.metrics(cdo));item=inventory.call_function('AddItemDefinition',cls,1)
            require(item is not None,'native inventory failed to create an item')
            values=stats(item,[row(t,0) for t in expected]);after=policy.metrics(cdo)
            selected=after['python_selected']-before['python_selected'] if profile=='Python' else after['native_selected']-before['native_selected']
            require(selected==1 and after['python_applied']-before['python_applied']==(1 if profile=='Python' else 0),'native fragment did not dispatch exactly once to the selected owner policy')
            require(values==expected,'initial native tag stacks differ: '+name)
            target=report['production_cases'] if kind=='production' else report['boundary_cases'];target.append(dict(name=name,profile=profile,definition=cls.get_path_name(),values=values,selected_calls=selected,native_item=item.get_path_name()))
            inventory.call_function('RemoveItemInstance',item);require(not inventory.call_function('GetAllItems'),'native inventory item cleanup failed')
        for profile in ('NativeFallback','Python'):
            for cls in classes:
                fragment,=[f for f in cls.get_cdo().get_property('Fragments') if f.is_a(ue.find_class('InventoryFragment_SetStats'))]
                expected={str(r.Tag.TagName):max(0,int(r.Count)) for r in fragment.call_function('UEPGetInitialStats')}
                for repeat in range(2):create(cls,profile,expected,cls.get_name()+'-'+str(repeat),'production')
        fixture=ue.create_blueprint(ue.find_class('LyraInventoryItemDefinition'),'/Game/UEPValidation/BP_InitialStatBoundary')
        mixins=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPNative/DA_InitialStatsMixin.DA_InitialStatsMixin');ue.blueprint_configure_mixin(fixture,mixins,'Python');ue.compile_blueprint(fixture)
        fixture_cls=fixture.GeneratedClass;fixture_cls.add_to_root();roots.append(fixture_cls);ue.register_declared_mixin(fixture_cls)
        library=ue.find_class('UEPNativeStatsFixture').get_cdo();ammo='Lyra.ShooterGame.Weapon.MagazineAmmo';spare='Lyra.ShooterGame.Weapon.SpareAmmo';size='Lyra.ShooterGame.Weapon.MagazineSize'
        specifications=[('empty',[]),('zero_negative',[(ammo,0),(spare,-5)]),('mixed',[(ammo,5),(size,12),(spare,0)]),('duplicate_last_wins',[(ammo,3),(ammo,7)]),('int32_max',[(ammo,2147483647)])]
        for name,entries in specifications:
            result=library.call_function('ConfigureDefinition',fixture_cls,[row(t,n) for t,n in entries]);values=result if isinstance(result,tuple) else (result,);fragment=next(v for v in values if hasattr(v,'get_class') and v.is_a(ue.find_class('InventoryFragment_SetStats')))
            snapshot=list(fragment.call_function('UEPGetInitialStats'));expected={str(r.Tag.TagName):max(0,int(r.Count)) for r in snapshot}
            for profile in ('NativeFallback','Python'):create(fixture_cls,profile,expected,name,'boundary')
        # No item definition means there is no Blueprint owner to route to.
        result=library.call_function('ConfigureDefinition',fixture_cls,[row(ammo,4)]);values=result if isinstance(result,tuple) else (result,);fragment=next(v for v in values if hasattr(v,'get_class') and v.is_a(ue.find_class('InventoryFragment_SetStats')))
        for profile in ('NativeFallback','Python'):
            cdo=fixture_cls.get_cdo();ue.set_mixin_profile(cdo,profile);before=copy.deepcopy(policy.metrics(cdo));item=ue.new_object(ue.find_class('LyraInventoryItemInstance'),actor)
            library.call_function('ApplyWithoutDefinition',fragment,item);require(stats(item,[row(ammo,0)])=={ammo:4} and policy.metrics(cdo)==before,'missing-definition native fallback changed')
            report['detached_cases'].append(dict(profile=profile,original_native_callback=True,values={ammo:4}))
        registered=next(r for r in ue.get_registered_mixins() if r['target_class']==fixture_cls);fixture_originals={p:v['python_class'] for p,v in registered['profiles'].items()}
        class Partial:
            def UEPUsesPythonInitialStats(self):return True
            def UEPInitializeItemStats(self,fragment,instance):instance.call_function('AddStatTagStack',GameplayTag(TagName=ammo),1)
        ue.register_mixin_profile(fixture_cls,'Python',Partial);ue.set_mixin_profile(fixture_cls.get_cdo(),'Python')
        item=inventory.call_function('AddItemDefinition',fixture_cls,1);require(stats(item,[row(ammo,0)])=={ammo:1},'native loop replayed after handled Python callback');inventory.call_function('RemoveItemInstance',item)
        report['handled_python_callback_no_native_replay']=True
        report['status']='passed'
    finally:
        if fixture_originals:
            for name,cls in fixture_originals.items():ue.register_mixin_profile(fixture.GeneratedClass,name,cls)
        for owner in overrides:
            if owner.is_valid():ue.clear_mixin_profile(owner)
        if fixture:ue.clear_mixin_profile(fixture.GeneratedClass.get_cdo())
        report['profile_overrides_cleared']=all(not owner.is_valid() or str(ue.get_mixin_profile(owner))=='Python' for owner in overrides)
        for cls in roots:cls.remove_from_root()
        report['class_roots_restored']=all(not cls.is_rooted() for cls in roots)
        if actor:
            subsystem=ue.find_class('EditorSubsystemBlueprintLibrary').get_cdo().call_function('GetEditorSubsystem',ue.find_class('EditorActorSubsystem'))
            destroyed=bool(subsystem.call_function('DestroyActor',actor))
            report['fixture_actor_destroyed']=destroyed and actor not in world.all_actors()
    return report


result=Path(arg('UEPNativeStatsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_stats.py'))).resolve();sys.path.insert(0,str(script.parent));report=run(Path(arg('UEPNativeStatsStageRoot')).resolve())
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_STATS_BOUNDARIES_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
