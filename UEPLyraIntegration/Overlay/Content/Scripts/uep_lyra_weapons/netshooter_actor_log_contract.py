"""Audit one exact original-template baseline ensure; reject every other error."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from .weapon_actor_helpers_contract import require


def validate_log(raw):
    pattern=r"(?ms)^[^\r\n]*UEP_NETSHOOTER_BASELINE_TEMPLATE_BEGIN[^\r\n]*\r?\n(?P<body>.*?)^[^\r\n]*UEP_NETSHOOTER_BASELINE_TEMPLATE_END[^\r\n]*"
    matches=list(re.finditer(pattern,raw));require(len(matches)==1,"one explicit original-template baseline window required")
    match=matches[0];body=match.group("body")
    error_lines=[line.split("LogOutputDevice: Error:",1)[1].strip() for line in body.splitlines() if "LogOutputDevice: Error:" in line]
    condition="Ensure condition failed: Component->GetArchetype() == Component->GetClass()->GetDefaultObject()"
    conditions=[line for line in error_lines if line.startswith(condition)]
    messages=[line for line in error_lines if line.startswith("Replicated component ")]
    require(len(conditions)==1 and "ActorReplication.cpp" in conditions[0] and len(messages)==1 and "::NODE_AddStaticMeshComponent-0 was added dynamically outside the construction script." in messages[0],"baseline ensure differs from the original template defect")
    allowed=[line for line in error_lines if not line or line=="=== Handled ensure: ===" or line=="Stack:" or line.startswith("[Callstack]") or line in conditions or line in messages]
    require(len(allowed)==len(error_lines) and "AActor::AddComponentForReplication" in body and "py_ue_call_mixin_original" in body,"baseline window contains an unrelated error or not the original BP path")
    remainder=re.sub(r"(?m)^.*LogOutputDevice: Error:[^\r\n]*(?:\r?\n|$)","",body)
    require(not re.search(r"(?im)Log\w+:\s*Error:|Fatal error:|Assertion failed|Unhandled Exception|Ensure condition failed",remainder),"unexpected error inside source baseline window")
    clean=raw[:match.start("body")]+remainder+raw[match.end("body"):]
    require(not re.search(r"(?im)Log\w+:\s*Error:|Fatal error:|Assertion failed|Unhandled Exception|Ensure condition failed",clean),"unexpected error outside audited source baseline")
    return dict(status="passed",original_blueprint_dynamic_replication_template_ensure=1,raw_log_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        source_baseline_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),native_component_network_replication_accepted=False),clean


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--log",required=True);parser.add_argument("--clean-log",required=True);parser.add_argument("--result",required=True);args=parser.parse_args()
    report,clean=validate_log(Path(args.log).read_text(encoding="utf-8-sig"));Path(args.clean_log).write_text(clean,encoding="utf-8");Path(args.result).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report))
