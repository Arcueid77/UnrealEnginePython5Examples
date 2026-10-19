"""Project field forwarding and shatter material/break policy; native Chaos owns physics."""
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={kind:'/Game/Effects/Physics/'+name+'.'+name+'_C' for kind,name in (('example','B_ExamplePhysicsField'),('sphere','B_ShatterSphere'))}
PARENTS=dict(construction='UEPFieldParentConstruction',begin='UEPFieldParentBegin',tick='UEPFieldParentTick')
BIND='UEPShatterBeginNativeBind'
AFTER='UEPShatterAfterNativeBind'


def evidence(actor):
    if not hasattr(actor,'_uep_physics_field'):
        actor._uep_physics_field={p+'_'+m:0 for p in ('python','fallback') for m in ('construction','begin','tick','materials','break')}
        actor._uep_physics_field.update(last_delta=None,diagnostic_fallbacks=0,material_slots=[])
    return actor._uep_physics_field


def parent(actor,kind,*args):
    evidence(actor)['python_'+kind]+=1
    if kind=='tick':evidence(actor)['last_delta']=float(args[0])
    return actor.call_function(PARENTS[kind],*args)


def materials(actor):
    counts=evidence(actor);counts['python_materials']+=1;component=actor.get_property('GeometryCollectionComponent')
    if not valid(component):counts['diagnostic_fallbacks']+=1;return True
    for slot,name in ((0,'DynaMat1'),(1,'DynaMat2')):
        material=component.call_function('CreateDynamicMaterialInstance',slot,None,'None');actor.set_property(name,material);counts['material_slots'].append(slot)
    return False


class LyraExamplePhysicsFieldPythonProfile:
    def UserConstructionScript(self):return parent(self,'construction')
    def ReceiveBeginPlay(self):return parent(self,'begin')
    def ReceiveTick(self,DeltaSeconds):return parent(self,'tick',DeltaSeconds)


class LyraExamplePhysicsFieldBlueprintFallbackProfile:
    def UserConstructionScript(self):evidence(self)['fallback_construction']+=1;return self.call_mixin_original('UserConstructionScript')
    def ReceiveBeginPlay(self):evidence(self)['fallback_begin']+=1;return self.call_mixin_original('ReceiveBeginPlay')
    def ReceiveTick(self,DeltaSeconds):evidence(self)['fallback_tick']+=1;evidence(self)['last_delta']=float(DeltaSeconds);return self.call_mixin_original('ReceiveTick',DeltaSeconds)


class LyraShatterSpherePythonProfile:
    def ReceiveBeginPlay(self):evidence(self)['python_begin']+=1;self.call_function(BIND)
    def AfterBind(self):return materials(self)
    AfterBind.override=AFTER
    def SphereIsBroken(self,BreakEvent):evidence(self)['python_break']+=1;self.set_property('TargetGlowAmt',0.)


class LyraShatterSphereBlueprintFallbackProfile:
    def ReceiveBeginPlay(self):evidence(self)['fallback_begin']+=1;return self.call_mixin_original('ReceiveBeginPlay')
    def AfterBind(self):evidence(self)['fallback_materials']+=1;return True
    AfterBind.override=AFTER
    def SphereIsBroken(self,BreakEvent):evidence(self)['fallback_break']+=1;return self.call_mixin_original('SphereIsBroken',BreakEvent)
