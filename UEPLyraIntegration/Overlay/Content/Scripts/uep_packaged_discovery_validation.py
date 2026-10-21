"""Opt-in cooked, fresh-process discovery without any registration API call."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_packaged_discovery_contract import validate


def arg(name):
    return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def check(ok, message):
    if not ok:
        raise AssertionError(message)


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPPackagedDiscoveryResult'));self.started=time.monotonic();self.phase='world'
        self.assets=json.loads(Path(arg('UEPPackagedDiscoveryAssets')).read_text(encoding='utf-8-sig'))
        check(self.assets['status']=='passed' and self.assets['root'].startswith('/Game/UEPInterop/PackageDiscovery_'),'owned authored fixture required')
        self.report=dict(status='running',explicit_registration_called=False,full_acceptance=False,classes={})
        self.objects=[];self.roots=[];self.loaded={};self.finished=False

    def write(self):
        self.path.write_text(json.dumps(self.report,indent=2)+'\n',encoding='utf-8')

    def registered(self):
        return {row['target_class'].get_path_name() for row in ue.get_registered_mixins()}

    def tick(self, delta):
        try:
            check(time.monotonic()-self.started<180,'discovery fixture timed out in '+self.phase)
            expected=set(self.assets['classes'].values())
            if self.phase=='world':
                worlds=[w for w in ue.all_worlds() if w.get_world_type() in (1,3)]
                if not worlds:return True
                self.world=worlds[0]
                check(not expected & self.registered(),'fresh classes loaded before the explicit package load')
                self.report['fresh_classes_initially_absent']=True
                self.loaded['Main']=ue.load_class(self.assets['classes']['Main'])
                check(self.loaded['Main'] is not None,'Main class missing from cooked content')
                self.phase='registration';return True
            if self.phase=='registration':
                if not expected <= self.registered():return True
                self.report['automatic_imported_classes_discovered']=True
                main=self.loaded['Main'].get_cdo()
                self.loaded.update({name:main.get_property(name+'Class') for name in ('Companion','Widget')})
                check({cls.get_path_name() for cls in self.loaded.values()}==expected,'imported class references differ')
                self.exercise();self.finish();return False
        except Exception:
            self.finish(traceback.format_exc());return False
        return True

    def make(self, name, cls):
        obj=ue.new_object(cls) if name=='Widget' else self.world.actor_spawn(cls)
        self.objects.append((obj,name=='Widget'))
        if name=='Widget' and not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        return obj

    @staticmethod
    def counts(obj):
        return {name:int(obj.get_property(name)) for name in ('BlueprintCalls','PythonCalls')}

    def exercise(self):
        caller_cls=ue.load_class(self.assets['caller']);caller=self.world.actor_spawn(caller_cls);self.objects.append((caller,False))
        for name,cls in self.loaded.items():
            first,second=self.make(name,cls),self.make(name,cls)
            second.set_property('PythonMixinProfile','BlueprintFallback')
            first.call_function('RunCommand');second.call_function('RunCommand')
            check(self.counts(first)==dict(BlueprintCalls=0,PythonCalls=1),'Python dispatch fell through')
            check(self.counts(second)==dict(BlueprintCalls=1,PythonCalls=0),'original fallback failed')
            if name=='Main':
                for target in (first,second):caller.set_property('Target',target);caller.call_function('Dispatch')
                check(self.counts(first)==dict(BlueprintCalls=0,PythonCalls=2) and self.counts(second)==dict(BlueprintCalls=2,PythonCalls=0),'precompiled caller bypassed the selected profile')
                self.report['precompiled_blueprint_caller_routed']=True
            same=first.get_class()==second.get_class()==cls
            ue.unregister_mixin(cls)
            first.call_function('RunCommand');second.call_function('RunCommand')
            self.report['classes'][name]=dict(same_unreal_class=same,native_original_restored=True,
                metaclass=cls.get_class().get_name(),python=self.counts(first),fallback=self.counts(second))

    def cleanup(self):
        for cls in self.loaded.values():
            if cls.is_valid() and cls.get_path_name() in self.registered():ue.unregister_mixin(cls)
        for obj,widget in reversed(self.objects):
            if not widget and obj.is_valid():obj.actor_destroy()
        for obj in self.roots:
            if obj.is_valid() and obj.is_rooted():obj.remove_from_root()
        self.report['cleanup_complete']=not set(self.assets['classes'].values()) & self.registered()

    def finish(self, error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_PACKAGED_DISCOVERY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_PACKAGED_DISCOVERY_SHUTDOWN_'+self.report['status'].upper())


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
