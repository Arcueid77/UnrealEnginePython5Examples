"""Original component BP choice policy, native cosmetic ownership/replication."""
import copy
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart

SELECTION = "/Game/Characters/Cosmetics/B_CharacterSelection.B_CharacterSelection_C"
RANDOM = "/Game/Characters/Cosmetics/B_PickRandomCharacter.B_PickRandomCharacter_C"
MANNY = "/Game/Characters/Cosmetics/B_Manny.B_Manny_C"
QUINN = "/Game/Characters/Cosmetics/B_Quinn.B_Quinn_C"
_stats = dict(selections=0, random_selections=0, errors=[])


def snapshot(): return copy.deepcopy(_stats)


def add(component, cls):
    # Native controller component owns the handle, Pawn changes, cleanup and
    # native FastArray replication. There is no Python-spawned replacement body.
    component.call_function("AddCharacterPart", LyraCharacterPart(PartClass=cls, CollisionMode=0))


def select(component):
    actors, = ue.find_class("GameplayStatics").get_cdo().call_function("GetAllActorsOfClass", component, ue.find_class("LyraCharacter"))
    parts = list(component.AvailableCharacterParts)
    # Use the original native integer remainder (including its empty-list
    # diagnostic/default behavior), not Python's incompatible modulo-zero error.
    index = int(ue.find_class("KismetMathLibrary").get_cdo().call_function("Percent_IntInt", len(actors), len(parts)))
    add(component, parts[index] if 0 <= index < len(parts) else None)
    _stats["selections"] += 1


def random_select(component):
    choose_quinn = bool(ue.find_class("KismetMathLibrary").get_cdo().call_function("RandomBool"))
    add(component, ue.load_class(QUINN if choose_quinn else MANNY))
    _stats["random_selections"] += 1


class LyraCharacterSelectionPythonProfile:
    def ReceiveBeginPlay(self):
        try: select(self)
        except Exception as error: _stats["errors"].append(str(error)); raise


class LyraRandomCharacterPythonProfile:
    def ReceiveBeginPlay(self):
        try: random_select(self)
        except Exception as error: _stats["errors"].append(str(error)); raise


class LyraCharacterSelectionBlueprintFallbackProfile:
    def ReceiveBeginPlay(self): self.call_mixin_original("ReceiveBeginPlay")


class LyraRandomCharacterBlueprintFallbackProfile:
    def ReceiveBeginPlay(self): self.call_mixin_original("ReceiveBeginPlay")
