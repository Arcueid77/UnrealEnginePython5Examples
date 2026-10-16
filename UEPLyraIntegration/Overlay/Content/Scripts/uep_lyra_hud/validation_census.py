"""Bounded native UI census settling, never hides persistent duplicates."""
class UniqueWidgetCensus:
    def __init__(self):
        self.epoch, self.since, self.samples = None, None, 0

    def ready(self, paths, epoch, now):
        if self.epoch != epoch:
            self.epoch, self.since, self.samples = epoch, None, 0
        if len(paths) <= 1:
            self.since, self.samples = None, 0
            return len(paths) == 1
        if self.since is None:
            self.since = now
        self.samples += 1
        # Native UI extension removal can follow construction in the next
        # frame. Do not accept either object during that interval. A pause in
        # asset loading is not four observations of persistent membership.
        if self.samples >= 4 and now-self.since >= 2.0:
            raise RuntimeError("persistent duplicate production UI owner: "+repr(paths))
        return False
