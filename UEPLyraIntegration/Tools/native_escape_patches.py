"""Escape request policy seam; CommonUI binding and streamed loading stay native."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha

BASE='Source/LyraGame/UI/LyraHUDLayout'


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]};rows=[]
    for relative in (BASE+'.h',BASE+'.cpp'):
        original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original HUD source differs from census')
        before=original.read_text(encoding='utf-8-sig');after=before
        if relative.endswith('.h'):
            after=after.replace('\tvoid HandleEscapeAction();','''\tUFUNCTION(BlueprintNativeEvent)
\tvoid HandleEscapeAction();

\tUFUNCTION(BlueprintCallable)
\tFString UEPGetEscapeMenuPath() const;

\tUFUNCTION(BlueprintCallable)
\tvoid UEPPushEscapeMenu(TSoftClassPtr<UCommonActivatableWidget> MenuClass);''')
            after=after.replace('\tFString UEPGetEscapeMenuPath() const;','\tFString UEPGetEscapeMenuPath() const;\n\n\tUFUNCTION(BlueprintPure)\n\tint32 UEPGetCurrentUIInputMode() const;')
        else:
            after=after.replace('#include "CommonUIExtensions.h"','#include "CommonUIExtensions.h"\n#include "Engine/LocalPlayer.h"\n#include "Input/CommonUIActionRouterBase.h"')
            after=after.replace('ULyraHUDLayout::HandleEscapeAction()','ULyraHUDLayout::HandleEscapeAction_Implementation()')
            after+='''
FString ULyraHUDLayout::UEPGetEscapeMenuPath() const
{
\treturn ensure(!EscapeMenuClass.IsNull()) ? EscapeMenuClass.ToSoftObjectPath().ToString() : FString();
}

void ULyraHUDLayout::UEPPushEscapeMenu(TSoftClassPtr<UCommonActivatableWidget> MenuClass)
{
\tUCommonUIExtensions::PushStreamedContentToLayer_ForPlayer(GetOwningLocalPlayer(), TAG_UI_LAYER_MENU, MenuClass);
}

int32 ULyraHUDLayout::UEPGetCurrentUIInputMode() const
{
\tconst ULocalPlayer* Player = GetOwningLocalPlayer();
\tconst UCommonUIActionRouterBase* Router = Player ? Player->GetSubsystem<UCommonUIActionRouterBase>() : nullptr;
\treturn Router ? static_cast<int32>(Router->GetActiveInputMode()) : -1;
}
'''
        if after==before:raise ValueError('Escape policy patch did not apply')
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():
    # difflib leaves an EOF line unterminated; emit Git's marker so the
    # removed final brace and added line cannot merge into a corrupt hunk.
    result=[]
    for row in sources():
        for line in difflib.unified_diff(row['before'].splitlines(True),row['after'].splitlines(True),fromfile='a/'+row['relative'],tofile='b/'+row['relative']):
            result.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    return ''.join(result)


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh Escape patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP09-escape-rules.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned Escape patch differs')
    rows=sources()
    for row in rows:
        if (stage/row['relative']).read_text(encoding='utf-8-sig') not in (row['before'],row['after']):raise ValueError('Unrelated HUD edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    result=dict(schema_version=1,status='patched_requires_native_build',batch='CPP09',policy_events=1,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP09-escape-rules.patch'
        if target.exists():raise ValueError('Escape patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
