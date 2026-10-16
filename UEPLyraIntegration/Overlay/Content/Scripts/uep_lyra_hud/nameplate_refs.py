"""Narrow optional-reference lookup at native nameplate teardown boundaries."""
from .weapon_observer import valid


def optional_ref(context, field):
    try:
        return getattr(context, field)
    except Exception as error:
        # A referenced async action/Pawn can already be invalid before native
        # GC clears its UPROPERTY. Do not suppress a dead receiver or another
        # property/permission/ABI error.
        if str(error) != "uobject is in invalid state" or not valid(context):
            raise
        return None
