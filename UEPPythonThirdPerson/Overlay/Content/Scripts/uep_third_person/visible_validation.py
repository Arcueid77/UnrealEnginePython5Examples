"""Opt-in rendered frames from the same native-input gameplay smoke test."""

import atexit
import hashlib
import json
import math
from pathlib import Path

import unreal_engine as ue
from unreal_engine.classes import KismetSystemLibrary

from .utils import command_line_value, gameplay_objects, is_valid


class VisibleValidation:
    def __init__(self, smoke, directory):
        self.smoke = smoke
        self.directory = Path(directory)
        self.frames = []
        self.errors = []
        atexit.register(self.write)

    def tick(self, delta):
        phase = self.smoke.phase
        if phase not in ("moving", "looking", "jumping") or any(item["phase"] == phase for item in self.frames):
            return True
        if self.smoke.phase_elapsed < 0.15:
            return True
        try:
            world, _, controller, pawn = gameplay_objects()
            if not all(is_valid(value) for value in (world, controller, pawn)):
                return True
            image = self.directory / (phase + ".png")
            if image.exists():
                raise RuntimeError("refusing to overwrite rendered evidence " + str(image))
            location = pawn.get_actor_location()
            frame = {"phase": phase, "image": str(image),
                     "character_class": pawn.get_class().get_name(),
                     "location": [location.x, location.y, location.z]}
            mesh = pawn.Mesh
            animation = mesh.get_anim_instance()
            frame["animation_instance"] = animation.get_class().get_name() if is_valid(animation) else None
            frame["mesh_path"] = mesh.get_path_name()
            frame["animation_instance_path"] = animation.get_path_name() if is_valid(animation) else None
            frame["mesh_animation_enabled"] = bool(mesh.bEnableAnimation)
            frame["mesh_animation_paused"] = bool(mesh.bPauseAnims)
            frame["mesh_component_tick_enabled"] = bool(mesh.call_function("IsComponentTickEnabled"))
            if frame["animation_instance"] == "AnimSingleNodeInstance":
                asset = animation.call_function("GetAnimationAsset")
                frame["animation_asset"] = asset.get_path_name() if is_valid(asset) else None
                frame["animation_position"] = float(mesh.call_function("GetPosition"))
                frame["animation_playing"] = bool(mesh.call_function("IsPlaying"))
            self.frames.append(frame)
            KismetSystemLibrary.ExecuteConsoleCommand(
                world, 'Shot SHOWUI -nosuffix filename="' + str(image) + '"', controller)
        except Exception as error:
            self.errors.append(str(error))
            ue.log_error("UEP_THIRD_PERSON_VISIBLE_FAILED " + str(error))
            return False
        return True

    def write(self):
        # Only file evidence is inspected at interpreter exit; no UObject use.
        smoke = json.loads(Path(self.smoke.result_path).read_text(encoding="utf-8-sig"))
        teardown = smoke.get("teardown") or {}
        if (smoke.get("status") != "passed" or smoke.get("error")
                or teardown.get("runtime_active") is not False
                or teardown.get("session_released") is not True):
            self.errors.append("gameplay completion/explicit teardown evidence missing")
        for frame in self.frames:
            if frame.get("animation_instance") == "AnimSingleNodeInstance":
                position = frame.get("animation_position", 0.0)
                expected = "MM_Jump.MM_Jump" if frame["phase"] == "jumping" else "BS_Idle_Walk_Run.BS_Idle_Walk_Run"
                if (not str(frame.get("animation_asset") or "").endswith(expected)
                        or not math.isfinite(position) or position <= 0
                        or frame.get("animation_playing") is not True):
                    self.errors.append("native animation asset/time did not advance during " + frame["phase"])
            path = Path(frame["image"])
            if not path.exists():
                self.errors.append("missing rendered image " + str(path))
                continue
            data = path.read_bytes()
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                self.errors.append("invalid rendered image " + str(path))
            frame["sha256"] = hashlib.sha256(data).hexdigest()
        if {frame["phase"] for frame in self.frames} != {"moving", "looking", "jumping"}:
            self.errors.append("missing required gameplay frame")
        report = {"schema_version": 1, "status": "failed" if self.errors else "passed",
                  "rendered": True, "frames": self.frames, "errors": self.errors}
        (self.directory / "visible.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        marker = "UEP_THIRD_PERSON_VISIBLE_SHUTDOWN_" + ("FAILED" if self.errors else "PASSED")
        (ue.log_error if self.errors else ue.log)(marker)


def start_visible_if_requested(smoke):
    directory = command_line_value("-UEPThirdPersonVisualDirectory=")
    if directory is None:
        return None, None
    if smoke is None:
        raise RuntimeError("rendered validation requires an enabled gameplay smoke test")
    probe = VisibleValidation(smoke, directory)
    return probe, ue.add_ticker(probe.tick)
