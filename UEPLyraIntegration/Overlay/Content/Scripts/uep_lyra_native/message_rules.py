"""Message rules preserving native comparison, float storage and broadcast order."""
import math
import struct


def float32(value):
    try:
        return struct.unpack('f', struct.pack('f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def streak_elimination(history, instigator, target, cast_player, thresholds):
    if instigator != target:
        player = cast_player(instigator)
        if player is not None:
            count = history.get(player, 0) + 1
            history[player] = count
            if count in thresholds:
                yield thresholds[count], player, count
    # Native code clears the target after the synchronous reward broadcast.
    player = cast_player(target)
    if player is not None:
        history.pop(player, None)


def chain_elimination(history, instigator, target, cast_player, thresholds, clock, window):
    if instigator != target:
        player = cast_player(instigator)
        if player is not None:
            now = clock()
            last, count = history.get(player, (0., 1))
            reset = last == 0. or last + window < now
            count = 1 if reset else count + 1
            history[player] = now, count
            if not reset and count in thresholds:
                yield thresholds[count], player, count


def assist_damage(history, instigator, target, magnitude, player_from_object):
    if instigator != target:
        player = player_from_object(instigator)
        if player is not None:
            victim = player_from_object(target)
            if victim is not None:
                damage = history.setdefault(victim, {})
                damage[player] = float32(damage.get(player, 0.) + magnitude)


def assist_elimination(history, instigator, target, cast_player):
    victim = cast_player(target)
    if victim is not None and victim in history:
        for player, damage in history[victim].items():
            if player is not None and player != instigator:
                yield player, victim, damage
        # Preserve native nested-broadcast ordering: clear after all broadcasts.
        history.pop(victim, None)
