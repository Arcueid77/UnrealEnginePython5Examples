"""Serialize native Shot requests; Unreal retains one request per frame.

Issued commands are not rendering acceptance. The outer driver still requires
every advertised PNG, hashes it and leaves actual inspection separate.
"""
from collections import deque


class FrameScreenshotQueue:
    def __init__(self, emit):
        self.emit = emit
        self.pending = deque()
        self.requested = []
        self.issued = []

    def request(self, path, *context):
        if not isinstance(path, str) or not path or path in self.requested:
            raise RuntimeError("invalid or duplicate screenshot request")
        self.pending.append((path, context))
        self.requested.append(path)

    def drain_one(self):
        if not self.pending:
            return
        path, context = self.pending[0]
        self.emit(path, *context)
        self.pending.popleft()
        self.issued.append(path)

    def snapshot(self):
        return {"requested": list(self.requested), "issued": list(self.issued), "pending_count": len(self.pending),
                "rendered_files_verified": False, "mode": "one-native-Shot-per-engine-frame"}


def validate_queue(value, images, peer):
    if (value["mode"] != "one-native-Shot-per-engine-frame" or value["pending_count"] != 0 or
            value["rendered_files_verified"] is not False or value["requested"] != value["issued"] or
            len(value["issued"]) != len(set(value["issued"])) or value["issued"] != images):
        raise RuntimeError("screenshot queue incomplete or unsupported rendering claim")
    if (peer == "server" and images) or (peer != "server" and not images):
        raise RuntimeError("wrong screenshot queue ownership")
