"""Choose an explicit validation lane; normal play must never auto-quit."""


def validation_module(arguments):
    if any(argument.startswith("-UEPWeaponDecalsResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_decals_validation"
    if any(argument.startswith("-UEPWeaponFireFXResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_fire_fx_validation"
    if any(argument.startswith("-UEPWeaponActorBeginResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_actor_begin_validation"
    if any(argument.startswith("-UEPWeaponActorFireResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_actor_fire_validation"
    if any(argument.startswith("-UEPWeaponActorHelpersResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_actor_helpers_validation"
    if any(argument.startswith("-UEPGrenadeFlightNetworkResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_flight_network_validation"
    if any(argument.startswith("-UEPGrenadeDetonateNetworkResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_detonate_network_validation"
    if any(argument.startswith("-UEPGrenadeDetonateResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_detonate_validation"
    if any(argument.startswith("-UEPGrenadeHitResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_hit_validation"
    if "-UEPGrenadeHeadless" in arguments and any(argument.startswith("-UEPGrenadeBeginResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_begin_headless_validation"
    if any(argument.startswith("-UEPGrenadeBeginResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_begin_validation"
    if any(argument.startswith("-UEPGrenadeActionsResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_actions_validation"
    if any(argument.startswith("-UEPGrenadeCleanupResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_cleanup_validation"
    if any(argument.startswith("-UEPGrenadeVFXResult=") for argument in arguments):
        return "uep_lyra_weapons.grenade_vfx_validation"
    if any(argument.startswith("-UEPGrenadeActivationNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.grenade_activation_network_validation"
    if any(argument.startswith("-UEPGrenadeActivationResult=") for argument in arguments):
        return "uep_lyra_abilities.grenade_activation_validation"
    if any(argument.startswith("-UEPGrenadeWidgetNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.grenade_widget_network_validation"
    if any(argument.startswith("-UEPGrenadeWidgetResult=") for argument in arguments):
        return "uep_lyra_abilities.grenade_widget_validation"
    if any(argument.lower().startswith("-run=") for argument in arguments):
        return None
    if any(argument.startswith("-UEPMeleeTraceNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.melee_trace_network_validation"
    if any(argument.startswith("-UEPMeleeTraceResult=") for argument in arguments):
        return "uep_lyra_abilities.melee_trace_validation"
    if any(argument.startswith("-UEPMeleeActivationNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.melee_activation_network_validation"
    if any(argument.startswith("-UEPMeleeActivationResult=") for argument in arguments):
        return "uep_lyra_abilities.melee_activation_validation"
    if any(argument.startswith("-UEPMeleeHitMontageNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.melee_hit_montage_network_validation"
    if any(argument.startswith("-UEPMeleeHitMontageResult=") for argument in arguments):
        return "uep_lyra_abilities.melee_hit_montage_validation"
    if any(argument.startswith("-UEPDashTasksNetworkLifecycleResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_tasks_network_lifecycle_validation"
    if any(argument.startswith("-UEPDashTasksLifecycleResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_tasks_lifecycle_validation"
    if any(argument.startswith("-UEPDashTasksNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_tasks_network_validation"
    if any(argument.startswith("-UEPDashTasksResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_tasks_validation"
    if any(argument.startswith("-UEPDashActivationNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_activation_network_validation"
    if any(argument.startswith("-UEPDashActivationResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_activation_validation"
    if any(argument.startswith("-UEPDashLocalDirectionNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_local_direction_network_validation"
    if any(argument.startswith("-UEPDashLocalDirectionResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_local_direction_validation"
    if any(argument.startswith("-UEPDashRPCInputNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_rpc_input_network_validation"
    if any(argument.startswith("-UEPDashSelectorNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_selector_network_validation"
    if any(argument.startswith("-UEPDashSelectorResult=") for argument in arguments):
        return "uep_lyra_abilities.dash_selector_validation"
    if any(argument.startswith("-UEPCharacterAudioResult=") for argument in arguments):
        return "uep_lyra_characters.emote_audio_validation"
    if any(argument.startswith("-UEPCharacterPartsNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.parts_changed_network_validation"
    if any(argument.startswith("-UEPCharacterPartsResult=") for argument in arguments):
        return "uep_lyra_characters.parts_changed_validation"
    if any(argument.startswith("-UEPCharacterHealthNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.health_changed_network_validation"
    if any(argument.startswith("-UEPCharacterHealthResult=") for argument in arguments):
        return "uep_lyra_characters.health_changed_validation"
    if any(argument.startswith("-UEPCharacterInputNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.enhanced_input_network_validation"
    if any(argument.startswith("-UEPCharacterInputResult=") for argument in arguments):
        return "uep_lyra_characters.enhanced_input_validation"
    if any(argument.startswith("-UEPCharacterDeathReplicationNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.death_replication_network_validation"
    if any(argument.startswith("-UEPCharacterDeathStartedNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.death_started_network_validation"
    if any(argument.startswith("-UEPCharacterDeathStartedResult=") for argument in arguments):
        return "uep_lyra_characters.death_started_validation"
    if any(argument.startswith("-UEPCharacterRagdollNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.ragdoll_network_validation"
    if any(argument.startswith("-UEPCharacterRagdollResult=") for argument in arguments):
        return "uep_lyra_characters.ragdoll_validation"
    if any(argument.startswith("-UEPCharacterEquipmentHideNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.equipment_hide_network_validation"
    if any(argument.startswith("-UEPCharacterEquipmentHideResult=") for argument in arguments):
        return "uep_lyra_characters.equipment_hide_validation"
    if any(argument.startswith("-UEPCharacterBeginPlayNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.begin_play_network_validation"
    if any(argument.startswith("-UEPCharacterBeginPlayResult=") for argument in arguments):
        return "uep_lyra_characters.begin_play_validation"
    if any(argument.startswith("-UEPCharacterVisibilityNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.visibility_network_validation"
    if any(argument.startswith("-UEPCharacterVisibilityResult=") for argument in arguments):
        return "uep_lyra_characters.visibility_validation"
    if any(argument.startswith("-UEPCharacterPossessedNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.possessed_network_validation"
    if any(argument.startswith("-UEPCharacterPossessedResult=") for argument in arguments):
        return "uep_lyra_characters.possessed_validation"
    if any(argument.startswith("-UEPCharacterWaitNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_wait_network_validation"
    if any(argument.startswith("-UEPCharacterWaitResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_wait_validation"
    if any(argument.startswith("-UEPCharacterReadyNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_ready_network_validation"
    if any(argument.startswith("-UEPCharacterReadyResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_ready_validation"
    if any(argument.startswith("-UEPCharacterLegacyNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.legacy_player_info_network_validation"
    if any(argument.startswith("-UEPCharacterLegacyResult=") for argument in arguments):
        return "uep_lyra_characters.legacy_player_info_validation"
    if any(argument.startswith("-UEPCharacterListenerNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.team_listener_network_validation"
    if any(argument.startswith("-UEPCharacterListenerResult=") for argument in arguments):
        return "uep_lyra_characters.team_listener_validation"
    if any(argument.startswith("-UEPCharacterObserverNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.team_observer_network_validation"
    if any(argument.startswith("-UEPCharacterObserverResult=") for argument in arguments):
        return "uep_lyra_characters.team_observer_validation"
    if any(argument.startswith("-UEPCharacterLifecycleNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.lifecycle_network_validation"
    if any(argument.startswith("-UEPCharacterLifecycleResetResult=") for argument in arguments):
        return "uep_lyra_characters.lifecycle_reset_validation"
    if any(argument.startswith("-UEPCharacterLifecycleResult=") for argument in arguments):
        return "uep_lyra_characters.lifecycle_validation"
    if any(argument.startswith("-UEPCharacterStencilNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.stencil_network_validation"
    if any(argument.startswith("-UEPCharacterStencilResult=") for argument in arguments):
        return "uep_lyra_characters.stencil_validation"
    if any(argument.startswith("-UEPCharacterTeamNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.team_cosmetics_network_validation"
    if any(argument.startswith("-UEPCharacterTeamResult=") for argument in arguments):
        return "uep_lyra_characters.team_cosmetics_validation"
    if any(argument.startswith("-UEPCharacterOutlineNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.outline_network_validation"
    if any(argument.startswith("-UEPCharacterOutlineResult=") for argument in arguments):
        return "uep_lyra_characters.outline_validation"
    if any(argument.startswith("-UEPCharacterLoadoutNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.initial_inventory_network_validation"
    if any(argument.startswith("-UEPCharacterLoadoutResult=") for argument in arguments):
        return "uep_lyra_characters.initial_inventory_natural_validation" if "-UEPCharacterLoadoutNatural" in arguments else "uep_lyra_characters.initial_inventory_validation"
    if any(argument.startswith("-UEPCharacterQuickbarNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.quickbar_input_network_validation"
    if any(argument.startswith("-UEPCharacterQuickbarResult=") for argument in arguments):
        return "uep_lyra_characters.quickbar_input_validation"
    if any(argument.startswith("-UEPCharacterAudioNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.emote_audio_network_validation"
    if "-UEPCharacterInventory" in arguments and any(argument.startswith("-UEPAutoRespawnResetResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_clear_reset_validation"
    if "-UEPCharacterInventory" in arguments and any(argument.startswith("-UEPAutoRespawnHelpersNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_clear_network_validation"
    if "-UEPCharacterInventory" in arguments and any(argument.startswith("-UEPAutoRespawnHelpersResult=") for argument in arguments):
        return "uep_lyra_characters.inventory_clear_validation"
    if any(argument.startswith("-UEPAutoRespawnResetResult=") for argument in arguments):
        return "uep_lyra_abilities.auto_respawn_reset_validation"
    if any(argument.startswith("-UEPAutoRespawnResetNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.auto_respawn_reset_network_validation"
    if any(argument.startswith("-UEPAutoRespawnLifecycleResult=") for argument in arguments):
        return "uep_lyra_abilities.auto_respawn_lifecycle_validation"
    if "-UEPAutoRespawnActivation" in arguments:
        if any(argument.startswith("-UEPAutoRespawnHelpersNetworkResult=") for argument in arguments):
            return "uep_lyra_abilities.auto_respawn_activation_network_validation"
        if any(argument.startswith("-UEPAutoRespawnHelpersResult=") for argument in arguments):
            return "uep_lyra_abilities.auto_respawn_activation_validation"
    if "-UEPAutoRespawnEvents" in arguments:
        if any(argument.startswith("-UEPAutoRespawnHelpersNetworkResult=") for argument in arguments):
            return "uep_lyra_abilities.auto_respawn_events_network_validation"
        if any(argument.startswith("-UEPAutoRespawnHelpersResult=") for argument in arguments):
            return "uep_lyra_abilities.auto_respawn_events_validation"
    if "-UEPAutoRespawnListeners" in arguments:
        if any(argument.startswith("-UEPAutoRespawnHelpersNetworkResult=") for argument in arguments):
            return "uep_lyra_abilities.auto_respawn_listeners_network_validation"
        if any(argument.startswith("-UEPAutoRespawnHelpersResult=") for argument in arguments):
            return "uep_lyra_abilities.auto_respawn_listeners_validation"
    if any(argument.startswith("-UEPAutoRespawnHelpersNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.auto_respawn_helpers_network_validation"
    if any(argument.startswith("-UEPAutoRespawnHelpersResult=") for argument in arguments):
        return "uep_lyra_abilities.auto_respawn_helpers_validation"
    if any(argument.startswith("-UEPWidgetPressedContextResult=") for argument in arguments):
        return "uep_lyra_abilities.widget_pressed_context_validation"
    if any(argument.startswith("-UEPWidgetPressedNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.widget_pressed_network_validation"
    if any(argument.startswith("-UEPWidgetPressedResult=") for argument in arguments):
        return "uep_lyra_abilities.widget_pressed_validation"
    if any(argument.startswith("-UEPWidgetHeldNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.widget_held_network_validation"
    if any(argument.startswith("-UEPWidgetHeldResult=") for argument in arguments):
        return "uep_lyra_abilities.widget_held_validation"
    if any(argument.startswith("-UEPEmoteNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.emote_network_validation"
    if any(argument.startswith("-UEPEmoteResult=") for argument in arguments):
        return "uep_lyra_abilities.emote_validation"
    if any(argument.startswith("-UEPDeviceColorResult=") for argument in arguments):
        return "uep_lyra_devices.team_color_validation"
    if any(argument.startswith("-UEPSpawnEffectNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.spawn_effect_network_validation"
    if any(argument.startswith("-UEPSpawnEffectResult=") for argument in arguments):
        return "uep_lyra_abilities.spawn_effect_validation"
    if any(argument.startswith("-UEPWeaponInstanceDeathResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_instance_death_validation"
    if any(argument.startswith("-UEPWeaponInstanceResult=") for argument in arguments):
        return "uep_lyra_weapons.weapon_instance_validation"
    if any(argument.startswith("-UEPReloadMagazineNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.reload_magazine_network_validation"
    if any(argument.startswith("-UEPReloadMagazineResult=") for argument in arguments):
        return "uep_lyra_abilities.reload_magazine_validation"
    if any(argument.startswith("-UEPDropWeaponNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.drop_weapon_network_validation"
    if any(argument.startswith("-UEPDropWeaponResult=") for argument in arguments):
        return "uep_lyra_abilities.drop_weapon_validation"
    if any(argument.startswith("-UEPADSNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.ads_network_validation"
    if any(argument.startswith("-UEPADSResult=") for argument in arguments):
        return "uep_lyra_abilities.ads_validation"
    if any(argument.startswith("-UEPHeroHealNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.hero_heal_network_validation"
    if any(argument.startswith("-UEPHeroHealResult=") for argument in arguments):
        return "uep_lyra_abilities.hero_heal_validation"
    if any(argument.startswith("-UEPAutoReloadNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.autoreload_network_validation"
    if any(argument.startswith("-UEPAutoReloadResult=") for argument in arguments):
        return "uep_lyra_abilities.autoreload_validation"
    if any(argument.startswith("-UEPCosmeticNetworkResult=") for argument in arguments):
        return "uep_lyra_characters.cosmetic_network_validation"
    if any(argument.startswith("-UEPCosmeticResult=") for argument in arguments):
        return "uep_lyra_characters.cosmetic_validation"
    if any(argument.startswith("-UEPDeathNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.death_network_validation"
    if any(argument.startswith("-UEPDeathAbilityResult=") for argument in arguments):
        return "uep_lyra_abilities.death_validation"
    if any(argument.startswith("-UEPQuickslotNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.quickslot_network_validation"
    if any(argument.startswith("-UEPQuickslotResult=") for argument in arguments):
        return "uep_lyra_abilities.quickslot_validation"
    if any(argument.startswith("-UEPJumpNetworkResult=") for argument in arguments):
        return "uep_lyra_abilities.jump_network_validation"
    if any(argument.startswith("-UEPJumpAbilityResult=") for argument in arguments):
        return "uep_lyra_abilities.jump_validation"
    if any(argument.startswith("-UEPAbilityWidgetResult=") for argument in arguments):
        return "uep_lyra_abilities.widget_validation"
    if any(argument.startswith("-UEPInteractionInspectionResult=") for argument in arguments):
        if "-UEPInteractionProducer" in arguments:
            return "uep_lyra_world.interaction_producer_network"
        return "uep_lyra_world.interaction_inspection"
    if any(argument.startswith("-UEPLyraHUDVisualResult=") for argument in arguments):
        return "uep_lyra_hud.visual_validation"
    if any(argument.startswith("-UEPReticleAmmoResult=") for argument in arguments):
        return "uep_lyra_hud.reticle_validation"
    if any(argument.startswith("-UEPTypedMessageResult=") for argument in arguments):
        return "uep_lyra_hud.message_payload_validation"
    if any(argument.startswith("-UEPWeaponReticleResult=") for argument in arguments):
        return "uep_lyra_hud.weapon_reticle_validation"
    if any(argument.startswith("-UEPOpenMenuResult=") for argument in arguments):
        return "uep_lyra_hud.open_menu_validation"
    if any(argument.startswith("-UEPReticleHostResult=") for argument in arguments):
        return "uep_lyra_hud.reticle_host_validation"
    if any(argument.startswith("-UEPAbilityProgressResult=") for argument in arguments):
        return "uep_lyra_hud.ability_progress_validation"
    if any(argument.startswith("-UEPDashResult=") for argument in arguments):
        return "uep_lyra_hud.dash_cooldown_validation"
    if any(argument.startswith("-UEPDashNativeResult=") for argument in arguments):
        return "uep_lyra_hud.dash_native_validation"
    if any(argument.startswith("-UEPRespawnResult=") for argument in arguments):
        return "uep_lyra_hud.respawn_timer_validation"
    if any(argument.startswith("-UEPRespawnNativeResult=") for argument in arguments):
        return "uep_lyra_hud.respawn_native_validation"
    if any(argument.startswith("-UEPQuickBarSlotResult=") for argument in arguments):
        return "uep_lyra_hud.quickbar_slot_validation"
    if any(argument.startswith("-UEPNameplateComponentsResult=") for argument in arguments):
        return "uep_lyra_hud.nameplate_components_validation"
    if any(argument.startswith("-UEPInventoryPadResult=") for argument in arguments):
        return "uep_lyra_world.inventory_pad_validation"
    if any(argument.startswith("-UEPInventoryPadPlayerResult=") for argument in arguments):
        return "uep_lyra_world.inventory_pad_player_validation"
    if any(argument.startswith("-UEPGrantGEResult=") for argument in arguments):
        return "uep_lyra_world.grant_ge_pad_validation"
    if any(argument.startswith("-UEPLauncherResult=") for argument in arguments):
        return "uep_lyra_world.launcher_validation"
    if any(argument.startswith("-UEPSpawnerResult=") for argument in arguments):
        return "uep_lyra_world.spawner_validation"
    if any(argument.startswith("-UEPTeleporterResult=") for argument in arguments):
        return "uep_lyra_world.teleporter_validation"
    if any(argument.startswith("-UEPActionTouchResult=") for argument in arguments):
        return "uep_lyra_hud.action_touch_validation"
    if any(argument.startswith("-UEPActionTouchClickResult=") for argument in arguments):
        return "uep_lyra_hud.action_touch_click_validation"
    if any(argument.startswith("-UEPHealAbilityResult=") for argument in arguments):
        return "uep_lyra_world.heal_ability_validation"
    if any(argument.startswith("-UEPNameplateResult=") for argument in arguments):
        return "uep_lyra_hud.nameplate_validation"
    if any(argument.startswith("-UEPAbilityFailureResult=") for argument in arguments):
        if "-UEPAbilityFailureNativeProducer" in arguments:
            return "uep_lyra_hud.ability_failure_native_validation"
        if "-UEPAbilityFailureCulture" in arguments:
            return "uep_lyra_hud.ability_failure_culture_validation"
        return "uep_lyra_hud.ability_failure_validation"
    if any(argument.startswith("-UEPEffectPadResult=") for argument in arguments):
        return "uep_lyra_world.effect_pad_validation"
    if any(argument.startswith("-UEPEffectPadGameplayResult=") for argument in arguments):
        return "uep_lyra_world.effect_pad_gameplay_validation"
    if "-UEPEffectPadNetwork" in arguments:
        return "uep_lyra_world.effect_pad_network_validation"
    if "-UEPInventoryPadNetwork" in arguments:
        return "uep_lyra_world.inventory_pad_network_validation"
    if "-UEPGrantGENetwork" in arguments:
        return "uep_lyra_world.grant_ge_pad_network_validation"
    if "-UEPLauncherNetwork" in arguments:
        return "uep_lyra_world.launcher_network_validation"
    if "-UEPSpawnerNetwork" in arguments:
        return "uep_lyra_world.spawner_network_validation"
    if "-UEPTeleporterNetwork" in arguments:
        return "uep_lyra_world.teleporter_network_validation"
    if "-UEPActionTouchNetwork" in arguments:
        return "uep_lyra_hud.action_touch_network_validation"
    if "-UEPHealAbilityNetwork" in arguments:
        return "uep_lyra_world.heal_ability_network_validation"
    if "-UEPLyraWeaponNetwork" in arguments:
        return "uep_lyra_weapon_network"
    if "-UEPLyraMultiClient" in arguments:
        return "uep_lyra_network"
    if any(argument.startswith("-UEPLyraWeaponHUDResult=") for argument in arguments):
        return "uep_lyra_hud.weapon_validation"
    if any(argument.startswith("-UEPLyraSmokeResult=") or argument.startswith("-UEPLyraMode=")
           for argument in arguments):
        return "uep_lyra_probe"
    return None
