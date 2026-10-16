"""Test-only observation of native OnLaunched, forwarding the original event."""
import unreal_engine as ue
from .launcher_contract import require

def xyz(value):
    return [float(getattr(value, key)) for key in ("x", "y", "z")]

class LaunchObservation:
    def __init__(self, pawns):
        self.events, self.classes, self.originals, self.closed = [], [], [], False
        self.paths = {pawn.get_path_name() for pawn in pawns}
        observer = self

        class Profile:
            def OnLaunched(self, LaunchVelocity, bXYOverride, bZOverride):
                if self.get_path_name() in observer.paths:
                    observer.events.append({"pawn": self.get_path_name(), "requested": xyz(LaunchVelocity),
                        "xy_override": bool(bXYOverride), "z_override": bool(bZOverride),
                        "before_velocity": xyz(self.call_function("GetVelocity"))})
                self.call_mixin_original("OnLaunched", LaunchVelocity, bXYOverride, bZOverride)

        try:
            for pawn in pawns:
                cls = pawn.get_class()
                if cls in self.classes:
                    continue
                require(not any(row["target_class"] == cls for row in ue.get_registered_mixins()),
                        "launcher observer must not replace an existing Character router")
                self.originals.append((pawn, pawn.find_function("OnLaunched")))
                ue.register_mixin_profile(cls, "UEPLauncherObserve", Profile, make_default=True)
                self.classes.append(cls)
        except Exception:
            self.close()
            raise

    def close(self):
        if self.closed:
            return
        for cls in self.classes:
            require(ue.unregister_mixin(cls), "launcher native observation router restore failed")
        self.classes.clear()
        for pawn, function in self.originals:
            require(pawn.find_function("OnLaunched") == function, "launcher original OnLaunched function not restored")
        self.originals.clear()
        self.closed = True
