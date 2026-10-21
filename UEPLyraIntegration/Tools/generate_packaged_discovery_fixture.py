"""Author fresh Actor/imported-Actor/Widget classes in the marked test stage."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

sys.path.insert(0, str(Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_packaged_discovery_fixture.py'))).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name):
    return next(a.split('=', 1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def connect(a, pin, b, other):
    a.node_find_pin(pin).make_link_to(b.node_find_pin(other))


def command(bp):
    for name in ('BlueprintCalls', 'PythonCalls'):
        ue.blueprint_add_member_variable(bp, name, 'int')
    ue.compile_blueprint(bp)
    graph = ue.blueprint_add_function(bp, 'RunCommand');entry = graph.Nodes[0]
    read = graph.graph_add_node_variable_get('BlueprintCalls')
    add = graph.graph_add_node_call_function(ue.find_class('KismetMathLibrary').Add_IntInt)
    add.node_find_pin('B').default_value = '1'
    write = graph.graph_add_node_variable_set('BlueprintCalls')
    connect(entry, 'then', write, 'execute');connect(read, 'BlueprintCalls', add, 'A');connect(add, 'ReturnValue', write, 'BlueprintCalls')
    ue.compile_blueprint(bp)


def generate():
    stage = require_authoring_stage(arg('UEPDiscoveryStage'), ue.convert_relative_path_to_full(ue.get_content_dir()))
    root = arg('UEPDiscoveryRoot')
    if not root.startswith('/Game/UEPInterop/PackageDiscovery_') or '..' in root:
        raise ValueError('fresh task-owned fixture root required')
    names = ('Main', 'Companion', 'Widget', 'Caller', 'MixinSet')
    if any((stage/'Content'/root.removeprefix('/Game/')/(name+'.uasset')).exists() for name in names):
        raise ValueError('preserve existing fixtures')
    factory = ue.new_object(ue.find_class('DataAssetFactory'));factory.DataAssetClass = ue.find_class('UEPPythonMixinSet')
    mixin = ue.create_asset('MixinSet', root, ue.find_class('UEPPythonMixinSet'), factory)
    mixin.DefaultProfile = 'Python'
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule='uep_packaged_discovery_profiles', PythonClass=p+'Profile') for p in ('Python', 'BlueprintFallback')]
    bps = {name: ue.create_blueprint(ue.find_class('Actor'), root+'/'+name) for name in ('Main', 'Companion')}
    widget_factory = ue.new_object(ue.find_class('WidgetBlueprintFactory'))
    widget_factory.ParentClass = ue.find_class('UserWidget')
    bps['Widget'] = ue.create_asset('Widget', root, ue.find_class('WidgetBlueprint'), widget_factory)
    for bp in bps.values():
        command(bp);ue.blueprint_configure_mixin(bp, mixin, 'Python', 'PythonMixinProfile');ue.compile_blueprint(bp)
    for name in ('Companion', 'Widget'):
        ue.blueprint_add_member_variable(bps['Main'], name+'Class', EdGraphPinType(PinCategory='class', PinSubCategoryObject=ue.find_class('Object')))
    ue.compile_blueprint(bps['Main'])
    for name in ('Companion', 'Widget'):
        bps['Main'].GeneratedClass.get_cdo().set_property(name+'Class', bps[name].GeneratedClass)
    ue.unregister_all_mixins()
    caller = ue.create_blueprint(ue.find_class('Actor'), root+'/Caller')
    ue.blueprint_add_member_variable(caller, 'Target', EdGraphPinType(PinCategory='object', PinSubCategoryObject=bps['Main'].GeneratedClass));ue.compile_blueprint(caller)
    graph = ue.blueprint_add_function(caller, 'Dispatch');entry = graph.Nodes[0]
    target = graph.graph_add_node_variable_get('Target');call = graph.graph_add_node_call_function(bps['Main'].GeneratedClass.RunCommand)
    connect(entry, 'then', call, 'execute');connect(target, 'Target', call, 'self');ue.compile_blueprint(caller)
    # Caller remains separate: loading Main must import the other two packages.
    ue.unregister_all_mixins()
    for bp in [*bps.values(), caller]:
        if int(bp.Status) == 2:
            raise RuntimeError('fixture blueprint compilation failed')
        bp.save_package()
    mixin.save_package()
    return dict(status='passed', fixture_only=True, runtime_acceptance=False, root=root,
                classes={name: root+'/'+name+'.'+name+'_C' for name in bps},
                caller=root+'/Caller.Caller_C', assets=[str(stage/'Content'/root.removeprefix('/Game/')/(name+'.uasset')) for name in names])


try:
    report = generate()
except Exception:
    report = dict(status='failed', error=traceback.format_exc())
Path(arg('UEPDiscoveryAuthorResult')).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
(ue.log if report['status'] == 'passed' else ue.log_error)('UEP_PACKAGED_DISCOVERY_AUTHOR_'+report['status'].upper())
if report['status'] != 'passed':
    raise RuntimeError(report['error'])
