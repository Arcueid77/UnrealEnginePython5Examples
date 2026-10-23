"""Ten unchanged native UI fixtures share one World and one actual VM shutdown."""
import atexit
import importlib
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from .ui_regression_suite_contract import SCENARIOS,defer_finish_exit,require,validate


class Suite:
    def __init__(self,result):
        self.path=Path(result);self.started=time.monotonic();self.index=0;self.instances=[];self.finished=False;self.quiet=0
        self.report=dict(status='running',error=None,cases=[],deferred_case_exit_requests=0,native_world_reused=False,
            final_native_exit_requested=False,finalized_during_actual_interpreter_exit=False,full_acceptance=False,network_acceptance=False,
            packaged_runtime=False,pixels_tested=False,callbacks_replayed=False,original_scenario_assertions_changed=False)
        self.start_case()

    def write(self):atomic_write(self.path,self.report)

    def start_case(self):
        name,marker=SCENARIOS[self.index];module=importlib.import_module('uep_lyra_hud.'+name+'_validation')
        row=dict(scenario=name,status='running',error=None,exit_requests=0,original_finish_code_preserved=False,report_file=name+'.json')
        def requested_exit():
            row['exit_requests']+=1;self.report['deferred_case_exit_requests']+=1
        original=module.Validation.finish;finish=defer_finish_exit(original,requested_exit)
        row['original_finish_code_preserved']=finish.__code__ is original.__code__
        cls=type('CombinedUI_'+name,(module.Validation,),dict(finish=finish))
        current=cls(str(self.path.parent/row['report_file']))
        self.active=(module,current,row,marker);self.instances.append(self.active);self.report['cases'].append(row)
        ue.log('UEP_UI_SUITE_CASE_STARTED '+name);self.write()

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<1600.,'Combined native UI suite timeout')
            module,current,row,marker=self.active
            if not current.finished:
                current.tick(delta)
                row['phase']=getattr(current,'phase',None)
                self.report['active_scenario']=row['scenario'];self.write()
                return True
            require(current.report['status']=='awaiting_shutdown' and current.report['error'] is None,'Native UI scenario failed: '+str(current.report.get('error')))
            require(row['exit_requests']==1,'Original finish exit request missing or duplicated')
            # Fail early on the exact existing semantic contract. The actual
            # finalizer still runs after the real interpreter shutdown.
            module.validate(dict(current.report,status='passed'))
            row['native_world_path']=current.world.get_path_name()
            require(len({item[2]['native_world_path'] for item in self.instances if 'native_world_path' in item[2]})==1,'A UI scenario changed the native World')
            row.update(status='awaiting_shutdown',error=None)
            self.quiet+=1
            if self.quiet<12:return True
            self.quiet=0;self.index+=1
            if self.index<len(SCENARIOS):self.start_case()
            else:self.report['native_world_reused']=True;self.finish()
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        if error:
            module,current,row,marker=self.active
            if not current.finished:current.finish(error)
            row.update(status='failed',error=error)
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error,final_native_exit_requested=True)
        self.write();(ue.log_error if error else ue.log)('UEP_UI_SUITE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        for module,current,row,marker in self.instances:
            try:current.finalize()
            except Exception:current.report.update(status='failed',error=traceback.format_exc());current.write()
            row.update(status=current.report['status'],error=current.report['error'])
        self.report['finalized_during_actual_interpreter_exit']=True
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report,self.path.parent)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_UI_SUITE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPUIRegressionSuiteResult=')),None)
if result:
    suite=Suite(result);atexit.register(suite.finalize);ticker=ue.add_ticker(suite.tick)
