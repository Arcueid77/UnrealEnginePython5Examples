"""Test-only class defaults; native GAS/input/inventory/networking remain intact."""
import atexit, copy, json, traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_abilities import autoreload_mixin, reload_magazine_mixin, quickslot_mixin
from uep_lyra_abilities.reload_magazine_contract import WEAPONS as RELOAD_WEAPONS
from . import weapon_ability_fire_mixin
from .weapon_ability_fire_contract import WEAPONS as FIRE_WEAPONS
from .integrated_profile_contract import validate, PROFILES


class ProfileGuard:
    def __init__(self, profile, peer, result):
        if profile not in PROFILES: raise RuntimeError("unsupported integrated gameplay Profile")
        self.profile, self.peer, self.path = profile, peer, Path(result)
        self.selectors, self.roots, self.parents, self.seen = [], [], {}, {}
        paths = dict(fire=[weapon_ability_fire_mixin.CLASS]+[FIRE_WEAPONS[name] for name in ("pistol", "rifle")],
            reload=[reload_magazine_mixin.CLASS]+[RELOAD_WEAPONS[name][0] for name in ("pistol", "rifle")],
            autoreload=[autoreload_mixin.CLASS], quickslot=[quickslot_mixin.CLASS])
        self.report = dict(peer=peer, selected_profile=profile, class_families=paths, observations=[],
            selectors_restored=False, owned_roots_released=False, gameplay_state_written=False, shutdown=None)
        try:
            for family, names in paths.items():
                for index, path in enumerate(names):
                    cls = ue.load_class(path)
                    if not cls.is_rooted(): cls.add_to_root(); self.roots.append(cls)
                    cdo = cls.get_cdo()
                    if "PythonMixinProfile" not in cdo.properties(): raise RuntimeError("missing retained Profile selector: "+path)
                    self.selectors.append((cls, str(cdo.get_property("PythonMixinProfile"))))
                    cdo.set_property("PythonMixinProfile", profile)
                    if index == 0: self.parents[family] = cls
        except Exception:
            self.close(); raise
        # Registered before the existing HUD finalizer: LIFO runs that finalizer
        # first, then this pure-data check verifies gameplay scopes in its report.
        atexit.register(self.finalize)

    def observe(self, controller, world_token):
        pawn = controller.get_controlled_pawn()
        if not valid(pawn): return
        asc = ability_system(pawn)
        if not valid(asc): return
        for spec in asc.get_property("ActivatableAbilities").Items:
            for ability in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances):
                if not valid(ability): continue
                for family, cls in self.parents.items():
                    if not ability.is_a(cls): continue
                    selected = str(ue.get_mixin_profile(ability))
                    if selected != self.profile: raise RuntimeError("integrated gameplay selected wrong Profile: "+ability.get_path_name()+"/"+selected)
                    key = (str(world_token), ability.get_path_name())
                    self.seen[key] = dict(world_token=str(world_token), controller=controller.get_path_name(), pawn=pawn.get_path_name(),
                        ability=ability.get_path_name(), native_class=ability.get_class().get_path_name(), family=family,
                        profile=selected, authority=bool(int(pawn.call_function("GetLocalRole")) == 3))
                    if family == "fire": self.seen[key]["fire_counts"] = copy.deepcopy(getattr(ability, "_uep_weapon_ability_fire", None))

    def close(self):
        for cls, original in self.selectors: cls.get_cdo().set_property("PythonMixinProfile", original)
        self.report["selectors_restored"] = all(str(cls.get_cdo().get_property("PythonMixinProfile")) == original for cls, original in self.selectors)
        for cls in self.roots: cls.remove_from_root()
        self.report["owned_roots_released"] = all(not cls.is_rooted() for cls in self.roots)
        self.report["observations"] = list(self.seen.values())
        return copy.deepcopy(self.report)

    def finalize(self):
        try:
            report = json.loads(self.path.read_text(encoding="utf-8-sig"))
            if "integrated_gameplay" not in report: return
            value = report["integrated_gameplay"]
            value["shutdown"] = dict(reload=reload_magazine_mixin.snapshot(), autoreload=autoreload_mixin.snapshot(), quickslot=quickslot_mixin.snapshot())
            validate(value, self.profile)
            if report["status"] != "passed" or report["shutdown"]["status"] != "passed": raise RuntimeError("integrated HUD/native report failed")
            atomic_write(self.path, report); ue.log("UEP_INTEGRATED_GAMEPLAY_SHUTDOWN_PASSED")
        except Exception:
            report = json.loads(self.path.read_text(encoding="utf-8-sig"))
            report["status"] = "failed"; report["error"] = traceback.format_exc()
            atomic_write(self.path, report); ue.log_error("UEP_INTEGRATED_GAMEPLAY_SHUTDOWN_FAILED")
