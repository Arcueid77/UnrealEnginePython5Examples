"""Read-only native adapter source checks; compile/runtime are separate gates."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/"Plugins/UEPLyraBridge/Source/UEPNetworkIdentity"


class TestNetworkIdentityNativeSource(unittest.TestCase):
    def test_lookup_does_not_allocate_or_repair(self):
        source=(ROOT/"Private/UEPLyraNetworkIdentityLibrary.cpp").read_text(encoding="utf-8")
        for required in ("GetNetGUID(Object)","GetReplicatedRefHandle(Object)","Handle.GetId()","Guid.IsValid() && !Guid.IsDefault()","Guid.ToString()"):
            self.assertIn(required,source)
        for forbidden in ("GetOrAssignNetGUID","AssignNewNetGUID","CreateNetIDForObject","PreRegisterNewObject","AssignNetIDToObject","InitAbilityActorInfo","InitializeAbilitySystem","ForceNetUpdate"):
            self.assertNotIn(forbidden,source)
    def test_blueprint_shape_and_missing_identity_explicit(self):
        header=(ROOT/"Public/UEPLyraNetworkIdentityLibrary.h").read_text(encoding="utf-8")
        source=(ROOT/"Private/UEPLyraNetworkIdentityLibrary.cpp").read_text(encoding="utf-8")
        self.assertIn("BlueprintPure",header);self.assertIn("bool bValid = false",header)
        for field in ("WireId","ObjectPath","WorldPath","DriverPath","LocalRole","WorldSeconds","ActorAgeSeconds"):
            self.assertIn(field,header)
        for value in ("InvalidObject","NoWorld","NoNetDriver","Legacy","Iris"): self.assertIn(value,source)
    def test_iris_is_build_gated_and_no_local_system_id_used(self):
        source=(ROOT/"Private/UEPLyraNetworkIdentityLibrary.cpp").read_text(encoding="utf-8")
        build=(ROOT/"UEPNetworkIdentity.Build.cs").read_text(encoding="utf-8")
        self.assertIn("#if UE_WITH_IRIS",source);self.assertNotIn("GetReplicationSystemId()",source)
        self.assertIn("SetupIrisSupport(Target)",build);self.assertIn('"NetCore"',build)
    def test_legacy_identity_not_truncated_to_old_32_bit_value(self):
        source=(ROOT/"Private/UEPLyraNetworkIdentityLibrary.cpp").read_text(encoding="utf-8")
        self.assertNotIn("Guid.Value",source);self.assertNotIn('TEXT("%u")',source)
