"""Expose spawner policy while native timer handles/replication retain ownership."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha

BASE='Source/LyraGame/Weapons/LyraWeaponSpawner'


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]};rows=[]
    for relative in (BASE+'.h',BASE+'.cpp'):
        original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original spawner differs from census')
        before=original.read_text(encoding='utf-8-sig');after=before
        if relative.endswith('.h'):
            after=after.replace('UFUNCTION(BlueprintCallable, Category = "Lyra|WeaponPickup")\n\tUE_API void ResetCoolDown();','UFUNCTION(BlueprintCallable, BlueprintNativeEvent, Category = "Lyra|WeaponPickup")\n\tUE_API void ResetCoolDown();')
            after=after.replace('UFUNCTION()\n\tUE_API void OnCoolDownTimerComplete();','UFUNCTION(BlueprintNativeEvent)\n\tUE_API void OnCoolDownTimerComplete();')
            for method in ('StartCoolDown','SetWeaponPickupVisibility'):
                needle='\tUE_API void '+method+'(';pos=after.index(needle);after=after[:pos]+'\tUFUNCTION(BlueprintCallable, Category = "Lyra|WeaponPickup")\n'+after[pos:]
            anchor='\tUFUNCTION(BlueprintNativeEvent)\n\tUE_API void OnCoolDownTimerComplete();'
            after=after.replace(anchor,anchor+'\n\n\t// Narrow timer operations; the handles never leave native ownership.\n\tUFUNCTION(BlueprintCallable)\n\tUE_API void UEPClearSpawnerCooldown();\n\n\tUFUNCTION(BlueprintCallable)\n\tUE_API void UEPScheduleSpawnerOverlapCheck();')
        else:
            after=after.replace('ALyraWeaponSpawner::ResetCoolDown()','ALyraWeaponSpawner::ResetCoolDown_Implementation()').replace('ALyraWeaponSpawner::OnCoolDownTimerComplete()','ALyraWeaponSpawner::OnCoolDownTimerComplete_Implementation()')
            after+='\nvoid ALyraWeaponSpawner::UEPClearSpawnerCooldown()\n{\n\tif (UWorld* World = GetWorld())\n\t{\n\t\tWorld->GetTimerManager().ClearTimer(CoolDownTimerHandle);\n\t}\n}\n\nvoid ALyraWeaponSpawner::UEPScheduleSpawnerOverlapCheck()\n{\n\tif (UWorld* World = GetWorld())\n\t{\n\t\tWorld->GetTimerManager().SetTimer(CheckOverlapsDelayTimerHandle, this, &ALyraWeaponSpawner::CheckForExistingOverlaps, CheckExistingOverlapDelay);\n\t}\n}\n'
        if after==before:raise ValueError('Spawner policy patch did not apply')
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh spawner patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP06-spawner-rules.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned spawner patch differs')
    rows=sources()
    for row in rows:
        if (stage/row['relative']).read_text(encoding='utf-8-sig') not in (row['before'],row['after']):raise ValueError('Unrelated spawner edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    result=dict(schema_version=1,status='patched_requires_native_build',batch='CPP06',policy_events=3,new_policy_events=2,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP06-spawner-rules.patch'
        if target.exists():raise ValueError('Spawner patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
