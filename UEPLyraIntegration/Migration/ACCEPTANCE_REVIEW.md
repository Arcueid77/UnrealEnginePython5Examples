# Migration acceptance review

The original 246 candidate paths, order and version assignments are preserved.
Zero `not_accepted` rows records bounded dispositions; full migration acceptance remains unproven.
This index does not execute or semantically revalidate the referenced runtime evidence.

| Version | Original candidates | Checklist requirements |
| --- | ---: | ---: |
| 0.9.0 | 5 | 7 |
| 0.10.0 | 32 | 3 |
| 0.11.0 | 37 | 3 |
| 0.12.0 | 75 | 3 |
| 0.13.0 | 57 | 3 |
| 0.14.0 | 40 | 3 |

## Original checklist requirements

- `0.9.0` — A checked-in call/lifecycle matrix labels every path as tested supported, intentionally rejected, or bypass/unsupported, with reproducible fixtures. (ROADMAP.md:242; all_33_documented_contract_paths_classified_with_pinned_reproducers_and_current_generic_calls_pie).
- `0.9.0` — The controlled reload and cleanup tests pass across repeated PIE, GC and travel; state, callbacks and router restoration are checked after teardown. (ROADMAP.md:244; current_sdk_controlled_reload_profile_gc_repeated_pie_and_two_travel_cleanup_source_verified).
- `0.9.0` — A visible and packaged weapon/ammo example proves native signal plus read-only sampled change updates, safe subscription removal and native authority ownership. (ROADMAP.md:246; current_native_python_packaged_and_visible_weapon_with_native_signal_sampler_cleanup_owner_protocol_verified).
- `0.9.0` — Batch 1A has original-BP/Python state and visual comparisons for weapon switching, firing, reload, empty ammo and Pawn replacement. One server and two clients prove that ammo/UI state never crosses local-player ownership. (ROADMAP.md:249; five_directly_reviewed_bp_python_weapon_component_views_and_current_native_two_owner_protocol_verified).
- `0.9.0` — Normal playable startup does not auto-run validation or request exit; explicitly enabled test modes retain bounded timeouts and cleanup evidence. Focused rendered weapon mode exits cleanly; the no-test-flag Lyra observation is bounded and stopped only by its owning test driver, not by a probe. (ROADMAP.md:252; native_normal_no_probe_observation_and_focused_rendered_probe_cleanup_and_sources_verified).
- `0.9.0` — Generic, both Third Person variants and Lyra pass the candidate regression matrix; the missing Mixin Third Person visible gate is closed. (ROADMAP.md:256; original_generic_third_person_and_lyra_candidate_cells_source_bound_and_aggregated).
- `0.9.0` — The supported API inventory and migration/deprecation rules are ready for RC freeze, with no known release-blocking correctness defects. (ROADMAP.md:258; supported_api_inventory_compatibility_and_explicit_correctness_dispositions_reviewed_for_rc).
- `0.10.0` — Each small batch passes original-BP/Python comparison without BP fallthrough. (ROADMAP.md:605; all_original_32_candidates_140_entries_source_bound_native_comparisons_without_bp_business_fallthrough).
- `0.10.0` — Pickup failure/success, cooldown/respawn and interaction effects match the baseline; two players cannot share another player's UI or claim state. (ROADMAP.md:606; native_pickup_rejection_cooldown_interaction_effects_and_two_owner_ui_claim_sources_verified).
- `0.10.0` — Widget and Actor lifetime tests leave no owned subscriptions after teardown, travel or profile switching. (ROADMAP.md:608; native_widget_actor_scope_teardown_travel_profile_cleanup_source_verified).
- `0.11.0` — Fire, reload, ammo exhaustion, switching, death and respawn pass BP/Python comparison in Standalone and one-server/two-client play. (ROADMAP.md:1705; native_six_behavior_standalone_two_client_source_pins_and_original_python_outcomes_verified).
- `0.11.0` — Supported ability tasks, delegates, cancellation and latent boundaries have call/lifetime regressions; unsupported signatures fail explicitly. (ROADMAP.md:1707; native_task_delegate_cancel_latent_and_timer_lifetimes_with_current_source_guards_verified).
- `0.11.0` — No replacement changes UObject class identity or bypasses the required authority, prediction or replication checks. (ROADMAP.md:1709; native_original_class_identity_authority_prediction_replication_boundaries_and_current_sources_verified).
- `0.12.0` — Effect/audio triggering, warmup/play/postgame, scoring and notifications match the original BP checkpoints under the same inputs. (ROADMAP.md:1722; native_effect_audio_phase_scoring_notification_checkpoints_and_current_sources_verified).
- `0.12.0` — AI task/service outcomes and cancellation are reproducible; long-running tasks do not retain a destroyed Pawn or World. (ROADMAP.md:1724; native_ai_eqs_outcomes_and_pawn_world_cancellation_with_collection_verified).
- `0.12.0` — Multi-client score/phase state, local notifications and cleanup agree. (ROADMAP.md:1726; native_multi_client_score_phase_local_notification_cleanup_and_current_sources_verified).
- `0.13.0` — Navigation, focus/back behavior, settings persistence, session results and replay controls pass original-BP/Python comparisons. (ROADMAP.md:1737; native_navigation_settings_sessions_replay_comparisons_and_current_sources_verified).
- `0.13.0` — Repeated screen open/close and travel restore subscriptions and state. (ROADMAP.md:1739; paired_native_reopen_travel_state_and_callback_restoration_verified).
- `0.13.0` — Failures/cancellations are tested, not accepted only on the success path. (ROADMAP.md:1740; native_ui_failure_and_cancellation_evidence_and_current_source_verified).
- `0.14.0` — Both Experiences pass original-BP/Python gameplay, presentation and applicable multi-client/local-player comparisons. (ROADMAP.md:1751; unproven).
- `0.14.0` — Every audited candidate is migrated, explicitly retained, unreachable with checked references, or a named blocker; no silent coverage gaps remain. (ROADMAP.md:1753; current_candidate_source_binding_retention_and_named_issue_dispositions_verified).
- `0.14.0` — Configuration-only BP shells and animation/editor/test exclusions have documented reasons. Game-project C++ migration stays a separate phase. (ROADMAP.md:1755; per_asset_reasons_and_current_reference_stage_copies_verified).

## Explicit unverified capabilities

These are recorded flags requiring requirement and platform review, not automatic new scope.

- `grenade_activation_pilot`: physical_input_tested.
- `grenade_actor_vfx_pilot`: network_acceptance.
- `grenade_actor_cleanup_pilot`: network_acceptance.
- `grenade_actor_actions_pilot`: network_acceptance.
- `grenade_actor_begin_pilot`: network_acceptance.
- `grenade_actor_headless_pilot`: network_acceptance.
- `grenade_actor_hit_pilot`: audio_playback_tested, network_acceptance.
- `grenade_actor_detonate_pilot`: audio_playback_tested, network_acceptance.
- `grenade_actor_detonate_network_pilot`: audio_playback_tested.
- `grenade_natural_flight_network_pilot`: audio_playback_tested, physical_input_tested.
- `weapon_actor_helpers_pilot`: audio_playback_tested, network_acceptance.
- `weapon_actor_fire_pilot`: network_acceptance, audio_playback_tested, pixels_tested.
- `weapon_actor_begin_pilot`: network_acceptance.
- `weapon_fire_fx_pilot`: pixels_tested, audio_playback_tested, network_acceptance.
- `weapon_decals_pilot`: pixels_tested, audio_playback_tested, network_acceptance.
- `weapon_impacts_pilot`: pixels_tested, audio_playback_tested, network_acceptance.
- `weapon_ability_fire_pilot`: physical_input_tested, pixels_tested, audio_playback_tested, network_acceptance.
- `weapon_fire_network_pilot`: physical_input_tested, audio_playback_tested, pixels_tested.
- `weapon_audio_math_pilot`: audible_playback_accepted, network_acceptance.
- `weapon_audio_dispatch_pilot`: audible_playback_accepted, network_acceptance.
- `weapon_audio_whiz_pilot`: audible_playback_accepted, network_acceptance.
- `weapon_audio_early_pilot`: audible_playback_accepted, network_acceptance.
- `weapon_audio_cold_routing_pilot`: audible_playback_accepted, network_acceptance.
- `weapon_audio_network_routing_pilot`: audible_playback_accepted.
- `music_manager_controls_pilot`: network_acceptance.
- `music_manager_lifecycle_pilot`: network_acceptance.
- `general_audio_pilot`: audible_playback_accepted, network_acceptance.
- `frontend_logout_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `startup_login_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `frontend_menu_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `menu_travel_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `menu_layers_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `credits_widgets_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `diagnostic_widgets_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `settings_screens_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `settings_editors_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `foundation_widgets_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `bound_action_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `editor_experiences_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `lobby_background_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `replay_runtime_pilot`: pixels_tested, audio_playback_tested, network_acceptance, packaged_runtime.
- `replay_browser_pilot`: pixels_tested, audio_playback_tested, network_acceptance, packaged_runtime.
- `ui_preparation_closure_pilot`: pixels_tested, physical_input_tested, packaged_runtime.
- `session_entry_pilot`: audio_playback_tested, pixels_tested, packaged_runtime.
- `session_browser_pilot`: audio_playback_tested, pixels_tested, network_acceptance, packaged_runtime.
- `session_button_pilot`: audio_playback_tested, pixels_tested, network_acceptance, packaged_runtime.
- `host_session_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `experience_selection_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `experience_catalog_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `experience_tile_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `menu_buttons_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `foundation_buttons_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `macro_consumer_closure_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `shooter_eqs_pilot`: network_acceptance, explicit_native_dead_actor_variant_tested, context_array_order_native_direct_tested, pixels_tested, packaged_runtime.
- `shooter_ai_controller_services_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `game_phases_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `elimination_score_widget_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `control_point_widgets_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `scoreboard_style_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `scoreboard_list_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `scoreboard_rows_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `weapon_hud_existing_acceptance_closure`: network_acceptance.
- `elimination_widgets_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `accolade_widgets_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `notification_relays_network_pilot`: pixels_tested, packaged_runtime.
- `accolade_relay_pilot`: pixels_tested, packaged_runtime.
- `elimination_feed_relay_pilot`: pixels_tested, packaged_runtime.
- `control_point_volume_feedback_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `control_point_volume_state_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `control_point_volume_helpers_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `cp_scoring_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `tdm_scoring_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `scoring_base_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `physics_field_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `small_burst_cue_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `spawning_cue_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `traversal_cue_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `hero_burst_cue_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `character_damage_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `message_widget_pilot`: pixels_tested, audio_playback_tested, network_acceptance, packaged_runtime.
- `cue_widget_pilot`: pixels_tested, audio_playback_tested, network_acceptance, packaged_runtime.
- `footstep_pilot`: audio_playback_tested, network_acceptance, packaged_runtime.
- `wind_system_pilot`: audible_playback_accepted, network_acceptance.
- `music_manager_family_pilot`: network_acceptance.
- `weapon_fire_cue_network_pilot`: audible_playback_accepted.
- `weapon_fire_cue_pilot`: audible_playback_accepted, network_acceptance.
- `netshooter_ability_pilot`: network_acceptance.
- `netshooter_actor_pilot`: network_acceptance.
- `dash_selector_pilot`: packaged_runtime_verified.
- `melee_two_owner_damage_pilot`: replica_readiness, physical_input_tested.
- `melee_trace_pilot`: physical_input_tested.
- `character_inventory_clear_pilot`: physical_input_tested.
- `character_native_lifecycle_event_pilot`: physical_input_tested.
- `character_health_changed_receiver_pilot`: physical_input_tested.
- `auto_respawn_activation_pilot`: physical_input_tested.
- `auto_respawn_event_pilot`: physical_input_tested.
- `auto_respawn_listener_pilot`: physical_input_tested.
- `auto_respawn_helpers_pilot`: physical_input_tested.
- `pressed_widget_ability_pilot`: physical_input_tested.
- `held_widget_ability_pilot`: physical_input_tested.
- `jump_ability_pilot`: physical_input_tested.
- `device_color_pilot`: network_acceptance.
- `healthbar_public_ingress`: healthbar_specific_precompiled_caller_tested.
- `second_batch`: physical_touch_tested, packaged_runtime_verified.
- `world_pad_pilot`: packaged_runtime_verified.
- `debug_spread_pilot`: packaged_runtime_verified.
- `production_reticle_pilot`: physical_shotgun_pickup_tested, real_elimination_gameplay_tested, packaged_runtime_verified.
- `open_menu_pilot`: physical_touch_tested, network_acceptance, packaged_runtime_verified.
- `reticle_host_pilot`: packaged_runtime_verified.
- `ability_progress_pilot`: packaged_runtime_verified.
- `ability_failure_pilot`: packaged_runtime_verified.
- `dash_cooldown_pilot`: packaged_runtime_verified.
- `respawn_timer_pilot`: packaged_runtime_verified.
- `quickbar_slot_pilot`: packaged_runtime_verified.
- `nameplate_pilot`: packaged_runtime_verified.
- `inventory_pad_pilot`: production_placement_tested.
- `launcher_pilot`: production_placement_tested.
- `teleporter_pilot`: production_placement_tested.
- `action_touch_pilot`: physical_touch_tested, production_placement_tested.
- `heal_ability_pilot`: production_placement_tested.
- `explorer_state_pilot`: network_acceptance, packaged_runtime.
- `explorer_character_helpers_pilot`: physical_input_tested, network_acceptance, packaged_runtime.
- `explorer_style_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_callbacks_pilot`: network_acceptance, packaged_runtime.
- `explorer_init_pilot`: network_acceptance, packaged_runtime.
- `explorer_beginplay_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_input_pilot`: network_acceptance, packaged_runtime.
- `explorer_behavior_pilot`: network_acceptance, packaged_runtime.
- `explorer_screen_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_grid_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_toast_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_item_list_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_interact_pilot`: network_acceptance, packaged_runtime.
- `explorer_actions_pilot`: network_acceptance, packaged_runtime.
- `collect_cue_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_marker_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `explorer_shell_retention_review`: pixels_tested, network_acceptance, packaged_runtime.
- `hero_default_stencil_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `hero_default_equipment_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `hero_default_ragdoll_pilot`: pixels_tested, network_acceptance, packaged_runtime.
- `hero_default_death_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `hero_default_motion_pilot`: audio_playback_tested, pixels_tested, network_acceptance, packaged_runtime.
- `arena_ready_pilot`: pixels_tested, audio_playback_tested, network_acceptance, packaged_runtime.
- `arena_player_ui_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `arena_player_tile_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `arena_powerup_stat_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `arena_hud_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `arena_phases_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `arena_mode_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `arena_actor_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `arena_level_pilot`: network_acceptance, pixels_tested, packaged_runtime.
- `arena_bomb_visual_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `arena_bomb_base_pilot`: network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `arena_drop_bomb_pilot`: network_acceptance, physical_input_tested, pixels_tested, audio_playback_tested, packaged_runtime, spawn_failure_native_tested, commit_race_failure_native_tested.
- `migration_acceptance_review`: natural_animation_dispatch_tested.
- `footstep_animation_pilot`: normal_locomotion_input_state_machine_tested, network_acceptance, pixels_tested, audio_playback_tested, packaged_runtime.
- `footstep_locomotion_pilot`: network_acceptance, pixels_tested, audio_playback_tested.
- `footstep_visual_pilot`: audio_playback_tested, network_acceptance.
- `tdm_lethal_network_pilot`: network_acceptance, packaged_runtime, pixels_tested.
- `weapon_lethal_network_pilot`: network_acceptance, packaged_runtime, pixels_tested.
- `migration_package_inventory`: packaged_runtime_verified.
- `arena_local_input_pilot`: physical_input_tested, network_acceptance, packaged_runtime, pixels_tested, audio_playback_tested.
- `arena_natural_bomb_pilot`: network_acceptance, packaged_runtime, physical_input_tested, audio_playback_tested.
- `arena_native_delay_pilot`: packaged_runtime, network_acceptance.
- `arena_current_round_pilot`: packaged_runtime, network_acceptance.
- `runtime_property_notification_pilot`: packaged_runtime, network_acceptance.
- `weapon_two_owner_lethal_pilot`: physical_input_tested, pixels_tested, packaged_runtime, network_acceptance.
- `current_reload_family_pilot`: packaged_runtime, pixels_tested, physical_input_tested.
- `current_autoreload_family_pilot`: packaged_runtime, physical_input_tested.
- `current_integrated_weapon_profile_pilot`: packaged_runtime, physical_input_tested.
- `arena_opponent_bomb_pilot`: network_acceptance, packaged_runtime.

## Next evidence work

Complete the original0.14 Explorer/TopDownArena gameplay,presentation and applicable multi-client/local-player comparisons. All seven original0.9 criteria are accepted within their explicit Win64 Development scope;no tag or publication is authorized.

Recorded capabilities still need their linked semantic/source evidence reviewed; this index
does not rerun them. Continue unresolved readiness observations and the original version scope.

## Bounded current Editor candidate components (batch267)

Both current-SDK Third Person Editor variants pass with six directly inspected
rendered images. The five Generic Editor suites pass49 checks. The original
six-suite70 gate still requires actual current-source packaged21;the complete
candidate regression requirement stays unproven. See
`candidate_editor_regression_matrix.json` and ledger267 for passed components,
preserved failed captures,exact input archives and unchanged preexisting assets.
Original acceptance stays16/22. No compile/link,cook/package or full regression.

## Current Generic core candidate (batch268)

The actual packaged Game passes21 and a single clean candidate run then passes
all six original Generic suites70/70. This supersedes the Generic packaged gap
recorded in batch267;that earlier capture remains historical. The independent
Third Person/Lyra candidate/package boundaries and other original requirements
stay open. Original acceptance remains16/22. See ledger268 and the updated
candidate matrix for the cold Game build,versioned Entry-only package,failed
wrapper evidence and exact runtime/source/artifact fingerprints.

## Controlled reload and cleanup (batch269)

The exact original0.9 reload/cleanup condition is accepted;overall17/22.
Three controlled new-widget reload/GC cycles,four live profile round trips,
42 weapon scenarios (38 paired state comparisons),three same-Editor PIE
sessions and actual nineteen-phase server/two-client travel/rejoin leave no
owned callbacks,tickers or scopes. Class routers are restored before exit.
Reuse the current-SDK PIE capture after exact source/binary revalidation;
five fresh native processes all exit0. Zero compile,cook or full regression.
Rendered network screenshots retain TapIDs/invalid-tap warnings in the NoSound
fixture;complete visual/audio and packaged acceptance remain separate.

## Visible and current packaged weapon example (batch270)

The exact original0.9 visible/packaged weapon-example criterion is accepted;
overall18/22. Visible01 PID17164 and real packaged Game PID9996 both exit0,
pass42 scenarios/38 paired states and three controlled reload/GC cycles.
Directly review the1280x720 and1440x900 images:paired ammo text and all three
counter styles are visible without a shader preparation overlay. This does
not accept every gameplay visual transition or pixel/audio parity.

The guarded Game plan and actual build execute only three compiles,one link
and one metadata action (PID39092,85.931 seconds). No C++ source is changed.
An independent package copy reuses unchanged cooked assets:246 candidates,
460 Overlay assets and12 maps all match their original cook-plan source bytes.
Replace only this copy's executable and loose Python payload with the current
verified Game and862 project/two core scripts. Preserve its previous payloads,
old Game,original archive and cooked products;no cook occurs. Native owner,
replication,slot/possession signals and cleanup reuse batch269's verified
nineteen-phase Editor-game protocol. Packaged networking remains separate.

## Batch1A component state/visual and owner comparison (batch271)

The exact original0.9 Batch1A criterion is accepted;overall19/22. Five actual
fire,reload,weapon-switch,empty-ammo and Pawn-replacement checkpoints show
test-owned original BP left/Python right panels and active counter materials.
Both read the actual local native item;the real shipped HUD stays present.
Native02's current-SDK nineteen-phase server/two-client protocol passes two
travels,exit/rejoin and native owner/replication checks. All four peers exit0;
visual Widget roots close16/16,12/12,4/4 and0/0. No compile or cook occurs.

Native01's functional protocol passes,but a debug overlay obscures part of
the original view. Keep its five raw PNGs,reports and exact retired root/stage
adapter bytes unaccepted for visual completion. Native02 changes only three
test UI coordinates. Directly review all five new1280x720 images;preserve the
NoSound TapIDs warnings in logs. Component review is not whole-frame pixel,
hardware-input or audio acceptance. Twenty-one selected index checks,one parse
and two preflight rejection checks pass. Candidate,RC and full two-Experience
criteria remain open;original246/22 scope and existing production code remain.

## Current Third Person Game packages (batch272)

Both actual5.8.1 Game variants pass their original behavior contracts using
one verified Game build. Mixin432 and PythonFirst34344 exit0. Preserve the
missing optional Editor plugin cook failure and the stale0.7.0 literal version
wrapper failure. The latter is corrected over completed output without a new
runtime/cook. Canonical controls now require the exact staged descriptor value;
six actual-report/rejection checks pass from an immutable index. Preserve the
old driver bytes and per-variant payload snapshots. Original migration remains
19/22;only this candidate component is closed,with no C++ source change.

## Original candidate matrix aggregate (batch273)

**Original candidate matrix accepted batch273 (2026-10-28):**
The original0.9 Generic/both Third Person/Lyra candidate criterion is accepted;
overall20/22. Aggregate the existing clean Generic six-suite70/current11call/
three-PIE proof, both rendered current-SDK Third Person Editor captures and both
actual current Game packages. Lyra retains normal no-probe startup, the current
nineteen-phase two-client owner/travel/rejoin protocol, five directly reviewed
Batch1A paired views and the visible/actual packaged42-scenario weapon example.

Recheck actual source, binary, report, log and image fingerprints. Recover the
exact old bytes of three unselected ability/weapon test modules from the recorded
Examples Git parent; identify this as post-execution reconstruction. Both root
and stage input references remain explicit. Only these named test probes may use
the exact archive. Normal/focused weapon production inputs must still match.
Thirty-two immutable-index checks pass, including missing-family, stale-SDK,
missing-Game, ownership/visual/package cells and production-archive rejection.
No new native process, build, cook or broad regression. Full Explorer/TopDownArena
and RC API review remain separate original requirements. Preserve all246 paths,
22 original texts, prior19 accepted criteria, official Lyra and unrelated dirt.

## Supported API freeze review (batch274)

**Original supported API freeze accepted batch274 (2026-10-28):**
The original0.9 API inventory/migration/deprecation criterion is accepted;
overall21/22. All seven original0.9 criteria now have scoped evidence. Review
twelve inventory surfaces,retain experimental exclusions and compare the current
registration tables with continuation checkpoint e1199d2:213 module plus462
UObject method names,function expressions and flags are unchanged. This does not
certify every legacy wrapper,argument behavior,ABI,platform or configuration.

Keep compatibility forms,explicit fallback/exception behavior,controlled reload,
game-thread ownership,native-GC frame boundaries and signature restart rules.
Deprecation names the old API,replacement,examples and removal version with a
compatibility path. SDK236 fixes the bootstrap conversion lifetime defect.
The Lyra candidate requires the approved isolated eight-line Hero guard246;
official Lyra remains unpatched and its original finding remains open. Preserve
the original0.11 NetShooter native component discrepancy97 and its boundary.
No currently identified release-blocking defect remains in the reviewed supported
API after these dispositions. Unknown defects are not certified absent.
Twenty immutable-index checks pass;no new native process,build,cook,tag or release.
Full original0.14 Explorer/TopDownArena acceptance remains open. Preserve original
246 paths/22 texts,prior20 accepted criteria,official source and unrelated dirt.
