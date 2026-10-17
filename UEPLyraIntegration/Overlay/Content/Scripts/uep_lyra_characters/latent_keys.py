"""Distinct stable keys for this Actor's Python-owned native latent sites."""
import uuid


def allocate(actor, site, count):
    if count < 1: raise ValueError("latent site needs a positive key count")
    sites = getattr(actor, "_uep_character_latent_keys", None)
    if sites is None: sites = {}; actor._uep_character_latent_keys = sites
    if site not in sites:
        used = {value for keys in sites.values() for value in keys}; keys = []
        while len(keys) < count:
            value = (uuid.uuid4().int & 0x7fffffff) or 1
            if value not in used: keys.append(value); used.add(value)
        sites[site] = keys
    if len(sites[site]) != count: raise ValueError("latent site key shape changed")
    return list(sites[site])
