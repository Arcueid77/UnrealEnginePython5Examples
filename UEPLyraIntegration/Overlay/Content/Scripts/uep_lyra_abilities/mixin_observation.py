"""Test observers augment existing profiles and restore their exact classes/functions."""
import unreal_engine as ue


def install(cls,function,callback):
    existing=next((r for r in ue.get_registered_mixins() if r['target_class']==cls),None);profiles={k:v['python_class'] for k,v in existing['profiles'].items()} if existing else {};original=cls.get_cdo().find_function(function)
    for name,base in (profiles.items() if profiles else [('UEPTemporaryObserver',object)]):
        attributes={k:v for parent in reversed(base.__mro__) if parent is not object for k,v in vars(parent).items() if k not in ('__module__','__dict__','__weakref__','__doc__','__qualname__')};key=next((k for k,v in attributes.items() if callable(v) and getattr(v,'override',k)==function),function);handler=attributes.get(key)
        def wrap(previous):
            def invoke(owner,*args):
                callback(owner,*args)
                return previous(owner,*args) if previous is not None else owner.call_mixin_original(function,*args)
            invoke.override=function;return invoke
        attributes[key]=wrap(handler);ue.register_mixin_profile(cls,name,type('Observed'+function+name,(),attributes),make_default=not profiles)
    return dict(cls=cls,function=function,original=original,profiles=profiles)


def restore(token):
    if token['profiles']:
        for name,base in token['profiles'].items():ue.register_mixin_profile(token['cls'],name,base)
        current=next(r for r in ue.get_registered_mixins() if r['target_class']==token['cls'])
        if not all(current['profiles'][name]['python_class'] is base for name,base in token['profiles'].items()):return False
    elif not ue.unregister_mixin(token['cls']):return False
    return token['cls'].get_cdo().find_function(token['function'])==token['original']
