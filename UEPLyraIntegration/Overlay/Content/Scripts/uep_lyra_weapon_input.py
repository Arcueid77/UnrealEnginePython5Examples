"""Test-only native aim setup; never writes weapon or ability state."""

import unreal_engine as ue


def aim_above_players(controller):
    # UEP's legacy FRotator positional order is Roll, Pitch, Yaw (not UE's
    # constructor order). Explicit fields prevent a rolled-camera false proof.
    rotation = ue.FRotator()
    rotation.pitch = 80.0
    rotation.yaw = 0.0
    rotation.roll = 0.0
    controller.call_function("SetControlRotation", rotation)


def aim_snapshot(controller):
    rotation = controller.call_function("GetControlRotation")
    return {name: float(getattr(rotation, name)) for name in ("pitch", "yaw", "roll")}
