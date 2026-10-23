"""Actual native HostSession invalid-request UI and delegate cleanup, no replay."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from .host_session_validation import Validation as HostBase, count
from .experience_screen_validation import path
from . import host_session_mixin as policy
from .host_session_failure_contract import require, validate
from uep_lyra_world.effect_pad_mixin import valid


class Validation(HostBase):
    def __init__(self, result):
        super().__init__(result)
        self.mode = 'life'; self.originals = []; self.dialogs = []; self.native_results = []; self.pairs = []
        self.report = dict(status='running', error=None, profiles=[])
        for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested',
                    'physical_button_input_tested', 'online_provider_failure_tested', 'callbacks_replayed', 'health_properties_written'):
            self.report[key] = False

    def begin(self):
        cls = ue.load_class(policy.CLASS)
        require(not [w for w in ue.tobject_iterator(cls) if w != cls.get_cdo()], 'Failure fixture requires no pre-existing host widget')
        ue.unregister_mixin(cls)
        for profile in ('BlueprintFallback', 'Python'):
            owner = getattr(policy, 'LyraHostSession' + profile + 'Profile')
            original = owner.prepared
            def prepared(widget, *args, _original=original):
                if widget == self.w:
                    self.invalidations += 1
                    require(valid(widget.get_property('SelectedExperience')), 'Actual selected experience missing at preparation completion')
                    require(valid(widget.get_property('SpinnerWidget')), 'Native spinner must precede invalidation')
                    widget.set_property('SelectedExperience', None)
                return _original(widget, *args)
            prepared.__dict__.update(original.__dict__)
            self.originals.append((owner, original)); owner.prepared = prepared
        super().begin()
        self.report['native_mode'] = str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld', self.world).call_function('CaptureSnapshot').NetMode)
        self.sub = policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem', self.world, ue.find_class('CommonSessionSubsystem'))
        def completed(result):
            self.native_results.append(dict(success=bool(result.bWasSuccessful), error=str(result.ErrorText), error_id=str(result.ErrorId)))
        self.bind(self.sub, 'K2_OnCreateSessionCompleteEvent', completed)

    def start_profile(self):
        self.invalidations = 0; self.native_before = len(self.native_results)
        super().start_profile()

    def history(self, widget, label):
        target = self.path.parent / (self.profile + '-' + label + '.t3d')
        require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(widget, str(target)), 'Native error text export failed')
        raw = target.read_bytes(); text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
        return [line.strip() for line in text.splitlines() if line.strip().startswith('Text=')]

    def active_dialogs(self):
        return [w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated') and w.call_function('GetOwningPlayer') == self.controller]

    def observe(self):
        require(time.monotonic() - self.phase_started < 35., 'Host failure phase timeout: ' + self.phase)
        if self.phase == 'settle':
            self.frames += 1
            if not self.loaded or self.frames < 4: return
            self.origin = path(self.world); self.result_before = len(self.native_results)
            self.list.get_property('ExperienceWidgets')[0].get_property('ExperienceTileButton').call_function('HandleButtonClicked')
            self.enter('failure')
        elif self.phase == 'failure':
            if count(self.w, 'completed') != 1 or not self.active_dialogs(): return
            dialogs = self.active_dialogs(); require(len(dialogs) == 1, 'Native failure dialog missing or duplicated')
            self.dialog = dialogs[0]; self.dialogs.append(self.dialog)
            title = self.history(self.dialog.get_property('Text_Title'), 'error-title')
            body = self.history(self.dialog.get_property('RichText_Description'), 'error-body')
            require(any('NetworkErrors' in line and 'InvalidRequest' in line for line in body), 'Native invalid-request FText history was not preserved')
            require(len(self.native_results) == self.result_before + 1 and not self.native_results[-1]['success'] and self.native_results[-1]['error'] == 'HostSession passed an invalid request.', 'Native HostSession failure notification differs')
            spinner = self.w.get_property('SpinnerWidget'); require(not spinner.call_function('IsActivated'), 'Failure left the native spinner active')
            self.row.update(native_tile_click_and_spinner=count(self.w, 'selected') == count(self.w, 'spinner_pushed') == 1,
                selected_experience_invalidated_only_at_prepared_entry=self.invalidations == 1,
                native_failed_completion_and_error_dialog=True, native_error_ftext_history_preserved=True, native_spinner_popped=True)
            self.state = dict(title=title, body=body, result=copy.deepcopy(self.native_results[-1]))
            buttons = list(self.dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries'))
            require(len(buttons) == 1, 'Actual error dialog needs one acknowledgement button')
            buttons[0].call_function('HandleButtonClicked'); self.frames = 0; self.enter('acknowledged')
        elif self.phase == 'acknowledged':
            self.frames += 1
            if self.frames < 4: return
            require(not self.dialog.call_function('IsActivated') and not self.active_dialogs(), 'Native acknowledgement did not close the error dialog')
            self.row['native_acknowledge_button_closed_dialog'] = True
            self.counters_before = copy.deepcopy(policy.evidence(self.w))
            # Public native API, not a replay of the UI or subsystem delegate.
            self.sub.call_function('HostSession', self.controller, None)
            require(len(self.native_results) == self.result_before + 2, 'Native unbound-control failure missing')
            self.enter('quiet')
        elif self.phase == 'quiet':
            if time.monotonic() - self.phase_started < .3: return
            require(policy.evidence(self.w) == self.counters_before and not self.active_dialogs() and path(self.world) == self.origin, 'Unbound native control reentered UI, or travelled')
            counters = policy.evidence(self.w); selected = 'fallback' if self.profile == 'BlueprintFallback' else 'python'; foreign = 'python' if selected == 'fallback' else 'fallback'
            self.row.update(native_second_failure_did_not_reenter_unbound_widget=True, no_late_callbacks_or_world_change=True,
                prepared_calls=count(self.w, 'prepared'), completed_calls=count(self.w, 'completed'), invalidations=self.invalidations,
                native_failure_notifications=len(self.native_results) - self.result_before,
                exclusive_selected_profile_calls=all(counters[selected + '_' + key] == 1 and counters[foreign + '_' + key] == 0 for key in ('prepared', 'completed', 'request')))
            self.report['profiles'].append(self.row); self.pairs.append(self.state); self.close(self.w); self.index += 1
            if self.index < 2: self.start_profile()
            else:
                self.report.update(source_python_failure_states_match=self.pairs[0] == self.pairs[1], native_failure_notifications=len(self.native_results), matrices=self.pairs)
                self.finish()

    def cleanup(self):
        for dialog in self.dialogs:
            if valid(dialog): self.close(dialog)
        super().cleanup()
        cls = self.classes.get('host')
        if cls is not None: ue.unregister_mixin(cls)
        for owner, original in self.originals: owner.prepared = original
        if cls is not None: ue.register_declared_mixin(cls)
        self.report['profile_methods_restored'] = all(owner.prepared is original for owner, original in self.originals)

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or '') + traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error); self.write()
        (ue.log_error if error else ue.log)('UEP_HOST_FAILURE_DIFFERENTIAL_' + ('FAILED ' + error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try: self.report['status'] = 'passed'; validate(self.report)
            except Exception: self.report.update(status='failed', error=traceback.format_exc())
        self.write(); (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_HOST_FAILURE_SHUTDOWN_' + self.report['status'].upper())


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHostSessionFailureResult=')), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
