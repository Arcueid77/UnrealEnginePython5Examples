"""Arena bomb collision and lifecycle policy with original native latent actions."""
import unreal_engine as ue
from unreal_engine.enums import EObjectTypeQuery
from unreal_engine.structs import GameplayEffectContextHandle
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid, ability_system

CLASS = '/TopDownArena/Game/Bombs/B_Bomb_Base.B_Bomb_Base_C'
SELECTOR = 'UEPArenaBombBaseMixinProfile'
BLOCK = '/TopDownArena/Game/Environment/B_DestructableBlock.B_DestructableBlock_C'
PICKUP = '/TopDownArena/Game/Pickups/B_TopDownArena_Pickup.B_TopDownArena_Pickup_C'
BONUSES = ('/TopDownArena/Game/Pickups/GE_BombCountUp.GE_BombCountUp_C',
           '/TopDownArena/Game/Pickups/GE_BombRangeUp.GE_BombRangeUp_C')
RESTORE = '/TopDownArena/Game/Bombs/GE_IncrementBombsRemaining.GE_IncrementBombsRemaining_C'
START_FUSE = 'UEPArenaBombNativeStartFuse'
MIN_BURN = 'UEPArenaBombNativeMinimumBurn'
PROPAGATE = 'UEPArenaBombNativePropagationDelay'
HOVER = 'UEPArenaBombNativeHoverDelay'
ATTRIBUTE = 'UEPArenaBombNativeRangeAttribute'
SPAWN = 'UEPArenaBombNativeSpawnBonus'
COSMETIC = 'UEPArenaBombNativeCanExecuteCosmetic'
GATES = dict(begin='UEPArenaBombBegin', destroyed='UEPArenaBombDestroyed',
             overlap='UEPArenaBombEndOverlap', trigger='UEPArenaBombTrigger',
             increment='UEPArenaBombIncrement', propagated='UEPArenaBombAfterPropagation',
             hover='UEPArenaBombAfterHover', fuse='UEPArenaBombFuseStillLit')
METHODS = ('add', 'expand', 'snapshot', 'bonus', 'rep') + tuple(GATES)


def lib(name):
    return ue.find_class(name).get_cdo()


def one(value):
    return value[0] if isinstance(value, tuple) and len(value) == 1 else value


def evidence(actor):
    value = getattr(actor, '_uep_arena_bomb_base', None)
    if value is None:
        value = {prefix+name: 0 for prefix in ('python_', 'fallback_') for name in METHODS}
        value.update(overlaps=0, damage=0, fireballs=0, bonuses=0)
        actor._uep_arena_bomb_base = value
    return value


def apply(component, effect):
    component.call_function('BP_ApplyGameplayEffectToSelf', effect, 0., GameplayEffectContextHandle())


def add_fireball(actor, dx, dy):
    counts = evidence(actor)
    math = lib('KismetMathLibrary')
    radius = int(actor.get_property('RadiusState'))
    relative = ue.FVector(math.call_function('Multiply_DoubleDouble', math.call_function('Multiply_IntInt', dx, radius), 100.),
                          math.call_function('Multiply_DoubleDouble', math.call_function('Multiply_IntInt', dy, radius), 100.), 50.)
    world = math.call_function('Add_VectorVector', relative, actor.call_function('K2_GetActorLocation'))
    result = lib('KismetSystemLibrary').call_function('BoxOverlapActors',
        WorldContextObject=actor, BoxPos=world, BoxExtent=ue.FVector(48., 48., 48.),
        ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery2, EObjectTypeQuery.ObjectTypeQuery1, EObjectTypeQuery.ObjectTypeQuery3],
        ActorClassFilter=None, ActorsToIgnore=[actor])
    blocked, spawn = False, True
    for other in native_outputs('KismetSystemLibrary', 'BoxOverlapActors', result)['OutActors']:
        counts['overlaps'] += 1
        if other.is_a(ue.find_class('StaticMeshActor')):
            blocked, spawn = True, False
        elif other.is_a(ue.load_class(BLOCK)):
            blocked = True
            actor.call_function('SpawnBonus', other)
            other.call_function('K2_DestroyActor')
        elif other.is_a(ue.load_class(CLASS)):
            blocked = True
            other.call_function('TriggerExplosion')
        elif other.is_a(ue.load_class(PICKUP)):
            blocked = True
            other.call_function('K2_DestroyActor')
        else:
            component = ability_system(other)
            if valid(component):
                apply(component, actor.get_property('BombDamageGameplayEffect'))
                counts['damage'] += 1
    if spawn:
        transform = math.call_function('MakeTransform', relative, ue.FRotator(), ue.FVector(1., 1., 1.))
        actor.get_property('FireballCollision').call_function('AddInstance', transform, False)
        counts['fireballs'] += 1
    return dict(SpaceWasBlocked=blocked, SpawnedFireball=spawn)


class LyraArenaBombBasePythonProfile:
    def ServerAddFireballInstance(self, DeltaX, DeltaY):
        evidence(self)['python_add'] += 1
        return add_fireball(self, DeltaX, DeltaY)
    ServerAddFireballInstance.uep_named_outputs = True

    def ServerExpandFireballInAllDirections(self):
        evidence(self)['python_expand'] += 1
        for index, direction in enumerate(self.get_property('DirectionsExpanding')):
            blocked = list(self.get_property('DirectionsBlocked'))
            if index < len(blocked) and blocked[index]:
                continue
            result = self.call_function('ServerAddFireballInstance', int(direction.X), int(direction.Y))
            space, spawned = result
            # Original Array_Set has bSizeToFit=false; short arrays stay short.
            blocked = list(self.get_property('DirectionsBlocked'))
            if index < len(blocked):
                blocked[index] = bool(space)
                self.set_property('DirectionsBlocked', blocked)
            if spawned:
                radii = list(self.get_property('DirectionalRadius'))
                if index < len(radii):
                    radii[index] = int(self.get_property('RadiusState'))
                    self.set_property('DirectionalRadius', radii)
        if one(self.call_function(COSMETIC)):
            self.call_function('ClientUpdateFireballVisuals')

    def SnapshotRange(self):
        evidence(self)['python_snapshot'] += 1
        value, found = self.call_function(ATTRIBUTE, self.get_property('InstigatingPlayerState'))
        if found:
            self.set_property('ExplosionRadius', lib('KismetMathLibrary').call_function('FTrunc', value))

    def SpawnBonus(self, Actor):
        counts = evidence(self)
        counts['python_bonus'] += 1
        math = lib('KismetMathLibrary')
        if math.call_function('Greater_IntInt', self.get_property('PercentageDropBonus'), math.call_function('RandomIntegerInRange', 0, 100)):
            # Array_Random uses the same global RandHelper as RandomInteger.
            effect = ue.load_class(BONUSES[math.call_function('RandomInteger', len(BONUSES))])
            self.call_function(SPAWN, Actor.call_function('K2_GetActorLocation'), effect)
            counts['bonuses'] += 1

    def OnRep_DirectionalRadius(self):
        evidence(self)['python_rep'] += 1
        if not self.call_function('HasAuthority'):
            self.call_function('ClientUpdateFireballVisuals')

    def UEPArenaBombBegin(self):
        evidence(self)['python_begin'] += 1
        instigator = self.call_function('GetInstigator')
        self.set_property('InstigatingPlayerState', instigator.get_property('PlayerState'))
        if instigator.is_a(ue.find_class('Character')):
            instigator.get_property('CapsuleComponent').call_function('IgnoreComponentWhenMoving', self.get_property('CollisionBox'), True)
            self.call_function('SnapshotRange')
            self.call_function(START_FUSE)
        return False

    def UEPArenaBombDestroyed(self):
        evidence(self)['python_destroyed'] += 1
        state = self.get_property('InstigatingPlayerState')
        if valid(state):
            apply(ability_system(state), ue.load_class(RESTORE))
        return False

    def UEPArenaBombEndOverlap(self, OtherActor):
        evidence(self)['python_overlap'] += 1
        instigator = self.get_property('Instigator')
        if OtherActor == instigator and instigator is not None and instigator.is_a(ue.find_class('Character')):
            instigator.get_property('CapsuleComponent').call_function('IgnoreComponentWhenMoving', self.get_property('CollisionBox'), False)
        return False

    def UEPArenaBombTrigger(self):
        evidence(self)['python_trigger'] += 1
        if self.get_property('IsFuseStillBurning'):
            self.set_property('IsFuseStillBurning', False)
            if self.call_function('HasAuthority'):
                self.call_function(MIN_BURN)
        return False

    def UEPArenaBombIncrement(self):
        evidence(self)['python_increment'] += 1
        self.set_property('RadiusState', lib('KismetMathLibrary').call_function('Add_IntInt', self.get_property('RadiusState'), 1))
        self.call_function('ServerExpandFireballInAllDirections')
        self.call_function(PROPAGATE)
        return False

    def UEPArenaBombAfterPropagation(self):
        evidence(self)['python_propagated'] += 1
        if lib('KismetMathLibrary').call_function('EqualEqual_IntInt', self.get_property('ExplosionRadius'), self.get_property('RadiusState')):
            self.call_function(HOVER)
        else:
            self.call_function('IncrementBlastRadius')
        return False

    def UEPArenaBombAfterHover(self):
        counts = evidence(self)
        counts['python_hover'] += 1
        self.call_function('K2_DestroyActor')
        return False

    def UEPArenaBombFuseStillLit(self):
        evidence(self)['python_fuse'] += 1
        return bool(self.get_property('IsFuseStillBurning'))


class LyraArenaBombBaseBlueprintFallbackProfile:
    def ServerAddFireballInstance(self, DeltaX, DeltaY):
        evidence(self)['fallback_add'] += 1
        space, spawned = self.call_mixin_original('ServerAddFireballInstance', DeltaX, DeltaY)
        return dict(SpaceWasBlocked=space, SpawnedFireball=spawned)
    ServerAddFireballInstance.uep_named_outputs = True

    def ServerExpandFireballInAllDirections(self):
        evidence(self)['fallback_expand'] += 1
        self.call_mixin_original('ServerExpandFireballInAllDirections')

    def SnapshotRange(self):
        evidence(self)['fallback_snapshot'] += 1
        self.call_mixin_original('SnapshotRange')

    def SpawnBonus(self, Actor):
        evidence(self)['fallback_bonus'] += 1
        self.call_mixin_original('SpawnBonus', Actor)

    def OnRep_DirectionalRadius(self):
        evidence(self)['fallback_rep'] += 1
        self.call_mixin_original('OnRep_DirectionalRadius')

    def UEPArenaBombBegin(self):
        evidence(self)['fallback_begin'] += 1
        return True

    def UEPArenaBombDestroyed(self):
        evidence(self)['fallback_destroyed'] += 1
        return True

    def UEPArenaBombEndOverlap(self, OtherActor):
        evidence(self)['fallback_overlap'] += 1
        return True

    def UEPArenaBombTrigger(self):
        evidence(self)['fallback_trigger'] += 1
        return True

    def UEPArenaBombIncrement(self):
        evidence(self)['fallback_increment'] += 1
        return True

    def UEPArenaBombAfterPropagation(self):
        evidence(self)['fallback_propagated'] += 1
        return True

    def UEPArenaBombAfterHover(self):
        evidence(self)['fallback_hover'] += 1
        return True

    def UEPArenaBombFuseStillLit(self):
        evidence(self)['fallback_fuse'] += 1
        return one(self.call_mixin_original(GATES['fuse']))
