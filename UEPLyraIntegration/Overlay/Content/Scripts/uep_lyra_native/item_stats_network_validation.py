"""Native initial-stat callbacks and replicated item tag stacks for two owners."""
import copy
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.inventory_pad_network_state import services
from .inventory_network_validation import Network as InventoryNetwork
from .inventory_network_contract import PLAN
from .message_validation import arg
from .message_validation_contract import require
from . import item_stats as policy
from .item_stats_network_contract import validate_stats


class Network(InventoryNetwork):
    def __init__(self):
        self.stats_boot=[];self.stats_cleaned=False;self.stats_profile=arg('UEPNativeStatsProfile')
        super().__init__()
        require(self.profile=='Python','previous inventory/quickbar policies must stay fixed in Python')
        self.report.update(stats_profile=self.stats_profile,previous_inventory_profile='Python',stats_policy_metrics={},native_replicated_stat_rows=None,stats_cdo_overrides_restored=False,stats_class_roots_restored=False)
        for target in policy.CLASSES:
            cls=ue.load_class(target);ue.register_declared_mixin(cls);rooted=cls.is_rooted()
            if not rooted:cls.add_to_root()
            cdo=cls.get_cdo();ue.set_mixin_profile(cdo,self.stats_profile);self.stats_boot.append((cls,cdo,rooted))

    def stat_rows(self,controller):
        items=services(controller)[0].call_function('GetAllItems');rows=[]
        if len(items)!=3:return None
        for item in items:
            definition=item.get_property('ItemDef')
            if definition is None:return None
            values={};expected={}
            for fragment in definition.get_cdo().get_property('Fragments'):
                if fragment.is_a(ue.find_class('InventoryFragment_SetStats')):
                    for value in fragment.call_function('UEPGetInitialStats'):
                        tag=str(value.Tag.TagName);expected[tag]=max(0,int(value.Count));values[tag]=int(item.call_function('GetStatTagStackCount',value.Tag))
            if len(expected)!=3 or expected!=values:return None
            rows.append(dict(definition=definition.get_path_name(),values=values))
        return rows

    def server_prepare(self):
        before={cls.get_path_name():copy.deepcopy(policy.metrics(cdo)) for cls,cdo,rooted in self.stats_boot}
        super().server_prepare()
        key='python_selected' if self.stats_profile=='Python' else 'native_selected';other='native_selected' if self.stats_profile=='Python' else 'python_selected'
        selected=sum(policy.metrics(cdo)[key]-before[cls.get_path_name()][key] for cls,cdo,rooted in self.stats_boot)
        other_calls=sum(policy.metrics(cdo)[other]-before[cls.get_path_name()][other] for cls,cdo,rooted in self.stats_boot)
        applied=sum(policy.metrics(cdo)['python_applied']-before[cls.get_path_name()]['python_applied'] for cls,cdo,rooted in self.stats_boot)
        require(selected==4 and other_calls==0 and applied==(4 if self.stats_profile=='Python' else 0),'actual server pickup did not select the initial-stat owner policy exactly once per new item')
        rows={p:self.stat_rows(owner['controller']) for p,owner in self.fixture.owners.items()};require(all(rows.values()),'authority initial item stats differ')
        self.report.update(native_stat_creation_calls=selected,other_stat_creation_calls=other_calls,python_stat_application_calls=applied,native_replicated_stat_rows=rows)

    def client_permit(self):
        if self.position==len(PLAN) and self.report['native_replicated_stat_rows'] is None:
            rows=self.stat_rows(self.controller)
            if rows is None:return
            self.report['native_replicated_stat_rows']=rows
        super().client_permit()

    def cleanup(self):
        if not self.stats_cleaned:
            self.report['stats_policy_metrics']={cls.get_path_name():copy.deepcopy(policy.metrics(cdo)) for cls,cdo,rooted in self.stats_boot}
            for cls,cdo,rooted in self.stats_boot:
                ue.clear_mixin_profile(cdo)
                if not rooted:cls.remove_from_root()
            self.report['stats_cdo_overrides_restored']=all(str(ue.get_mixin_profile(cdo))=='Python' for cls,cdo,rooted in self.stats_boot)
            self.report['stats_class_roots_restored']=all(cls.is_rooted()==rooted for cls,cdo,rooted in self.stats_boot);self.stats_cleaned=True
        super().cleanup()

    def finish(self,error=None):
        if self.finished:return
        super().finish(error)
        (ue.log_error if self.report['status']=='failed' else ue.log)('UEP_NATIVE_STATS_NETWORK_'+('FAILED' if self.report['status']=='failed' else 'PASSED'))

    def finalize(self):
        super().finalize()
        if self.report['status']=='passed':
            try:validate_stats(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_STATS_NETWORK_SHUTDOWN_'+self.report['status'].upper())


network=Network();ticker=ue.add_ticker(network.tick)
