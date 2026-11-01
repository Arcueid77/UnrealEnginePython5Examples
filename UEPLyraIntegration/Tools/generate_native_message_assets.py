"""Configure retained processors and the one production Assist class reference."""
from pathlib import Path
import hashlib
import json
import re
import sys
import traceback
import unreal_engine as ue


def argument(name):
    return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'=')),None)


def object_path(value):return value.get_path_name() if value is not None else None


def inspect(stage,output):
    root=stage/'Plugins/GameFeatures/ShooterCore/Content'
    paths=[root/'ShooterCore.uasset',root/'Accolades/EAS_BasicShooterAcolades.uasset',*sorted((root/'Experiences').glob('*.uasset'))]
    containers=[]
    for file in paths:
        package='/ShooterCore/'+file.relative_to(root).with_suffix('').as_posix()
        obj=ue.load_object(ue.find_class('Object'),package+'.'+file.stem)
        if obj.is_a(ue.find_class('Blueprint')):obj=obj.GeneratedClass.get_cdo()
        if 'Actions' not in obj.properties():continue
        actions=[]
        for index,action in enumerate(obj.get_property('Actions')):
            row=dict(index=index,cls=object_path(action.get_class()))
            if 'ComponentList' in action.properties():
                row['entries']=[]
                for slot,entry in enumerate(action.get_property('ComponentList')):
                    item=dict(slot=slot,server=bool(entry.bServerComponent),client=bool(entry.bClientComponent))
                    try:item.update(actor=object_path(entry.ActorClass),component=object_path(entry.ComponentClass))
                    except Exception:item['soft_reference_error']=traceback.format_exc()
                    row['entries'].append(item)
            actions.append(row)
        export=output/(file.stem+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(export)):
            raise RuntimeError('Native container export failed: '+package)
        containers.append(dict(package=package,object=object_path(obj),actions=actions,export=str(export)))
    signatures={}
    for name,functions in {'ElimStreakProcessor':['UEPHandleElimination'],
                           'ElimChainProcessor':['UEPHandleElimination'],
                           'AssistProcessor':['UEPHandleDamage','UEPHandleElimination']}.items():
        cls=ue.find_class(name)
        if cls is None:raise RuntimeError('Native processor class missing: '+name)
        signatures[name]={fn:ue.describe_function(cls,fn) for fn in functions}
    return dict(status='passed',scope='native-entry-and-component-container-inspection',
        runtime_acceptance=False,assets_saved=False,signatures=signatures,containers=containers)


def export_text(obj,path):
    if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(path)):
        raise RuntimeError('Native object export failed')
    data=path.read_bytes()
    return data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')


def generate(stage,output):
    from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    from mixin_graph_gates import semantics
    from uep_lyra_native.message_processors import CLASSES
    baseline=inspect(stage,output)
    ue.unregister_all_mixins()
    for name in ('DA_NativeStreakMixin','DA_NativeChainMixin','DA_NativeAssistMixin'):
        if (stage/('Content/UEPNative/'+name+'.uasset')).exists():raise RuntimeError('Fresh native rule asset family required')
    definitions={
        'streak':('/ShooterCore/Accolades/B_ElimStreakProcessor','Streak','ElimStreakProcessor',2),
        'chain':('/ShooterCore/Accolades/B_ElimChainProcessor','Chain','ElimChainProcessor',2),
        'assist':('/Game/UEPNative/BP_AssistProcessor','Assist','AssistProcessor',3),
    }
    assets=[];details={};blueprints={};save_later=[]
    for kind,(package,prefix,parent,methods) in definitions.items():
        if kind=='assist':bp=ue.create_blueprint(ue.find_class(parent),package);ue.compile_blueprint(bp)
        else:bp=ue.load_object(Blueprint,package+'.'+package.rsplit('/',1)[-1])
        ue.unregister_all_mixins()
        if bp.ParentClass!=ue.find_class(parent):raise RuntimeError('Processor native parent differs')
        before=export_text(bp.GeneratedClass.get_cdo(),output/(kind+'-before.t3d'))
        original_graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
        graph_hashes={g.get_name():semantics(g,n,set()) for g,n in original_graphs}
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
        name='DA_Native'+prefix+'Mixin'
        mixins=ue.create_asset(name,'/Game/UEPNative',UEPPythonMixinSet,factory)
        mixins.DefaultProfile='Python'
        mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.message_processors',
            PythonClass=prefix+p+'Profile') for p in ('Python','NativeFallback')]
        ue.blueprint_configure_mixin(bp,mixins,'Python','PythonMixinProfile')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('Native processor Blueprint did not compile: '+kind)
        after=export_text(bp.GeneratedClass.get_cdo(),output/(kind+'-after.t3d'))
        def retained(text):
            return '\n'.join(line for line in text.splitlines() if not line.strip().startswith(('PythonMixinProfile=','PythonMixinSet=')))
        if retained(before)!=retained(after):raise RuntimeError('Original native processor defaults changed: '+kind)
        if any(semantics(g,n,set())!=graph_hashes[g.get_name()] for g,n in original_graphs):raise RuntimeError('Original processor graph changed')
        ue.register_declared_mixin(bp.GeneratedClass)
        try:
            registered,=[row for row in ue.get_registered_mixins() if row['target_class']==bp.GeneratedClass]
            counts={profile:len(row['functions']) for profile,row in registered['profiles'].items()}
            if counts!={'Python':methods,'NativeFallback':methods}:raise RuntimeError('Native processor profile method counts differ: '+str(counts))
        finally:ue.unregister_all_mixins()
        save_later.extend((bp,mixins));blueprints[kind]=bp
        def relative(pkg):
            return ('Plugins/GameFeatures/ShooterCore/Content/'+pkg[len('/ShooterCore/'):] if pkg.startswith('/ShooterCore/') else 'Content/'+pkg[len('/Game/'):])+'.uasset'
        assets.extend([relative(package),'Content/UEPNative/'+name+'.uasset'])
        details[kind]=dict(parent=object_path(bp.ParentClass),class_path=object_path(bp.GeneratedClass),
            original_defaults_preserved=True,original_graphs_preserved=True,method_counts=counts)
    # The processors are installed by this action set, referenced from the
    # Experiences' ActionSets, rather than by their direct Actions arrays.
    eas_path='/ShooterCore/Accolades/EAS_BasicShooterAcolades.EAS_BasicShooterAcolades'
    eas=ue.load_object(ue.find_class('LyraExperienceActionSet'),eas_path)
    replacements=[]
    for index,action in enumerate(eas.get_property('Actions')):
        if 'ComponentList' not in action.properties():continue
        before=export_text(action,output/('action-'+str(index)+'-before.t3d'))
        matches=re.findall(r'ComponentList\((\d+)\)=.*?ComponentClass="/Script/ShooterCoreRuntime.AssistProcessor"',before)
        if not matches:continue
        if len(matches)!=1:raise RuntimeError('Exactly one original native Assist component reference required')
        # Array getters can expose live struct views. The array setter clears
        # its storage before copying, so detach every entry before writeback.
        slot=int(matches[0]);entries=[entry.clone() for entry in action.get_property('ComponentList')]
        original_flags=(bool(entries[slot].bServerComponent),bool(entries[slot].bClientComponent),int(entries[slot].AdditionFlags))
        entries[slot].ComponentClass=blueprints['assist'].GeneratedClass
        action.set_property('ComponentList',entries)
        after=export_text(action,output/('action-'+str(index)+'-after.t3d'))
        expected=before.replace('/Script/ShooterCoreRuntime.AssistProcessor',CLASSES['assist'])
        if before.count('/Script/ShooterCoreRuntime.AssistProcessor')!=1 or after!=expected:
            raise RuntimeError('Component action changed beyond the one Assist class reference')
        current=action.get_property('ComponentList')[slot]
        if original_flags!=(bool(current.bServerComponent),bool(current.bClientComponent),int(current.AdditionFlags)):
            raise RuntimeError('Original component role/addition flags changed')
        replacements.append(dict(action=index,slot=slot,original_flags=original_flags,before=before,after=after))
    if len(replacements)!=1:raise RuntimeError('One production Assist replacement in the original action set required')
    for obj in [*save_later,eas]:obj.save_package()
    assets.append('Plugins/GameFeatures/ShooterCore/Content/Accolades/EAS_BasicShooterAcolades.uasset')
    return dict(status='passed',scope='CPP01-native-message-processor-authoring',runtime_acceptance=False,
        assets_saved=True,assets=assets,processors=details,production_assist_replacements=replacements,
        event_entrypoints=4,native_subscriptions_and_cleanup_preserved=True,
        baseline_signatures=baseline['signatures'],asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=argument('UEPNativeMessageAssetsResult')
if result is None:raise RuntimeError('An explicit native message authoring result is required')
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_message_assets.py'))).resolve()
    sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeMessageStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()))
    report=inspect(stage,Path(result).parent) if '-UEPNativeMessageInspectOnly' in sys.argv else generate(stage,Path(result).parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
Path(result).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_MESSAGE_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
