"""Existing native wire identity; paths and local clocks are not peer keys."""


def read(value):
    import unreal_engine as ue
    cls=ue.find_class("UEPLyraNetworkIdentityLibrary")
    if cls is None: raise RuntimeError("compiled read-only network identity module required")
    data=cls.get_cdo().call_function("ReadNetworkIdentity",value)
    return dict(valid=bool(data.bValid),transport=str(data.Transport),wire_id=str(data.WireId),
        object_path=str(data.ObjectPath),world_path=str(data.WorldPath),driver_path=str(data.DriverPath),
        local_role=int(data.LocalRole),world_seconds=float(data.WorldSeconds),actor_age_seconds=float(data.ActorAgeSeconds))


def key(value):
    if not isinstance(value,dict) or value.get("valid") is not True: return None
    transport,wire=value.get("transport"),value.get("wire_id")
    if transport not in ("Legacy","Iris") or not isinstance(wire,str) or not wire.isdecimal() or int(wire)==0:
        raise ValueError("valid native network identity requires transport and lossless decimal wire id")
    return transport,wire


def same(left,right):
    value=key(left)
    return value is not None and value==key(right)
