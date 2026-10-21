"""Original native HealthSet/OnOutOfHealth produces every observed score/message."""
import atexit, copy, sys, time, traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_hud.notification_relays_network_validation import Network as Relays, identity, payload_model
from uep_lyra_hud import elimination_feed_relay_mixin as kill
from .hero_burst_cue_mixin import lib
from . import tdm_scoring_mixin as scoring, scoring_base_mixin as shared, game_phases_mixin as phases
from .tdm_lethal_network_contract import PEERS, FALSE_FIELDS, require, validate

DAMAGE = '/Game/GameplayEffects/Damage/GE_Damage_Basic_SetByCaller.GE_Damage_Basic_SetByCaller_C'


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


class Network(Relays):
    def __init__(self, result, peer, run):
        super().__init__(result, peer, run)
        self.profile = arg('UEPTDMNetworkProfile')
        self.report = dict(status='running', error=None, peer=peer, run_id=run, requested_profile=self.profile,
            profiles_selected_before_component_creation=True, actual_native_damage_spec_applied=False, server_waited_for_client_process_exit=False)
        self.report.update(dict.fromkeys(FALSE_FIELDS, False))
        self.boot_selectors = []
        for path in (shared.CLASS, scoring.CLASS, *phases.CLASSES.values()):
            cls = ue.load_class(path)
            if 'PythonMixinProfile' in cls.get_cdo().properties():
                self.boot_selectors.append((cls, cls.get_cdo().get_property('PythonMixinProfile')))
                cls.get_cdo().set_property('PythonMixinProfile', self.profile)

    def setup(self):
        super().setup()
        self.phase_system = lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem', self.world, ue.find_class('LyraGamePhaseSubsystem'))
        if self.peer == 'server':
            self.scoring.call_function(scoring.SET_TARGET, 1)
            self.initial_tdm = copy.deepcopy(scoring.evidence(self.scoring))
        else:
            self.scoring = self.state.get_component_by_type(ue.load_class(scoring.CLASS))
            require(valid(self.scoring), 'replicated TDM component absent')
        for component in self.components.values():
            ue.set_mixin_profile(component, self.profile)
        self.stage = 'roster'

    def attribute_health(self, state):
        asc = state.get_property('AbilitySystemComponent')
        found = [value for value in asc.get_property('SpawnedAttributes') if valid(value) and value.is_a(ue.find_class('LyraHealthSet'))]
        require(len(found) == 1, 'canonical native HealthSet required')
        return float(found[0].get_property('Health').CurrentValue)

    def resolve_states(self, roster):
        states = {int(a.call_function('GetPlayerId')): a for a in self.world.all_actors() if valid(a) and a.is_a(ue.find_class('LyraPlayerState'))}
        players = {}
        for peer, row in roster.items():
            state = states.get(row['player_id'])
            if not valid(state) or identity(state) != row['state_wire']:
                return False
            pawn = state.call_function('GetPawn')
            if not valid(pawn) or identity(pawn) != row['pawn_wire'] or self.team_id(pawn) != row['team'] or self.attribute_health(state) != 100.:
                return False
            players[peer] = dict(state=state, pawn=pawn)
        self.players = players
        return True

    def arm(self):
        self.entries = dict(kill=0, award=0);self.receipts=[];self.kill_messages=[];self.award_messages=[]
        self.score_before = self.scores() if self.peer == 'server' else None
        self.baseline_stats = self.stats()
        require(self.attribute_health(self.players['A']['state']) == self.attribute_health(self.players['B0']['state']) == 100., 'canonical native health not ready before damage')
        self.armed = True

    def stats(self):
        source, target = self.players['A']['state'], self.players['B0']['state']
        return dict(kills=int(source.call_function('GetStatTagStackCount', GameplayTag(TagName='ShooterGame.Score.Eliminations'))),
            deaths=int(target.call_function('GetStatTagStackCount', GameplayTag(TagName='ShooterGame.Score.Deaths'))),
            team=int(self.team.call_function('GetTeamTagStackCount', self.roster['A']['team'], GameplayTag(TagName='ShooterGame.Score.Eliminations'))),
            other=int(self.team.call_function('GetTeamTagStackCount', self.roster['B0']['team'], GameplayTag(TagName='ShooterGame.Score.Eliminations'))))

    def apply_lethal(self):
        require(self.peer == 'server', 'only authority produces native GAS damage')
        source = ability_system(self.players['A']['pawn']);target = ability_system(self.players['B0']['pawn'])
        spec = source.call_function('MakeOutgoingSpec', ue.load_class(DAMAGE), 1., source.call_function('MakeEffectContext'))
        spec = lib('AbilitySystemBlueprintLibrary').call_function('AssignTagSetByCallerMagnitude', spec, GameplayTag(TagName='SetByCaller.Damage'), 100.)
        source.call_function('BP_ApplyGameplayEffectSpecToTarget', spec, target)
        self.report['actual_native_damage_spec_applied'] = True
        self.fired_at = time.monotonic()
        atomic_write(self.root/'native-lethal-fired.json', dict(run_id=self.run))

    def record(self):
        after = self.stats();before = self.baseline_stats
        asc = self.players['A']['state'].get_property('AbilitySystemComponent')
        cue_cls = ue.find_class('/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided_C')
        cues = [actor for actor in ue.tobject_iterator(cue_cls) if valid(actor) and actor.get_world() == self.world] if cue_cls else []
        row = dict(roster=self.roster, attacker_health=self.attribute_health(self.players['A']['state']), victim_health=self.attribute_health(self.players['B0']['state']),
            attacker_kills_delta=after['kills']-before['kills'], victim_deaths_delta=after['deaths']-before['deaths'],
            attacker_team_score_delta=after['team']-before['team'], other_team_score_delta=after['other']-before['other'],
            target_score=int(self.scoring.get_property('TargetScore')), ability_input_blocked=bool(asc.call_function('GetGameplayTagCount', GameplayTag(TagName='Gameplay.AbilityInputBlocked'))),
            postgame_damage_immunity=bool(asc.call_function('GetGameplayTagCount', GameplayTag(TagName='Gameplay.DamageImmunity'))),
            relay_entries=copy.deepcopy(self.entries), relay_receipts=copy.deepcopy(self.receipts),
            kill_notifications=copy.deepcopy(self.kill_messages), award_notifications=copy.deepcopy(self.award_messages),
            native_match_decided_cue_actors=len(cues), native_postgame_phase_active=bool(self.phase_system.call_function('IsPhaseActive', GameplayTag(TagName='ShooterGame.GamePhase.PostGame'))),
            native_playing_phase_inactive=not bool(self.phase_system.call_function('IsPhaseActive', GameplayTag(TagName='ShooterGame.GamePhase.Playing'))))
        if self.peer == 'server':
            values = scoring.evidence(self.scoring);prefix = 'python_' if self.profile == 'Python' else 'fallback_'
            row['selected_tdm_elimination_calls'] = values[prefix+'Elimination']-self.initial_tdm[prefix+'Elimination']
            row['selected_tdm_victory_calls'] = values[prefix+'Victory']-self.initial_tdm[prefix+'Victory']
        return row

    def server_tick(self):
        if self.stage == 'roster':
            ready = {peer:self.token(peer+'-ready.json') for peer in ('A','B0')}
            if not all(ready.values()):
                return
            controllers, = self.statics.call_function('GetAllActorsOfClass', self.world, ue.find_class('LyraPlayerController'))
            roster = {};players = {}
            for peer, receipt in ready.items():
                controller = next((c for c in controllers if valid(c.PlayerState) and int(c.PlayerState.call_function('GetPlayerId')) == receipt['player_id']), None)
                if not valid(controller) or not valid(controller.get_controlled_pawn()):
                    return
                state, pawn = controller.PlayerState, controller.get_controlled_pawn()
                roster[peer] = dict(player_id=receipt['player_id'], state_wire=identity(state), pawn_wire=identity(pawn), name=state.call_function('GetPlayerName'), team=self.team_id(pawn))
                players[peer] = dict(controller=controller, state=state, pawn=pawn)
            require(roster['A']['team'] != roster['B0']['team'], 'real owners must be on opposing native teams')
            self.roster, self.players = roster, players
            self.arm();atomic_write(self.root/'native-lethal-roster.json', dict(run_id=self.run, roster=roster));self.stage='armed';return
        if self.stage == 'armed':
            if not all(self.token(peer+'-lethal-armed.json') for peer in ('A','B0')):
                return
            self.apply_lethal();self.stage='observe';return
        if self.stage == 'observe':
            row = self.record()
            if row['victim_health'] != 0. or not row['native_postgame_phase_active'] or row['attacker_team_score_delta'] != 1:
                require(time.monotonic()-self.fired_at < 6., 'native lethal score/postgame did not occur')
                return
            self.report['result']=row
            if not all(self.token(peer+'-lethal-observed.json') for peer in ('A','B0')):
                return
            self.cleanup();self.report['status']='awaiting_release';atomic_write(self.root/'ready-server.json', dict(run_id=self.run));self.stage='release'
        elif self.stage == 'release':
            released = self.token('server-release.json')
            if released:
                require(released['client_exit_codes'] == {'A': 0, 'B0': 0}, 'both actual client exits required')
                self.report['server_waited_for_client_process_exit']=True
                self.finish()

    def client_tick(self):
        if self.stage == 'roster':
            source = self.token('native-lethal-roster.json')
            if source is None or not self.resolve_states(source['roster']):
                return
            self.roster = source['roster'];self.arm()
            atomic_write(self.root/(self.peer+'-lethal-armed.json'), dict(run_id=self.run));self.stage='observe';return
        if self.stage == 'observe':
            fired = self.token('native-lethal-fired.json')
            if fired is None:
                return
            if not hasattr(self,'fired_at'):
                self.fired_at = time.monotonic()
            row = self.record()
            ready = row['victim_health'] == 0. and row['attacker_team_score_delta'] == 1 and len(row['kill_notifications']) == 1 and row['native_match_decided_cue_actors'] >= 1 and row['postgame_damage_immunity']
            if not ready:
                self.report['pending_result'] = row
                require(time.monotonic()-self.fired_at < 6., 'actual native replication/notification/postgame cue missing')
                return
            self.report['result']=row;atomic_write(self.root/(self.peer+'-lethal-observed.json'), dict(run_id=self.run))
            self.cleanup();self.report['status']='awaiting_release';atomic_write(self.root/('ready-'+self.peer+'.json'), dict(run_id=self.run));self.stage='release'
        elif self.stage == 'release' and self.token('release.json'):
            self.finish()

    def cleanup(self):
        if getattr(self,'cleanup_done',False):
            return
        super().cleanup()
        for cls, previous in reversed(self.boot_selectors):
            cls.get_cdo().set_property('PythonMixinProfile', previous)
        self.report['boot_selectors_restored'] = all(cls.get_cdo().get_property('PythonMixinProfile') == previous for cls, previous in self.boot_selectors)

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 480., 'native lethal network timeout')
            if not self.ready:
                if self.world_ready():
                    self.setup()
            elif self.peer == 'server':
                self.server_tick()
            else:
                self.client_tick()
            self.report['stage']=self.stage;atomic_write(self.path,self.report);return not self.finished
        except Exception:
            self.finish(traceback.format_exc());return False

    def finish(self, error=None):
        if self.finished:
            return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error)
        atomic_write(self.path,self.report);(ue.log_error if error else ue.log)('UEP_TDM_LETHAL_NETWORK_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_TDM_LETHAL_NETWORK_SHUTDOWN_'+self.report['status'].upper())


if any(value.startswith('-UEPTDMNetworkResult=') for value in sys.argv):
    validation=Network(arg('UEPTDMNetworkResult'),arg('UEPTDMNetworkPeer'),arg('UEPTDMNetworkRun'));atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
