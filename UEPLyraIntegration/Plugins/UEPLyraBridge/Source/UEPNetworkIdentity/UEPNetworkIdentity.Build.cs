using UnrealBuildTool;

public class UEPNetworkIdentity : ModuleRules
{
    public UEPNetworkIdentity(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.Add("NetCore");
        SetupIrisSupport(Target);
    }
}
