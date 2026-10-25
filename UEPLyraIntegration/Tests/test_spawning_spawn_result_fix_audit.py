import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_spawning_spawn_result_fix as audit

class SpawningSpawnResultFixAuditTests(unittest.TestCase):
    def test_cli_only_correction_preserves_native_command_and_source(self):
        before="native launch unchanged\n$gate=Invoke -Arguments @('-B','-X','utf8',$contract,'--report',file) -Name 'Native Spawning destroyed-target semantic gate'\n"
        after=before.replace("'-X','utf8',$contract,'--report'","'-X','utf8','-m',\"uep_lyra_weapons.$contractName\",'--report'").replace('Native Spawning destroyed-target semantic gate','Native Spawning result semantic gate')
        audit.driver_cli_only(before,after)
        for bad in (after.replace('native launch unchanged','different native input'),after+'extra side effect\n',before):
            with self.assertRaises(ValueError):audit.driver_cli_only(before,bad)
    def test_all_three_native_boundaries_remain_explicit(self):
        self.assertEqual(len(audit.SPECS),3)
        self.assertEqual({r[2] for r in audit.SPECS},{'spawning_null_effect_contract','spawning_cue_contract','spawning_destroyed_target_contract'})
