"""Additional local gateway witnesses cannot be replaced by an old RPC pass."""
import copy
import unittest
from test_dash_rpc_input_contract import reports as rpc_reports
from uep_lyra_abilities.dash_local_direction_contract import network


def reports():
    values = rpc_reports()
    for authority in values["server"]["cases"]:
        row = values[authority["target"]]["cases"][authority["index"]]; python = row["profile"] == "Python"
        row["local_direction"] = dict(counters=dict(python_calls=int(python), fallback_calls=int(not python)),
            before=copy.deepcopy(authority["stores_before_rpc"]), stored=copy.deepcopy(row["chosen"]), last=None)
        if python:
            chosen = row["chosen"]; row["local_direction"]["last"] = dict(ai=False, facing=[1., 0., 0.],
                last_input=copy.deepcopy(chosen["direction"]), movement=copy.deepcopy(chosen["direction"]), bias=row["name"] == "forward",
                direction=copy.deepcopy(chosen["direction"]), montage=chosen["montage"], projected=None, projection_succeeded=None)
        authority["client"]["row"] = copy.deepcopy(row)
        authority["local_direction_counters"] = dict(python_calls=0, fallback_calls=0)
    return values


class LocalDirectionContractModels(unittest.TestCase):
    def setUp(self): self.values = reports()
    def reject(self):
        with self.assertRaises(RuntimeError): network(self.values)
    def test_complete_shape_is_not_native_execution(self): self.assertEqual(network(self.values)["native_local_direction_preparations"], 8)
    def test_old_rpc_pass_cannot_substitute_for_local_python(self): self.values["A"]["cases"][2]["local_direction"]["counters"]["python_calls"] = 0; self.reject()
    def test_local_python_cannot_also_fall_through(self): self.values["A"]["cases"][2]["local_direction"]["counters"]["fallback_calls"] = 1; self.reject()
    def test_stored_native_fields_must_match_computed_result(self): self.values["A"]["cases"][2]["local_direction"]["last"]["direction"] = [0., 1., 0.]; self.reject()
    def test_unused_remote_local_preparation_stays_noop(self): self.values["server"]["cases"][0]["local_direction_counters"]["fallback_calls"] = 1; self.reject()
    def test_native_player_must_not_take_ai_branch(self): self.values["A"]["cases"][2]["local_direction"]["last"]["ai"] = True; self.reject()
    def test_stale_native_values_cannot_mask_local_stores(self):
        row = self.values["A"]["cases"][2]; row["local_direction"]["before"] = copy.deepcopy(row["chosen"]); self.reject()
    def test_original_forward_bias_is_required(self): self.values["A"]["cases"][2]["local_direction"]["last"]["movement"] = [0., 1., 0.]; self.reject()
    def test_explicit_network_entry_and_commandlet_disarming(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPDashLocalDirectionNetworkResult=x"]), "uep_lyra_abilities.dash_local_direction_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPDashLocalDirectionNetworkResult=x"]))
