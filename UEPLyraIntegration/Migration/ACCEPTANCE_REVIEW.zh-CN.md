[English](ACCEPTANCE_REVIEW.md) | [简体中文](ACCEPTANCE_REVIEW.zh-CN.md)

<a id="migration-acceptance-review"></a>

# 迁移验收审核

原始的246候选路径、顺序和版本分配被保留。接受的原始范围：22/22标准和246个候选配置。接受结合了源绑定的先前本地证据和当前受影响的集成运行。它不是新的完全回归。适用范围：UE5.8/CPython3.11Win64Development。需要经过批准的隔离Lyra英雄守卫。

| 版本 | 原候选项 | 清单要求 |
| --- | ---: | ---: |
| 0.9.0 | 5 | 7 |
| 0.10.0 | 32 | 3 |
| 0.11.0 | 37 | 3 |
| 0.12.0 | 75 | 3 |
| 0.13.0 | 57 | 3 |
| 0.14.0 | 40 | 3 |

<a id="original-checklist-requirements"></a>

## 原始清单要求

- `0.9.0` — 签入的call/lifecycle 矩阵将每条路径标记为测试支持、有意拒绝或bypass/unsupported，并具有可重现的夹具。 （ROADMAP.md：242。all_33_documented_contract_paths_classified_with_pinned_reproducers_and_current_generic_calls_pie）。
- `0.9.0` — 受控重装和清理测试通过重复的PIE、GC 和行程。清理后检查状态、回调和路由器恢复。 （ROADMAP.md：244。current_sdk_controlled_reload_profile_gc_repeated_pie_and_two_travel_cleanup_source_verified）。
- `0.9.0` — 一个可见且打包的weapon/ammo示例证明了本机信号以及只读采样更改更新、安全订阅删除和本机权威所有权。 （ROADMAP.md：246。current_native_python_packaged_and_visible_weapon_with_native_signal_sampler_cleanup_owner_protocol_verified）。
- `0.9.0` — 第 1A 批次具有 original-BP/Python 武器切换、射击、重装、空弹药和Pawn 更换的状态和视觉比较。一台服务器和两个客户端证明ammo/UI状态永远不会跨越本地玩家所有权。 （ROADMAP.md：249。five_directly_reviewed_bp_python_weapon_component_views_and_current_native_two_owner_protocol_verified）。
- `0.9.0` — 正常可玩启动不会自动运行验证或请求退出。显式启用的测试模式保留有限的超时和清理证据。集中渲染的武器模式干净地退出。 no-test-flag Lyra 观察仅受其所属的测试驱动程序限制和停止，而不是受探针限制和停止。 （ROADMAP.md：252。native_normal_no_probe_observation_and_focused_rendered_probe_cleanup_and_sources_verified）。
- `0.9.0` — 通用，第三人称变体和Lyra都通过候选回归矩阵。失踪的Mixin第三人称可见门已关闭。 （ROADMAP.md：256。original_generic_third_person_and_lyra_candidate_cells_source_bound_and_aggregated）。
- `0.9.0` — 支持的 API 库存和 migration/deprecation 规则已准备好用于 RC 冻结，没有已知的发布阻塞正确性缺陷。 （ROADMAP.md：258。supported_api_inventory_compatibility_and_explicit_correctness_dispositions_reviewed_for_rc）。
- `0.10.0` — 每个小批量都通过original-BP/Python比较，没有BP失败。 （ROADMAP.md：605。all_original_32_candidates_140_entries_source_bound_native_comparisons_without_bp_business_fallthrough）。
- `0.10.0` — 拾取failure/success、cooldown/respawn和交互效果与基线匹配。两个玩家不能共享另一个玩家的 UI 或声明状态。 （ROADMAP.md：606。native_pickup_rejection_cooldown_interaction_effects_and_two_owner_ui_claim_sources_verified）。
- `0.10.0` — Widget 和 Actor 生命周期测试在清理、切图或Profile切换后不会留下任何拥有的订阅。 （ROADMAP.md：608。native_widget_actor_scope_teardown_travel_profile_cleanup_source_verified）。
- `0.11.0` — 开火、重装、弹药耗尽、切换、死亡和重生通行证 BP/Python 单机游戏和 one-server/two-client 游戏的比较。 （ROADMAP.md：1705。native_six_behavior_standalone_two_client_source_pins_and_original_python_outcomes_verified）。
- `0.11.0` — 支持的能力任务、委托、取消和潜在边界具有 call/lifetime 回归。不支持的签名显式失败。 （ROADMAP.md：1707。native_task_delegate_cancel_latent_and_timer_lifetimes_with_current_source_guards_verified）。
- `0.11.0` — 没有替换更改 UObject 类标识或绕过所需的权威、预测或复制检查。 （ROADMAP.md：1709。native_original_class_identity_authority_prediction_replication_boundaries_and_current_sources_verified）。
- `0.12.0` — Effect/audio触发，warmup/play/postgame，评分和通知与相同输入下的原始BP检查点匹配。 （ROADMAP.md：1722。native_effect_audio_phase_scoring_notification_checkpoints_and_current_sources_verified）。
- `0.12.0` — AI task/service 结果和取消是可重现的。长时间运行的任务不会保留已销毁的Pawn或World。 （ROADMAP.md：1724。native_ai_eqs_outcomes_and_pawn_world_cancellation_with_collection_verified）。
- `0.12.0` — 多客户端score/phase状态，本地通知和清理一致。 （ROADMAP.md：1726。native_multi_client_score_phase_local_notification_cleanup_and_current_sources_verified）。
- `0.13.0` — 导航、focus/back 行为、设置持久性、会话结果和重播控制通过 original-BP/Python 比较。 （ROADMAP.md：1737。native_navigation_settings_sessions_replay_comparisons_and_current_sources_verified）。
- `0.13.0` — 重复屏幕open/close 和切图恢复订阅和状态。 （ROADMAP.md：1739。paired_native_reopen_travel_state_and_callback_restoration_verified）。
- `0.13.0` — Failures/cancellations 经过测试，仅在成功路径上不被接受。 （ROADMAP.md：1740。native_ui_failure_and_cancellation_evidence_and_current_source_verified）。
- `0.14.0` — 两种体验均通过original-BP/Python游戏玩法、演示和适用的multi-client/local-player比较。 （ROADMAP.md：1751。all_original_explorer_arena_components_and_current_native_bp_python_player_comparisons_verified）。
- `0.14.0` — 每个经过审核的候选者都被迁移、显式保留、通过检查的引用无法访问或指定的阻止程序。不存在无声的覆盖差距。 （ROADMAP.md：1753。current_candidate_source_binding_retention_and_named_issue_dispositions_verified）。
- `0.14.0` — 仅配置 BP shell 和 animation/editor/test 排除已记录原因。游戏项目 C++ 迁移仍然是一个单独的阶段。 （ROADMAP.md：1755。per_asset_reasons_and_current_reference_stage_copies_verified）。

<a id="explicit-unverified-capabilities"></a>

## 显式的未经验证的功能

这些是需要需求和平台审查的记录标志，而不是自动新范围。

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

<a id="next-evidence-work"></a>

## 下一步取证工作

接受原约定的Python更换范围。其他platforms/configurations，更广泛的本机 C++ 迁移和发布仍然是单独的工作。

记录的功能仍需要对其链接的semantic/source证据进行审查。该索引不会重新运行它们。继续未解决的准备情况观察和原始版本范围。

<a id="bounded-current-editor-candidate-components-batch267"></a>

## 有界当前编辑器候选组件 (batch267)

当前的两个SDK第三人称编辑器变体都通过了六个直接检查的渲染图像。五个通用编辑器套件通过了 49 项检查。最初的六套件 70 门仍然需要实际的电流源封装21。完整的候选回归要求尚未得到证实。请参阅 `candidate_editor_regression_matrix.json` 和 ledger267 了解已通过的组件、保留的失败捕获、精确的输入档案和未更改的预先存在的资产。原始接受stays16/22.否compile/link、cook/package或完全回归。

<a id="current-generic-core-candidate-batch268"></a>

## 当前通用核心候选者（batch268）

实际打包的游戏通过了21，然后一个干净的候选运行通过了所有六个原始通用suites70/70.，这取代了批次267中记录的通用打包间隙。早期的捕获仍然是历史的。独立的第三Person/Lyracandidate/package边界和其他原始要求保持开放。原始接受remains16/22. 请参阅ledger268 和更新后的冷游戏构建候选矩阵、版本化的Entry-only 包、失败的包装证据和准确的runtime/source/artifact 指纹。

<a id="controlled-reload-and-cleanup-batch269"></a>

## 受控重新加载和清理（batch269）

接受确切的原始0.9reload/cleanup条件。overall17/22.三个受控新部件reload/GC周期，四个实时Profile往返，42武器场景（38配对状态比较），三个相同编辑器PIE 会话和实际的十九阶段 server/two-client travel/rejoin 不留下任何拥有的回调、代码或范围。类路由器在退出前恢复。在精确的 source/binary 重新验证后重用当前的-SDK PIE 捕获。五个新的本机进程全部 exit0。零编译、Cook或完全回归。渲染的网络截图在NoSound夹具中保留TapIDs/invalid-tap警告。完整的visual/audio和打包验收保持分开。

<a id="visible-and-current-packaged-weapon-example-batch270"></a>

## 可见且当前打包的武器示例（batch270）

接受确切的原始0.9visible/packaged武器示例标准。 overall18/22. Visible01 PID17164 和真实打包的游戏 PID9996 都 exit0、pass42 scenarios/38 配对状态和三个受控的 reload/GC 周期。直接查看 1280x720 和 1440x900 图像：配对弹药文本和所有三种计数器样式均可见，无需着色器准备覆盖。这并不接受每个游戏视觉过渡或pixel/audio奇偶校验。

受保护的游戏计划和实际构建仅执行 3 次编译、1 个链接和 1 个元数据操作（PID39092，85.931 秒）。没有更改 C++ 源代码。独立的包副本重用未更改的烘焙资源：246候选资源、460覆盖资源和12个映射均与其原始Cook计划源字节匹配。仅将此副本的可执行文件和松散的 Python 有效负载替换为当前经过验证的游戏和862 project/two 核心脚本。保留以前的有效负载、旧游戏、原始存档和熟品。不会发生熟化。本地所有者、复制、slot/possession信号和清理重用batch269经过验证的十九阶段编辑器游戏协议。打包网络仍然是独立的。

<a id="batch1a-component-statevisual-and-owner-comparison-batch271"></a>

## Batch1A组件state/visual和所有者比较（batch271）

准确的原版0.9Batch1A标准被接受。overall19/22.五个实际开火、重装弹、武器切换、空弹药和Pawn替换检查点显示测试拥有的原始BPleft/Python右面板和主动反制材料。两者都读取实际的本地本地项目。实际发货的HUD仍然存在。 Native02当前的SDK十九阶段server/two-client协议通过了两次切图，exit/rejoin和本机owner/replication检查。所有四个对等点 exit0。可视化 Widget 根close16/16、12/12、4/4 and0/0. 不会发生编译或烘焙。

Native01 的功能协议通过了，但是调试覆盖层遮盖了部分原始视图。保留其五个原始 PNG、报告和确切已退役的 root/stage 适配器字节，以实现视觉完成。 Native02仅更改三个测试UI坐标。直接查看所有五个新的1280x720图像。在日志中保留NoSoundTapIDs警告。组件审查不是全帧像素、硬件输入或音频验收。二十一项选定的索引检查、一项解析和两项预检拒绝检查均通过。候选者、RC 和完整的两项经验标准保持开放。original246/22 范围和现有生产代码保持不变。

<a id="current-third-person-game-packages-batch272"></a>

## 当前第三人称游戏包（batch272）

两种实际5.8.1 游戏变体都使用一个经过验证的游戏构建来传递其原始行为契约。 Mixin432 和 PythonFirst34344 exit0。保留缺少的可选编辑器插件烘焙失败和 stale0.7.0 文字版本包装器失败。后者在没有新的runtime/cook.的情况下对已完成的输出进行了纠正。规范控制现在需要精确的分阶段描述符值。六个 actual-report/rejection 检查通过不可变索引。保留旧的驱动程序字节和每个变体的有效负载快照。原来的迁移仍然是19/22。只是关闭了这个候选组件，没有更改C++源代码。

<a id="original-candidate-matrix-aggregate-batch273"></a>

## 原始候选矩阵聚合（batch273）

**原始候选矩阵接受batch273 (2026-10-28):**原始0.9Generic/both接受第三个Person/Lyra候选标准。 overall20/22. 聚合现有的干净通用six-suite70/current11call/ 三个-PIE 证明，均呈现当前-SDK 第三人称编辑器捕获以及实际的当前游戏包。 Lyra保留了正常的无探针启动、当前十九阶段二客户端owner/travel/rejoin协议、五个直审Batch1A配对视图以及visible/actual打包的42场景武器示例。

重新检查实际源、二进制、报告、日志和图像指纹。从记录的示例 Git 父级中恢复三个未选择的 ability/weapon 测试模块的确切旧字节。将此识别为执行后重建。根和阶段输入引用都保持明确。只有这些指定的测试探针可以使用确切的存档。 Normal/focused 武器生产投入仍必须匹配。通过了 32 项不可变索引检查，包括缺失系列、陈旧SDK、缺失游戏、ownership/visual/package 单元和生产存档拒绝。没有新的本机流程、构建、Cook或广泛的回归。完整的Explorer/TopDownArena和RCAPI审查仍然是单独的原始要求。保留所有246条路径，22原始文本，先前的19个接受标准，官方Lyra和不相关的污垢。

<a id="supported-api-freeze-review-batch274"></a>

## 支持API冻结审核（batch274）

**原始支持API冻结接受的batch274（2026-10-28）：**原始0.9APIinventory/migration/deprecation标准被接受。 overall21/22. 所有七个原始0.9 标准现在都有范围证据。检查 12 个清单表面，保留实验排除并将当前注册表与继续检查点 e1199d2 进行比较：213 模块 plus462 UObject 方法名称、函数表达式和标志未更改。这并不验证每个遗留包装器、参数行为、ABI、平台或配置。

保持兼容性形式，显式的fallback/exception行为，受控的重新加载，游戏线程所有权，本机GC帧边界和签名重新启动规则。弃用使用兼容性路径命名旧的 API、替换、示例和删除版本。 SDK236修复了引导转换生命周期缺陷。 Lyra候选者需要经过批准的隔离八线英雄守卫246。官方Lyra仍未修补，其原始发现仍处于开放状态。保留原始0.11NetShooter原生组件discrepancy97及其边界。在这些处置之后，已审核的受支持API中不存在当前已识别的发布阻塞缺陷。未知缺陷不会被证明不存在。二十个不可变索引检查通过。没有新的本机进程、构建、Cook、标记或发布。完整原件0.14Explorer/TopDownArena接受仍然开放。保留原始246paths/22文本，prior20接受的标准，官方来源和不相关的污垢。

<a id="final-original-scope-acceptance-batch275"></a>

## 最终原始范围验收（batch275）

**原始迁移范围接受batch275（2026-10-28）：22/22，246候选版。**所有原始0。9-0.14标准在UE5.8/CPython3.11内接受Win64Development。保留491个原始审计资产，246候选paths/order/versions，182配置shell，63保留资产和11项范围审查不变。这接受商定的Python替换范围。其他platforms/configurations，更广泛的原生游戏-C++迁移，RC标签和发布保持分开。

最终的0.14标准涵盖了所有四十个Explorer/TopDownArena候选者。 Recheck49 原始组件捕获以及针对当前生产代码和原始语义报告的共享GetReady Cue 父级。当前的六种original/Python积分对通过：库存菜单、放置交互、follow/navigation/cancel/travel、两客户端预测collect/sit、两本地玩家可变帧自然bombs/death/refund/HUD、对手death/kill/team归因。 All16 接受本机进程 exit0。六个实际的竞技场图像显示owner0 炸弹1->0->1，而owner1 保持1。保留原生debug/warning文本和死亡过渡模糊。

保留5个较早的网络组：1个较早的阳性组和4个失败组，总共15进程。31新的UE进程，包括final16。第一个 Python 故障是过度指定的服务器本地剪辑结束计数器。共享读取器更正保留了Windows共享违规中断。确切的 callback/native-end-observer 等待在未更改的 70 秒阶段界限内失败并保持保留。最终证据表明，相同的原生能力在进入时处于活动状态，然后在规范count0/no任务中处于非活动状态。仍需要客户端蒙太奇完成。 Original/Python 权威拾取，车主复制，进度与清理结果一致。没有声明通用的本机 C++ 事件拦截。

保留初始的 SDK-status 和引用的 helper-root 预启动失败。控件使用SDK236，通过显式变量绑定辅助路径，并使用现有的共享 JSON 读取器进行网络监视器。存档确切的退役测试/控制输入。只有两个指定的测试模块和包装器可以使用它们。不会发生生产策略、资产、正常引导、C++ 源、构建或烘焙更改。三十三次不可变索引Python检查和十六次精确索引PS控制检查通过。仅在输入、Git 生产增量、原始库存和仅元数据清单更改经过验证后，才能重用之前的 21 个标准。一起提升所有 22 条标准和 246 条候选倾向。历史上的每次捕获范围限制保持不变。官方Lyra保持不变。仍需要经过批准的隔离英雄guard246。所有六个不相关的修改文件均被保留。
