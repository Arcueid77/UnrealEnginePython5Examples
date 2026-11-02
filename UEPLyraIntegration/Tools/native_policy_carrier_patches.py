"""World-owned Blueprint policy carrier for native-only owners, starting with Reset."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha
from native_lifecycle_patches import sources as lifecycle_sources


def sources():
    reset=next(r for r in lifecycle_sources() if r['relative'].endswith('LyraGameplayAbility_Reset.cpp'));before=reset['after'];after=before.replace('#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraGameplayAbility_Reset)','#include "UEPPolicy/UEPNativeGameplayPolicy.h"\n#include "UObject/StrongObjectPtr.h"\n#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraGameplayAbility_Reset)')
    after=after.replace('bool ULyraGameplayAbility_Reset::UEPUsesPythonResetPolicy_Implementation() const { return false; }','''bool ULyraGameplayAbility_Reset::UEPUsesPythonResetPolicy_Implementation() const
{
    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(GetWorld());
    return Host && Host->UEPUsesPythonPolicy(TEXT("Reset.Activate"));
}''').replace('TArray<FName> ULyraGameplayAbility_Reset::UEPResetActivationPlan_Implementation() const { return {}; }','''TArray<FName> ULyraGameplayAbility_Reset::UEPResetActivationPlan_Implementation() const
{
    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(GetWorld());
    if (!Host) { return {}; }
    TStrongObjectPtr<UUEPNativeResetPolicyContext> Context(NewObject<UUEPNativeResetPolicyContext>(Host));
    Context->Operation = TEXT("Reset.Activate");
    Context->bHasCharacter = GetLyraCharacterFromActorInfo() != nullptr;
    Host->UEPApplyPolicy(Context.Get());
    ensureMsgf(Context->bCompleted, TEXT("Python Reset policy did not complete"));
    return Context->bCompleted ? Context->Actions : TArray<FName>();
}''')
    rows=[dict(relative=reset['relative'],before=before,after=after,original_sha256=reset['original_sha256'])]
    for suffix in ('.h','.cpp'):
        p=REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters'/('UEPNativeGameplayPolicy'+suffix);rows.append(dict(relative='Source/LyraGame/UEPPolicy/'+p.name,before='',after=p.read_text(),original_sha256=None,source=str(p)))
    return rows


def patch_text():return ''.join(line if line.endswith('\n') else line+'\n' for r in sources() for line in difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'] if r['before'] else '/dev/null',tofile='b/'+r['relative']))


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve()
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned policy stage/fresh patch output required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP15-native-policy-carrier.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned policy carrier patch differs')
    rows=sources()
    for r in rows:
        p=stage/r['relative']
        if (p.read_text(encoding='utf-8-sig') if p.exists() else '') not in (r['before'],r['after']):raise ValueError('Unrelated native policy edit')
    output.mkdir(parents=True);records=[]
    for r in rows:
        p=stage/r['relative'];p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            backup=output/'PreviousSources'/r['relative'];backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
        p.write_text(r['after'],encoding='utf-8',newline='\n');records.append(dict(path=str(p),original=str(REFERENCE/r['relative']) if r['original_sha256'] else None,original_sha256=r['original_sha256'],patched_sha256=sha(p)))
    result=dict(status='patched_requires_native_build',sources=records,runtime_acceptance=False);(output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(apply(a.stage,a.output),indent=2))
