"""Two real owners cancel/rebind only after authority sees native RPC/tasks."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from .dash_tasks_network_validation import Client as TasksClient, Server as TasksServer
from .auto_respawn_helpers_network_validation import token
from .dash_rpc_input_network_validation import task_state, delta, payload
from .dash_activation_mixin import evidence as activation_evidence
from .dash_local_direction_mixin import evidence as local_evidence
from .jump_network_validation import arg
from .dash_tasks_network_lifecycle_contract import client, require


def ready_name(peer, index): return peer+"-"+str(index)+"-native-active.json"


class Client(TasksClient):
    def __init__(self, result, peer, run):
        super().__init__(result, peer, run); self.report["network_lifecycle_interventions"] = True
    def trial_begin_evidence(self):
        super().trial_begin_evidence(); self.intervened = False; self.quiet_tasks = None
    def intent(self):
        super().intent()
        if self.phase == "observe":
            self.activation_time = self.game_time()
            after = copy.deepcopy(activation_evidence(self.dash))
            self.actual_entry = dict(counters=delta(after, self.activation_before), last=after["last"] if self.profile == "Python" else None)
            local = copy.deepcopy(local_evidence(self.dash))
            self.actual_local = dict(counters=delta(local, self.local_before), before=self.local_fields_before,
                stored=payload(self.dash), last=local["last"] if self.profile == "Python" else None)
    def observe(self):
        if not self.intervened:
            confirmation = token(self.root, ready_name(self.peer, self.index), self.run)
            elapsed = self.game_time()-self.activation_time
            if confirmation is not None and elapsed >= .07:
                require(confirmation["peer"] == self.peer and confirmation["index"] == self.index and confirmation["rpc_and_tasks_active"] is True,
                    "foreign/invalid authority native activity confirmation")
                state = task_state(self.dash)
                require(self.dash.get_property("bIsActive") and state["root"] and state["montage"], "native intervention missed active task window")
                self.intervened = True
                value = dict(authority_ready_observed=True, root_before=True, montage_before=True, active_before=True,
                    elapsed=elapsed, native_entry="GameplayAbility.K2_CancelAbility" if self.index%2 == 0 else "ue.set_mixin_profile")
                if self.index%2 == 0: self.dash.call_function("K2_CancelAbility")
                else:
                    ue.set_mixin_profile(self.dash, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                    value["new_profile"] = str(ue.get_mixin_profile(self.dash))
                value["active_after"] = bool(self.dash.get_property("bIsActive")); self.row["network_lifecycle"] = value
            require(self.intervened or elapsed < .22, "authority activity confirmation missed real root-motion window")
        super().observe()
    def quiet(self):
        value = self.producer.finish()
        if self.quiet_tasks is None: self.quiet_tasks = copy.deepcopy(value)
        require(value == self.quiet_tasks, "late task/producer work after owner lifecycle intervention")
        super().quiet()
    def trial_end_evidence(self):
        super().trial_end_evidence()
        self.row["activation_entry"] = copy.deepcopy(self.actual_entry)
        self.row["local_direction"] = copy.deepcopy(self.actual_local)
        self.row["network_lifecycle"]["quiet_unchanged"] = True
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; client(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_TASKS_NETWORK_LIFECYCLE_SHUTDOWN_"+self.report["status"].upper())


class Server(TasksServer):
    def __init__(self, result, run):
        super().__init__(result, run); self.report["network_lifecycle_interventions"] = True
    def observe(self):
        super().observe()
        if self.current is None: return
        current = self.current; owner = self.owners[current["target"]]; state = task_state(owner["ability"])
        if current.get("received") is not None and owner["ability"].get_property("bIsActive") and state["root"] and state["montage"]:
            if not current.get("authority_ready_sent"):
                current["authority_ready_sent"] = True
                atomic_write(self.root/ready_name(current["target"], current["index"]),
                    dict(run_id=self.run, peer=current["target"], index=current["index"], rpc_and_tasks_active=True))
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_TASKS_NETWORK_LIFECYCLE_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDashTasksNetworkLifecycleResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDashTasksNetworkLifecycleResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
