"""Expose selection/grant policy while retaining RPC, equipment and fast-array code."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha

QUICK='Source/LyraGame/Equipment/LyraQuickBarComponent'
INVENTORY='Source/LyraGame/Inventory/LyraInventoryManagerComponent'
PICKUP='Source/LyraGame/Inventory/IPickupable.cpp'


def function_range(text,signature):
    start=text.index(signature);opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return start,opening,end


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]};rows=[]
    for relative in (QUICK+'.h',QUICK+'.cpp',INVENTORY+'.h',INVENTORY+'.cpp',PICKUP):
        original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original inventory source differs from census')
        before=original.read_text(encoding='utf-8-sig');after=before
        if relative==QUICK+'.h':
            for name in ('CycleActiveSlotForward','CycleActiveSlotBackward'):
                old='UFUNCTION(BlueprintCallable, Category="Lyra")\n\tvoid '+name+'();'
                if after.count(old)!=1:raise ValueError('Native quickbar cycle signature changed')
                after=after.replace(old,old.replace('BlueprintCallable,','BlueprintCallable, BlueprintNativeEvent,'))
            old='UFUNCTION(BlueprintCallable, BlueprintPure=false)\n\tint32 GetNextFreeItemSlot() const;'
            if after.count(old)!=1:raise ValueError('Native quickbar free-slot signature changed')
            after=after.replace(old,old.replace('BlueprintCallable,','BlueprintCallable, BlueprintNativeEvent,'))
        elif relative==QUICK+'.cpp':
            for name in ('CycleActiveSlotForward','CycleActiveSlotBackward','GetNextFreeItemSlot'):
                old='ULyraQuickBarComponent::'+name+'('
                if after.count(old)!=1:raise ValueError('Native quickbar definition changed')
                after=after.replace(old,'ULyraQuickBarComponent::'+name+'_Implementation(')
        elif relative==INVENTORY+'.h':
            after=after.replace('#include "Net/Serialization/FastArraySerializer.h"','#include "Net/Serialization/FastArraySerializer.h"\n#include "Inventory/IPickupable.h"')
            after=after.replace('UCLASS(MinimalAPI, BlueprintType)','UCLASS(MinimalAPI, BlueprintType, Blueprintable)')
            anchor='\tUFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category=Inventory)\n\tUE_API bool CanAddItemDefinition'
            extra='''	// Native pickup interface resolution stays in PickupableStatics.
	UFUNCTION(BlueprintNativeEvent, Category="UEP|NativeGameplay")
	UE_API void UEPGrantPickup(const FInventoryPickup& PickupInventory);

'''
            if after.count(anchor)!=1:raise ValueError('Native inventory declaration anchor changed')
            after=after.replace(anchor,extra+anchor)
        elif relative==INVENTORY+'.cpp':
            source=(REFERENCE/PICKUP).read_text(encoding='utf-8-sig')
            start=source.index('\t\tfor (const FPickupTemplate& Template : PickupInventory.Templates)')
            end=source.index('\n\t}\n}',start)
            body='\n'.join(line[1:] if line.startswith('\t') else line for line in source[start:end].splitlines())
            after+='\nvoid ULyraInventoryManagerComponent::UEPGrantPickup_Implementation(const FInventoryPickup& PickupInventory)\n{\n'+body.replace('InventoryComponent->','')+'\n}\n'
        else:
            start=after.index('\t\tfor (const FPickupTemplate& Template : PickupInventory.Templates)');end=after.index('\n\t}\n}',start)
            after=after[:start]+'\t\tInventoryComponent->UEPGrantPickup(PickupInventory);'+after[end:]
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh inventory patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native migration stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP05-inventory-rules.patch'
    if artifact.read_text(encoding='utf-8')!=patch_text():raise ValueError('Versioned inventory patch differs')
    rows=sources()
    for row in rows:
        if (stage/row['relative']).read_text(encoding='utf-8-sig') not in (row['before'],row['after']):raise ValueError('Unrelated inventory edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    report=dict(schema_version=1,status='patched_requires_native_build',batch='CPP05',new_policy_events=4,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP05-inventory-rules.patch'
        if target.exists():raise ValueError('Inventory patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
