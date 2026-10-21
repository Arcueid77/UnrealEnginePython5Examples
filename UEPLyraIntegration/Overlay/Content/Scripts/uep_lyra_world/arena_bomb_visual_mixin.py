"""Standard Arena bomb materials and local fireball positions."""
import unreal_engine as ue

CLASS = '/TopDownArena/Game/Bombs/B_Bomb_Standard.B_Bomb_Standard_C'
CONSTRUCT = 'UEPArenaBombConstructVisuals'


def lib(name):
    return ue.find_class(name).get_cdo()


def evidence(actor):
    value = getattr(actor, '_uep_arena_bomb_visual', None)
    if value is None:
        value = dict(python_construct=0, python_visuals=0,
                     fallback_construct=0, fallback_visuals=0)
        actor._uep_arena_bomb_visual = value
    return value


def construct(actor):
    material = actor.get_property('SphereMesh').call_function(
        'CreateDynamicMaterialInstance', 0, None, 'None')
    actor.set_property('BombMID', material)
    actor.get_property('CylinderMesh').call_function('SetMaterial', 0, material)
    material.call_function('SetScalarParameterValue', 'InitialTime',
        lib('GameplayStatics').call_function('GetRealTimeSeconds', actor))
    material.call_function('SetScalarParameterValue', 'BombLifespan',
        actor.get_property('BombLifespan'))


def positions(actor):
    # This is a fresh function-local array on every original BP invocation.
    result = []
    directions = actor.get_property('DirectionsExpanding')
    math = lib('KismetMathLibrary')
    for index, radius in enumerate(actor.get_property('DirectionalRadius')):
        for step in range(1, int(radius) + 1):
            # BP array-get returns a default IntPoint when out of range.
            point = directions[index] if index < len(directions) else None
            x, y = (point.X, point.Y) if point is not None else (0, 0)
            x = math.call_function('Multiply_IntInt', int(x), step)
            y = math.call_function('Multiply_IntInt', step, int(y))
            value = ue.FVector(math.call_function('Multiply_DoubleDouble', x, 100.),
                              math.call_function('Multiply_DoubleDouble', y, 100.), 50.)
            if not any(value.x == old.x and value.y == old.y and value.z == old.z
                       for old in result):
                result.append(value)
    return result


class LyraArenaBombVisualPythonProfile:
    def UEPArenaBombConstructVisuals(self):
        evidence(self)['python_construct'] += 1
        construct(self)
        return False

    def ClientUpdateFireballVisuals(self):
        evidence(self)['python_visuals'] += 1
        self.get_property('ExplosionAudio').call_function('Activate', False)
        component = self.get_property('NS_BombFuse1')
        lib('NiagaraDataInterfaceArrayFunctionLibrary').call_function(
            'SetNiagaraArrayVector', component, 'User.PositionArray', positions(self))
        component.call_function('Activate', True)


class LyraArenaBombVisualBlueprintFallbackProfile:
    def UEPArenaBombConstructVisuals(self):
        evidence(self)['fallback_construct'] += 1
        return True

    def ClientUpdateFireballVisuals(self):
        evidence(self)['fallback_visuals'] += 1
        self.call_mixin_original('ClientUpdateFireballVisuals')
