"""Select both inherited interface defaults before disposable Actor creation."""
from contextlib import contextmanager
SELECTOR='UEPHeroDefaultMixinProfile'

@contextmanager
def defaults(cls,profile):
    cdo=cls.get_cdo();previous={name:cdo.get_property(name) for name in (SELECTOR,'PythonMixinProfile') if name in cdo.properties()}
    try:
        for name in previous:cdo.set_property(name,profile)
        yield
    finally:
        for name,value in previous.items():cdo.set_property(name,value)
