"""Negative acceptance models reject counters-only, missing native sense and leaks."""
import copy
import unittest
from uep_lyra_characters.health_changed_contract import CLASS, PLAN, COUNTERS, validate


def case(name, profile, authority=True, keys=("A", "AI"), local=None):
    target = "AI" if name.startswith("ai-") else ("B0" if name.startswith("player-B0") else "A")
    event = authority and name in ("ai-foreign", "ai-foreign-healing")
    amount = -3. if name.endswith("healing") else 5.; old = 95. if name.endswith("healing") else 100.
    stimulus = dict(source="source-pawn", strength=amount, location=[17., -23., 61.], hit_location=[0., 0., 0.], tag="None", sense="/Script/AIModule.AISense_Damage")
    actors = {}
    for key in keys:
        selected = profile if key == target else ("Python" if profile == "BlueprintFallback" else "BlueprintFallback")
        stats = dict.fromkeys(COUNTERS, 0); active = key == target
        if active:
            stats["python_calls" if selected == "Python" else "fallback_calls"] = 1
            if selected == "Python": stats["authority_noops" if not authority else ("instigator_noops" if name == "ai-non-playerstate" else ("self_noops" if name.endswith("self") else ("damage_reports" if target == "AI" else "controller_noops")))] = 1
        actors[key] = dict(profile=selected, native_role=3 if authority else (2 if key == local else 1), authority=authority,
            health=old-amount if active else 100., original_health=100., counters=stats,
            delegates=[dict(component_matches=True, owner_matches=True, old=old, new=old-amount, instigator="source-state" if authority else None)] if active else [],
            last_report=dict(amount=amount, controller="ai-controller", instigator="source-pawn", location=stimulus["location"], hit_location=[0., 0., 0.]) if event and profile == "Python" else None)
    return dict(name=name, profile=profile, target=target, native_gas_producer_called=authority, actors=actors,
        native_stimuli=[copy.deepcopy(stimulus)] if event else [], native_ai_perception_memory=event,
        native_ai_perception_memory_stimulus=copy.deepcopy(stimulus) if event else None,
        native_source_instigator="source-state" if authority else None, source_instigator_is_playerstate=authority and name != "ai-non-playerstate",
        source_pawn="source-pawn" if authority else None, source_location=stimulus["location"] if authority else None)


def report():
    return dict(status="passed", error=None, retained_character_class=CLASS, native_net_mode="Standalone",
        cases=[case(*value) for value in PLAN], cleanup=dict(health_restored=True, original_profiles_restored=True, original_inventory_restored=True,
            cdo_profile_restored=True, observer=dict(created=1, closed=1, bindings_created=3, bindings_closed=3, active=0, health_deliveries=22, sense_deliveries=4, errors=[])),
        owned_fixture_cleanup=dict(owned_pawn_controller_playerstate_producer_destroyed=True, original_bot_producer_list_preserved=True),
        **dict.fromkeys(("callback_replayed", "health_properties_written", "sense_report_called_by_fixture", "component_delegate_broadcast_by_fixture", "gameplay_state_delivered_by_files",
            "pixels_verified", "physical_input_tested", "packaged_runtime", "whole_character_migrated", "full_acceptance"), False))


class CharacterHealthChangedReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.report)

    def test_complete_real_evidence_shape_passes_model_only(self): self.assertEqual(validate(self.report)["native_gas_health_trials"], 10)
    def test_process_exit_alone_cannot_replace_actual_matrix(self): self.report["cases"] = []; self.reject()
    def test_native_authority_must_be_observed(self): self.report["cases"][0]["actors"]["A"]["authority"] = False; self.reject()
    def test_counters_without_health_delegate_rejected(self): self.report["cases"][0]["actors"]["A"]["delegates"] = []; self.reject()
    def test_wrong_component_payload_rejected(self): self.report["cases"][0]["actors"]["A"]["delegates"][0]["component_matches"] = False; self.reject()
    def test_source_instigator_must_be_actual_gas_context(self): self.report["cases"][0]["native_source_instigator"] = "invented"; self.reject()
    def test_foreign_case_must_really_have_playerstate_instigator(self): self.report["cases"][-1]["source_instigator_is_playerstate"] = False; self.reject()
    def test_passive_actor_health_cannot_change(self): self.report["cases"][0]["actors"]["AI"]["health"] = 95.; self.reject()
    def test_native_ai_callback_not_only_python_count(self): self.report["cases"][6]["native_stimuli"] = []; self.reject()
    def test_memory_must_independently_match_multicast(self): self.report["cases"][6]["native_ai_perception_memory_stimulus"]["strength"] = 0.; self.reject()
    def test_healing_must_keep_raw_negative_stimulus(self): self.report["cases"][8]["native_stimuli"][0]["strength"] = 3.; self.reject()
    def test_original_hit_location_is_zero_not_target_location(self): self.report["cases"][6]["native_stimuli"][0]["hit_location"] = [1., 2., 3.]; self.reject()
    def test_self_branch_cannot_report_damage_sense(self): self.report["cases"][0]["native_ai_perception_memory"] = True; self.reject()
    def test_no_open_subscription_scope(self): self.report["cleanup"]["observer"]["active"] = 1; self.reject()
    def test_native_observer_errors_cannot_be_hidden(self): self.report["cleanup"]["observer"]["errors"] = ["conversion failed"]; self.reject()
    def test_original_player_health_and_inventory_restore_required(self): self.report["cleanup"]["health_restored"] = False; self.reject()
    def test_owned_native_ai_must_be_destroyed(self): self.report["owned_fixture_cleanup"]["owned_pawn_controller_playerstate_producer_destroyed"] = False; self.reject()
    def test_no_callback_replay_or_health_property_write(self): self.report["callback_replayed"] = True; self.reject()
    def test_normal_play_never_selects_validation(self):
        from uep_lyra_hud.startup import validation_module
        self.assertIsNone(validation_module([])); self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterHealthResult=x"]))
        self.assertEqual(validation_module(["-UEPCharacterHealthResult=x"]), "uep_lyra_characters.health_changed_validation")

    def test_cleanup_cached_pod_does_not_touch_destroyed_native_objects(self):
        import ast
        from pathlib import Path
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_observation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(value for value in tree.body if isinstance(value, ast.ClassDef) and value.name == "Context")
        method = next(value for value in cls.body if isinstance(value, ast.FunctionDef) and value.name == "cleanup")
        namespace = {}; exec(compile(ast.Module(body=[method], type_ignores=[]), str(file), "exec"), namespace)
        import types
        expected = dict(cached=True)
        self.assertIs(namespace["cleanup"](types.SimpleNamespace(closed=True, cleanup_report=expected)), expected)

    def test_owned_ai_uses_reflected_game_mode_name_api_not_cpp_only_setter(self):
        import ast
        from pathlib import Path
        import types
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_observation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(value for value in tree.body if isinstance(value, ast.ClassDef) and value.name == "OwnedAI")
        calls = []
        state = types.SimpleNamespace(call_function=lambda *args: (_ for _ in ()).throw(AssertionError("PlayerState.SetPlayerName is C++ only")))
        pawn = object(); perception = object()
        controller = types.SimpleNamespace(get_property=lambda name: {"PlayerState": state, "BrainComponent": None, "PerceptionComponent": perception}[name],
            get_controlled_pawn=lambda: pawn, call_function=lambda *args: calls.append(args))
        template = types.SimpleNamespace(get_property=lambda name: [], get_class=lambda: "original-bot-producer-class")
        bot_list = []
        creator = types.SimpleNamespace(component_is_registered=lambda: False, get_property=lambda name: bot_list,
            call_function=lambda name: bot_list.append(controller) if name == "SpawnOneBot" else (_ for _ in ()).throw(AssertionError(name)))
        game_state = types.SimpleNamespace(get_component_by_type=lambda cls: template)
        mode = types.SimpleNamespace(call_function=lambda *args: calls.append(args))
        engine = types.SimpleNamespace(find_class=lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda name, world: game_state if name == "GetGameState" else mode)) if name == "GameplayStatics" else name,
            new_object=lambda cls, outer, name: creator)
        world = object()
        namespace = dict(ue=engine, path=lambda value: value, valid=lambda value: value is not None, require=lambda value, message: self.assertTrue(value, message))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        result = namespace["OwnedAI"](world)
        self.assertEqual(calls, [("ChangeName", controller, "UEPHealthSenseFixture", False), ("StopMovement",)])
        self.assertIs(result.pawn, pawn)

    def test_authority_restore_uses_official_healing_ge_and_positive_heal_magnitude(self):
        import ast
        from pathlib import Path
        import types
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_observation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); function = next(value for value in tree.body if isinstance(value, ast.FunctionDef) and value.name == "apply")
        calls = []; source = types.SimpleNamespace(call_function=lambda *args: calls.append(args) or ("context" if args[0] == "MakeEffectContext" else "spec"))
        library = types.SimpleNamespace(call_function=lambda *args: calls.append(args) or "spec")
        engine = types.SimpleNamespace(find_class=lambda name: types.SimpleNamespace(get_cdo=lambda: library), load_class=lambda name: name)
        namespace = dict(ue=engine, DAMAGE="native-damage-ge", GameplayTag=lambda **args: args, ability_system=lambda actor: "target-asc", path=lambda obj: obj)
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(file), "exec"), namespace)
        namespace["apply"](source, object(), -3.)
        self.assertIn(("MakeOutgoingSpec", "/Game/GameplayEffects/Heal/GE_Heal_SetByCaller.GE_Heal_SetByCaller_C", 1., "context"), calls)
        self.assertIn(("AssignTagSetByCallerMagnitude", "spec", dict(TagName="SetByCaller.Heal"), 3.), calls)

    def test_owned_controller_destruction_does_not_use_native_noop_blueprint_entry(self):
        import ast
        from pathlib import Path
        import types
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_observation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(value for value in tree.body if isinstance(value, ast.ClassDef) and value.name == "OwnedAI")
        method = next(value for value in cls.body if isinstance(value, ast.FunctionDef) and value.name == "close")
        class Actor:
            alive = True
            def actor_destroy(self): self.alive = False
            def call_function(self, *args): raise AssertionError("Controller.K2_DestroyActor is a native noop")
        actors = [Actor() for _ in range(3)]
        producer = Actor(); producer.call_function = lambda name, obj: producer.actor_destroy()
        template = types.SimpleNamespace(get_property=lambda name: [])
        owner = types.SimpleNamespace(**dict(zip(("pawn", "controller", "state"), actors)), creator=producer, template=template, original_bots=[])
        namespace = dict(valid=lambda value: value is not None and value.alive, path=lambda value: value)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(file), "exec"), namespace)
        self.assertTrue(namespace["close"](owner)["owned_pawn_controller_playerstate_producer_destroyed"])
