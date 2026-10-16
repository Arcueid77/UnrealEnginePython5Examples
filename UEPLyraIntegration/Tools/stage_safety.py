"""Fail closed before authoring assets in a disposable Lyra project."""

from pathlib import Path


def require_authoring_stage(stage_argument, current_content_directory):
    if not stage_argument:
        raise RuntimeError("an explicit disposable stage root is required")
    stage = Path(stage_argument).resolve()
    if not (stage / ".uep-lyra-full-stage.json").is_file():
        raise RuntimeError("weapon HUD authoring requires a marked disposable stage")
    current_project = Path(current_content_directory).resolve().parent
    if current_project != stage:
        raise RuntimeError("current Unreal project differs from the marked authoring stage")
    return stage
