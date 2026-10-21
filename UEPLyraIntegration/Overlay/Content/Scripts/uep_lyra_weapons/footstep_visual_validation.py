"""Capture a native rendered view during unchanged actual-player locomotion."""
import atexit, hashlib, math, sys, traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_network_io import read_json
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .footstep_locomotion_validation import Validation as Locomotion
from .footstep_locomotion_contract import require
from .footstep_visual_contract import validate


class Validation(Locomotion):
    def __init__(self, result):
        super().__init__(result)
        self.report.update(images=[], visual_inspection_completed=False, original_view_target_restored=False, effect_render_visibility_restored=False)
        self.camera = None
        self.before_requested = self.after_requested = False
        self.camera_ready = None
        self.step_count_seen = 0
        self.step_seen_time = None
        self.effect_control = None

    def begin(self):
        super().begin()
        if self.role == 'client':
            self.original_view = self.controller.call_function('GetViewTarget')
            self.original_hidden_actors = list(self.controller.get_property('HiddenActors'))
            self.camera = self.world.actor_spawn(ue.find_class('CameraActor'))
            self.camera.get_component_by_type(ue.find_class('CameraComponent')).call_function('SetFieldOfView', 55.)

    def configure_camera(self):
        location = self.pawn.call_function('K2_GetActorLocation')
        half = float(self.pawn.get_property('CapsuleComponent').call_function('GetScaledCapsuleHalfHeight'))
        yaw = float(self.controller.call_function('GetControlRotation').yaw);angle = math.radians(yaw)
        target = ue.FVector(location.x+math.cos(angle)*200., location.y+math.sin(angle)*200., location.z-half)
        rotation = ue.find_class('KismetMathLibrary').get_cdo().call_function('MakeRotator', Roll=0., Pitch=-90., Yaw=yaw)
        require(self.camera.call_function('K2_TeleportTo', ue.FVector(target.x, target.y, target.z+250.), rotation), 'native observer camera placement failed')
        self.controller.call_function('SetViewTargetWithBlend', self.camera, 0., 0, 0., False)
        parts = self.pawn.get_component_by_type(ue.find_class('LyraPawnComponent_CharacterParts'))
        part_actors = list(parts.call_function('GetCharacterPartActors')) if valid(parts) else []
        self.controller.set_property('HiddenActors', list(dict.fromkeys(self.original_hidden_actors+[self.pawn]+part_actors)))
        self.observer_hidden_actors = list(self.controller.get_property('HiddenActors'))
        self.report['character_render_hidden_in_observer_view_only'] = True
        self.camera_ready = self.game_time()
        self.report['camera_target'] = [float(target.x), float(target.y), float(target.z)]
        self.report['camera_height'] = 250.

    def screenshot(self, kind, projected=0):
        file = self.root/(self.requested_profile.lower()+'-footstep-'+kind+'.png')
        self.statics.call_function('GetPlayerController', self.world, 0)
        ue.find_class('KismetSystemLibrary').get_cdo().call_function('ExecuteConsoleCommand', self.world,
            'Shot -nosuffix filename="'+str(file)+'"', self.controller)
        current = self.current
        self.report['images'].append(dict(kind=kind, path=str(file), requested_game_time=self.game_time(),
            successful_footsteps_at_capture=sum(row['hit'] for row in current['foot']), projected_hits_in_view=projected,
            native_motion_samples=current['foot'][-3:]))

    def projected_hits(self):
        count = 0
        size = native_outputs('PlayerController', 'GetViewportSize', self.controller.call_function('GetViewportSize'))
        width, height = int(size['SizeX']), int(size['SizeY'])
        self.report['actual_viewport_size'] = [width, height]
        for row in self.current['foot']:
            if not row['hit']:
                continue
            point = ue.FVector(*row['location'])
            value = self.controller.call_function('ProjectWorldLocationToScreen', WorldLocation=point, bPlayerViewportRelative=False)
            fields = native_outputs('PlayerController', 'ProjectWorldLocationToScreen', value)
            screen = fields['ScreenLocation']
            if fields['ReturnValue'] and .08*width <= screen.x <= .92*width and .08*height <= screen.y <= .92*height:
                count += 1
        return count

    def observe_client(self):
        if self.effect_control is not None and self.effect_control != 'complete':
            self.input_value(0.)
            now = self.game_time()
            if self.effect_control == 'visible-wait' and now-self.control_time >= .1 and Path(self.report['images'][-1]['path']).is_file():
                foot = self.pawn.get_property('FootStep')
                require(valid(foot), 'native footprint Actor vanished before view attribution')
                self.controller.set_property('HiddenActors', list(dict.fromkeys(self.observer_hidden_actors+[foot])))
                self.effect_control='hidden-settle';self.control_time=now
            elif self.effect_control == 'hidden-settle' and now-self.control_time >= .1:
                self.screenshot('effect-hidden', self.projected_hits());self.effect_control='hidden-wait';self.control_time=now
            elif self.effect_control == 'hidden-wait' and now-self.control_time >= .1 and Path(self.report['images'][-1]['path']).is_file():
                self.controller.set_property('HiddenActors', self.observer_hidden_actors)
                self.report['effect_render_visibility_restored']=True
                self.effect_control='restore-settle';self.control_time=now
            elif self.effect_control == 'restore-settle' and now-self.control_time >= .1:
                self.screenshot('effect-restored', self.projected_hits());self.effect_control='restored-wait';self.control_time=now
            elif self.effect_control == 'restored-wait' and now-self.control_time >= .1 and Path(self.report['images'][-1]['path']).is_file():
                self.effect_control='complete'
            return
        if self.phase == 'await-server' and self.index == 0:
            ack = read_json(self.root/'locomotion-server-ready.json')
            if ack and ack.get('run_id') == self.run and ack.get('index') == 0:
                if self.camera_ready is None:
                    self.configure_camera();return
                if not self.before_requested:
                    if self.game_time()-self.camera_ready < .4:
                        return
                    self.screenshot('before');self.before_requested=True;self.camera_ready=self.game_time();return
                if self.game_time()-self.camera_ready < .15:
                    return
        super().observe_client()
        if self.current is not None and self.index == 0 and self.phase in ('moving', 'stopping') and not self.after_requested:
            count = len(self.current['foot'])
            if count != self.step_count_seen:
                self.step_count_seen=count;self.step_seen_time=self.game_time()
            if count and self.step_seen_time is not None and self.game_time()-self.step_seen_time >= .15:
                projected = self.projected_hits()
                if projected:
                    self.screenshot('after', projected);self.after_requested=True
                    self.effect_control='visible-wait';self.control_time=self.game_time()
        if self.index > 0 and valid(self.camera) and self.controller.call_function('GetViewTarget') == self.camera:
            self.controller.call_function('SetViewTargetWithBlend', self.original_view, 0., 0, 0., False)
            self.controller.set_property('HiddenActors', self.original_hidden_actors)

    def cleanup(self):
        if self.cleaned:
            return
        if self.role == 'client' and hasattr(self, 'original_view'):
            self.controller.call_function('SetViewTargetWithBlend', self.original_view, 0., 0, 0., False)
            self.controller.set_property('HiddenActors', self.original_hidden_actors)
            if valid(self.camera):
                self.camera.actor_destroy()
        super().cleanup()
        self.report['original_view_target_restored'] = self.role == 'server' or self.controller.call_function('GetViewTarget') == self.original_view and list(self.controller.get_property('HiddenActors')) == self.original_hidden_actors
        if self.role == 'server':
            self.report['effect_render_visibility_restored']=True

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try:
                for row in self.report['images']:
                    row['sha256'] = hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
                self.report['status'] = 'passed';validate(self.report)
            except Exception:
                self.report.update(status='failed', error=traceback.format_exc())
        self.write()
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_FOOTSTEP_VISUAL_SHUTDOWN_'+self.report['status'].upper())

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.cleanup()
        except Exception:
            error = (error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_FOOTSTEP_VISUAL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPFootstepVisualResult=')), None)
if result:
    validation = Validation(result);atexit.register(validation.finalize);ticker = ue.add_ticker(validation.tick)
