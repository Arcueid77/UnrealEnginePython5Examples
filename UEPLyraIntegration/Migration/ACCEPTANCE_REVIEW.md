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

- `0.9.0` — A checked-in call/lifecycle matrix labels every path as tested supported, intentionally rejected, or bypass/unsupported, with reproducible fixtures. (ROADMAP.md:242; historical_claim_needs_source_and_evidence_review).
- `0.9.0` — The controlled reload and cleanup tests pass across repeated PIE, GC and travel; state, callbacks and router restoration are checked after teardown. (ROADMAP.md:244; historical_claim_needs_source_and_evidence_review).
- `0.9.0` — A visible and packaged weapon/ammo example proves native signal plus read-only sampled change updates, safe subscription removal and native authority ownership. (ROADMAP.md:246; historical_claim_needs_source_and_evidence_review).
- `0.9.0` — Batch 1A has original-BP/Python state and visual comparisons for weapon switching, firing, reload, empty ammo and Pawn replacement. One server and two clients prove that ammo/UI state never crosses local-player ownership. (ROADMAP.md:249; historical_claim_needs_source_and_evidence_review).
- `0.9.0` — Normal playable startup does not auto-run validation or request exit; explicitly enabled test modes retain bounded timeouts and cleanup evidence. Focused rendered weapon mode exits cleanly; the no-test-flag Lyra observation is bounded and stopped only by its owning test driver, not by a probe. (ROADMAP.md:252; historical_claim_needs_source_and_evidence_review).
- `0.9.0` — Generic, both Third Person variants and Lyra pass the candidate regression matrix; the missing Mixin Third Person visible gate is closed. (ROADMAP.md:256; historical_claim_needs_source_and_evidence_review).
- `0.9.0` — The supported API inventory and migration/deprecation rules are ready for RC freeze, with no known release-blocking correctness defects. (ROADMAP.md:258; historical_claim_needs_source_and_evidence_review).
- `0.10.0` — Each small batch passes original-BP/Python comparison without BP fallthrough. (ROADMAP.md:605; unproven).
- `0.10.0` — Pickup failure/success, cooldown/respawn and interaction effects match the baseline; two players cannot share another player's UI or claim state. (ROADMAP.md:606; unproven).
- `0.10.0` — Widget and Actor lifetime tests leave no owned subscriptions after teardown, travel or profile switching. (ROADMAP.md:608; unproven).
- `0.11.0` — Fire, reload, ammo exhaustion, switching, death and respawn pass BP/Python comparison in Standalone and one-server/two-client play. (ROADMAP.md:1705; unproven).
- `0.11.0` — Supported ability tasks, delegates, cancellation and latent boundaries have call/lifetime regressions; unsupported signatures fail explicitly. (ROADMAP.md:1707; unproven).
- `0.11.0` — No replacement changes UObject class identity or bypasses the required authority, prediction or replication checks. (ROADMAP.md:1709; unproven).
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

Review the remaining original0.9-0.14 gameplay,presentation,lifecycle,network and package requirements against their actual native evidence. The named Pawn/ASC readiness issue remains open;inventory disposition does not close these requirements.

Recorded capabilities still need their linked semantic/source evidence reviewed; this index
does not rerun them. Continue unresolved readiness observations and the original version scope.
