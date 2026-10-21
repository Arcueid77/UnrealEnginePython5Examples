"""Arena bomb grid, occupancy and ability commit policy with native GAS tasks."""
import unreal_engine as ue
from unreal_engine.enums import EObjectTypeQuery
from unreal_engine.structs import GameplayTag, GameplayTagContainer
from uep_lyra_abilities.melee_trace_mixin import native_outputs

CLASS = '/TopDownArena/Game/Bombs/GA_DropBomb.GA_DropBomb_C'
BOMB = '/TopDownArena/Game/Bombs/B_Bomb_Base.B_Bomb_Base_C'
STANDARD = '/TopDownArena/Game/Bombs/B_Bomb_Standard.B_Bomb_Standard_C'
FAILURE = 'Ability.ActivateFail.CellAlreadyContainsBomb'
AFTER_MONTAGE = 'UEPArenaDropBombAfterMontage'
AFTER_SPAWN = 'UEPArenaDropBombAfterSpawn'
SPAWN = 'UEPArenaDropBombNativeSpawn'


def lib(name):
    return ue.find_class(name).get_cdo()


def one(value):
    return value[0] if isinstance(value, tuple) and len(value) == 1 else value


def evidence(ability):
    value = getattr(ability, '_uep_arena_drop_bomb', None)
    if value is None:
        value = {p+k: 0 for p in ('python_', 'fallback_') for k in ('location', 'can', 'activate', 'spawn_end')}
        value.update(commit_success=0, commit_failed=0, authority_spawns=0, occupied=0)
        ability._uep_arena_drop_bomb = value
    return value


class LyraArenaDropBombPythonProfile:
    def GetBombSpawnLocation(self, AvatarActor):
        evidence(self)['python_location'] += 1
        position = AvatarActor.call_function('K2_GetActorLocation')
        return lib('KismetMathLibrary').call_function('Vector_SnappedToGrid', ue.FVector(position.x, position.y, 0.), 100.)

    def K2_CanActivateAbility(self, ActorInfo, Handle):
        counts = evidence(self)
        counts['python_can'] += 1
        position = one(self.call_function('GetBombSpawnLocation', ActorInfo.AvatarActor))
        result = lib('KismetSystemLibrary').call_function('SphereOverlapActors', WorldContextObject=self,
            SpherePos=position, SphereRadius=32., ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery2],
            ActorClassFilter=ue.load_class(BOMB), ActorsToIgnore=[])
        blocked = bool(native_outputs('KismetSystemLibrary', 'SphereOverlapActors', result)['ReturnValue'])
        counts['occupied'] += int(blocked)
        tags = GameplayTagContainer(GameplayTags=[GameplayTag(TagName=FAILURE)]) if blocked else GameplayTagContainer()
        return dict(ReturnValue=not blocked, RelevantTags=tags)
    K2_CanActivateAbility.uep_named_outputs = True

    def UEPArenaDropBombAfterMontage(self):
        counts = evidence(self)
        counts['python_activate'] += 1
        if not self.call_function('K2_CommitAbility'):
            counts['commit_failed'] += 1
            self.call_function('K2_EndAbility')
            return False
        counts['commit_success'] += 1
        position = one(self.call_function('GetBombSpawnLocation', self.call_function('GetAvatarActorFromActorInfo')))
        if self.call_function('K2_HasAuthority'):
            counts['authority_spawns'] += 1
            self.call_function(SPAWN, position)
        return False

    def UEPArenaDropBombAfterSpawn(self):
        counts = evidence(self)
        counts['python_spawn_end'] += 1
        self.call_function('K2_EndAbility')
        return False


class LyraArenaDropBombBlueprintFallbackProfile:
    def GetBombSpawnLocation(self, AvatarActor):
        evidence(self)['fallback_location'] += 1
        return one(self.call_mixin_original('GetBombSpawnLocation', AvatarActor))

    def K2_CanActivateAbility(self, ActorInfo, Handle):
        evidence(self)['fallback_can'] += 1
        allowed, tags = self.call_mixin_original('K2_CanActivateAbility', ActorInfo, Handle)
        return dict(ReturnValue=allowed, RelevantTags=tags)
    K2_CanActivateAbility.uep_named_outputs = True

    def UEPArenaDropBombAfterMontage(self):
        evidence(self)['fallback_activate'] += 1
        return True

    def UEPArenaDropBombAfterSpawn(self):
        evidence(self)['fallback_spawn_end'] += 1
        return True
