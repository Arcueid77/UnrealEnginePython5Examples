// Kept independent of LyraGame: only existing Engine network ids are read.
#include "UEPLyraNetworkIdentityLibrary.h"

#include "Engine/NetDriver.h"
#include "Engine/PackageMapClient.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

#if UE_WITH_IRIS
#include "Iris/ReplicationSystem/NetRefHandle.h"
#include "Iris/ReplicationSystem/ObjectReplicationBridge.h"
#include "Iris/ReplicationSystem/ReplicationSystem.h"
#endif

#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPLyraNetworkIdentityLibrary)

FUEPLyraNetworkIdentity UUEPLyraNetworkIdentityLibrary::ReadNetworkIdentity(const UObject* Object)
{
    FUEPLyraNetworkIdentity Result;
    if (!IsValid(Object))
    {
        Result.Transport = TEXT("InvalidObject");
        return Result;
    }

    Result.ObjectPath = Object->GetPathName();
    UWorld* World = Object->GetWorld();
    if (!World)
    {
        Result.Transport = TEXT("NoWorld");
        return Result;
    }

    Result.WorldPath = World->GetPathName();
    Result.WorldSeconds = World->GetTimeSeconds();
    const AActor* Actor = Cast<AActor>(Object);
    const AActor* DriverOwner = Actor ? Actor : Object->GetTypedOuter<AActor>();
    UNetDriver* Driver = DriverOwner ? DriverOwner->GetNetDriver() : World->GetNetDriver();
    if (Actor)
    {
        Result.LocalRole = static_cast<int32>(Actor->GetLocalRole());
        Result.ActorAgeSeconds = Actor->GetGameTimeSinceCreation();
    }
    if (!Driver)
    {
        Result.Transport = TEXT("NoNetDriver");
        return Result;
    }
    Result.DriverPath = Driver->GetPathName();

#if UE_WITH_IRIS
    if (Driver->IsUsingIrisReplication())
    {
        Result.Transport = TEXT("Iris");
        UReplicationSystem* System = Driver->GetReplicationSystem();
        UObjectReplicationBridge* Bridge = System ? System->GetReplicationBridge() : nullptr;
        const UE::Net::FNetRefHandle Handle = Bridge ? Bridge->GetReplicatedRefHandle(Object) : UE::Net::FNetRefHandle();
        if (Handle.IsValid())
        {
            // GetId omits the process-local ReplicationSystemId. Identity is
            // comparable across peers, never used as an ordering/generation.
            Result.WireId = FString::Printf(TEXT("%llu"), static_cast<unsigned long long>(Handle.GetId()));
            Result.bValid = true;
        }
        return Result;
    }
#endif

    Result.Transport = TEXT("Legacy");
    const TSharedPtr<FNetGUIDCache>& Cache = Driver->GetNetGuidCache();
    const FNetworkGUID Guid = Cache.IsValid() ? Cache->GetNetGUID(Object) : FNetworkGUID();
    if (Guid.IsValid() && !Guid.IsDefault())
    {
        Result.WireId = Guid.ToString();
        Result.bValid = true;
    }
    return Result;
}
