"""Collectible/HUD runtime layered around the mixed Blueprint character."""

import math
import traceback

import unreal_engine as ue

from uep_third_person.gameplay import ThirdPersonGameplay
from uep_third_person.hud import ThirdPersonHUD
from uep_third_person.utils import gameplay_objects, is_valid


class MixinThirdPersonSession:
    def __init__(self, world, game_mode, controller, pawn, generation):
        self.world = world
        self.game_mode = game_mode
        self.controller = controller
        self.pawn = pawn
        self.generation = generation
        self.gameplay = ThirdPersonGameplay(world, pawn)
        self.hud = ThirdPersonHUD(
            title="UEP 0.7  |  BLUEPRINT MIXIN",
            status_label="BP CLASS + PYTHON MOVE/AIM",
        )
        self.hud.attach(world)
        self.closed = False

    def tick(self, delta_seconds, pawn):
        self.pawn = pawn
        velocity = pawn.get_actor_velocity()
        pawn.PythonAnimationSpeed = math.sqrt(
            (velocity.x * velocity.x) + (velocity.y * velocity.y)
        )
        pawn.PythonAnimationState = "blueprint_anim"
        self.gameplay.tick(delta_seconds, pawn)
        self.hud.update(self.gameplay.progress, pawn)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.hud.detach()
        self.gameplay.close()


class MixinThirdPersonRuntime:
    """Maintain one Python gameplay session without replacing UE classes."""

    def __init__(self):
        self.session = None
        self.session_generation = 0
        self.last_error = None
        self.active = True

    def _matches_session(self, world, controller, pawn):
        return (
            self.session is not None
            and not self.session.closed
            and is_valid(self.session.world)
            and is_valid(self.session.pawn)
            and self.session.world == world
            and self.session.controller == controller
            and self.session.pawn == pawn
        )

    def close_session(self):
        if self.session is not None:
            self.session.close()
        self.session = None

    def shutdown(self):
        self.active = False
        self.close_session()

    def tick(self, delta_seconds):
        if not self.active:
            return False
        try:
            world, game_mode, controller, pawn = gameplay_objects()
            if not all(
                is_valid(value)
                for value in (world, game_mode, controller, pawn)
            ):
                if self.session is not None and not is_valid(self.session.world):
                    self.close_session()
                return True

            if not self._matches_session(world, controller, pawn):
                self.close_session()
                self.session_generation += 1
                self.session = MixinThirdPersonSession(
                    world,
                    game_mode,
                    controller,
                    pawn,
                    self.session_generation,
                )
                ue.log("UEP_MIXIN_THIRD_PERSON_WORLD_READY")

            self.session.tick(delta_seconds, pawn)
            return True
        except Exception:
            self.last_error = traceback.format_exc()
            ue.log_error(self.last_error)
            self.close_session()
            return False
