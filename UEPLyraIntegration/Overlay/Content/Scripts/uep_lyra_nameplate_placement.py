"""Read the retained native GameFeature component placement, without edits."""
import copy
import unreal_engine as ue

ASSET = "/ShooterCore/Experiences/LAS_ShooterGame_StandardComponents.LAS_ShooterGame_StandardComponents"
CLASSES = {"source": "/Game/UI/Indicators/NameplateSource.NameplateSource_C",
           "manager": "/Game/UI/Indicators/NameplateManagerComponent.NameplateManagerComponent_C"}
_cached = None


def read_placement():
    global _cached
    if _cached is None:
        # FSoftClassProperty reads return a resolved object, not a path. Load
        # only these two known classes before inspecting the retained asset.
        loaded = {ue.load_class(path).get_path_name(): kind for kind, path in CLASSES.items()}
        asset = ue.load_object(ue.find_class("Object"), ASSET)
        rows = {}
        for action in asset.Actions:
            if action.get_class().get_name() != "GameFeatureAction_AddComponents":
                continue
            for entry in action.ComponentList:
                component = entry.ComponentClass
                if component is None or component.get_path_name() not in loaded:
                    continue
                kind = loaded[component.get_path_name()]
                if kind in rows:
                    raise RuntimeError("duplicate native nameplate component placement")
                rows[kind] = {"class": component.get_path_name(), "client": bool(entry.bClientComponent),
                              "server": bool(entry.bServerComponent)}
        if set(rows) != set(CLASSES):
            raise RuntimeError("native nameplate component placement missing")
        _cached = {"asset": ASSET, "rows": rows, "native_asset_read": True, "asset_modified": False}
    return copy.deepcopy(_cached)
