"""Correlate native legacy RPC logs with native Actor GUID cleanup records.

Actor names only join records within one peer. Native GUIDs, independently
recorded by the read-only identity module and UActorChannel::CleanUp, identify
the replicated object across peers. Local timer callbacks cannot emit a native
FObjectReplicator 'Received RPC' record.
"""
import json
import re
from .grenade_detonate_contract import require

HEADER = re.compile(r"LogNetTraffic:\s+(?:Channel )?Actor (.+):\s*$")
RECEIVE = re.compile(r"LogRepTraffic:\s+Received RPC: Detonate\s*$")
SEND = re.compile(r"LogNetTraffic:\s+Sent RPC: B_Grenade_C (.+)::Detonate \[")
CLEANUP = re.compile(r"LogNetTraffic:\s+UActorChannel::CleanUp \(ChIndex: \d+\): B_Grenade_C (.+) \| NetGuid: (\d+) \| Reason: (\w+)")
MARKER = re.compile(r"LogPython:\s+UEP_GRENADE_FLIGHT_BODY (\{.*\})\s*$")


def parse(text, server=False):
    current, received, sent, cleanups, markers = None, {}, {}, [], []
    number = 0
    for number, line in enumerate(text.splitlines(), 1):
        match = HEADER.search(line)
        if match:
            full = match[1]
            current = full[len("B_Grenade_C "):] if full.startswith("B_Grenade_C ") else None
        if RECEIVE.search(line) and current is not None:
            received.setdefault(current, []).append(number)
        match = SEND.search(line)
        if match: sent.setdefault(match[1], []).append(number)
        match = CLEANUP.search(line)
        if match:
            cleanups.append(dict(actor=match[1], wire_id=match[2], reason=match[3], line=number))
            if current == match[1]: current = None
        match = MARKER.search(line)
        if match: markers.append(dict(line=number, **json.loads(match[1])))
        require(not ("Rejected unwanted function Detonate" in line and "B_Grenade_C" in line), "native receiver rejected Detonate")
    result = {}
    for marker in markers:
        actor, guid = marker["actor"], marker["wire_id"]
        require(isinstance(guid, str) and guid.isdecimal() and int(guid) > 0, "body marker lacks native lossless GUID")
        require(guid not in result, "native grenade body logged more than once")
        prior_close = max((row["line"] for row in cleanups if row["actor"] == actor and row["line"] < marker["line"] and row["wire_id"] != guid), default=0)
        native_closes = [row for row in cleanups if row["actor"] == actor and row["wire_id"] == guid and row["line"] > marker["line"] and row["reason"] == "Destroyed"]
        if not server:
            require(len(native_closes) == 1, "client Actor GUID/destruction log correlation missing")
        end = max((row["line"] for row in native_closes), default=number+1)
        outgoing = [line for line in sent.get(actor, []) if prior_close < line < end]
        incoming = [line for line in received.get(actor, []) if prior_close < line < end]
        require(len(outgoing) == 2 if server else len(incoming) == 1, "native two-connection send or exact client receive count differs")
        result[guid] = dict(actor=actor, body_line=marker["line"], sent_lines=outgoing, received_lines=incoming,
            cleanup_lines=[row["line"] for row in native_closes], position=marker["position"],
            rpc_before_body=None if server else incoming[0] < marker["line"], native_guid=guid)
    require(result, "native grenade RPC/body log witness absent")
    return result
