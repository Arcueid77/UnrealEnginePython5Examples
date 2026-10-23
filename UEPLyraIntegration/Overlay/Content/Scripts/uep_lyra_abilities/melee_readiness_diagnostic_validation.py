"""Existing melee matrix with lazy native construction/birth/destruction reads.

Normal class loading and the original handlers stay unchanged. This lane does
not preload the Character, write its CDO, initialize an ASC or repair Health.
"""
from . import melee_trace_network_validation as native
from .lazy_pawn_lifecycle_observation import LazyPawnLifecycleObservation


class Watch:
    def __init__(self,validation):
        if validation.character_default_control is not None:
            raise RuntimeError('lazy melee diagnosis cannot preload a Character treatment')
        validation.early_watch.close()
        self.observation=LazyPawnLifecycleObservation(validation.root,native.peer,validation.run)
        validation.report['lazy_lifecycle_observation']=self.observation.report

    @property
    def files(self):return self.observation.watch.files

    def poll(self):self.observation.poll()

    def close(self):self.observation.close()


native.validation.early_watch=Watch(native.validation)
