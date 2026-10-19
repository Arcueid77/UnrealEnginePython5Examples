"""Actual offline firing components and untouched authored/dynamic preset setup."""
import argparse
import json
from pathlib import Path
from .weapon_audio_cold_contract import validate as validate_cold
from .weapon_actor_helpers_contract import require


def validate(report):
    validate_cold(report)
    for field in ("preset_initialized_by_probe","preset_settings_written_by_probe","fixture_taps_added","audio_components_created_by_probe","physical_audio_output_tested","waveform_output_accepted"):
        require(report[field] is False,"offline effect initialization was forced or overclaimed: "+field)
    require(len(report["effect_shots"])==2,"actual offline firing observations missing")
    for row in report["effect_shots"]:
        after=row["preset_after"];require(after["resident"] and len(after["authored_taps"])==8,"authored preset not observed")
        require(after["dynamic_tap_ids"]==[tap["TapId"] for tap in after["authored_taps"]],"actual native effect did not initialize authored Taps")
        require(len(after["dynamic_taps"])==8,"native dynamic Tap state missing")
        require(row["weapon_components"] and any(c["playing"] for c in row["weapon_components"]),"actual native weapon audio component never played")
        require(all(report["selected_weapon"] in c["sound"].lower() for c in row["weapon_components"]),"observed audio component is not the selected weapon")
        if report["selected_weapon"]=="rifle":
            events=row["trigger_events"];require(len(events)==1 and events[0]["native_fire_trigger_delta"]==1,"cached Rifle component did not receive the actual native Fire trigger")
            require(any(c["path"]==events[0]["component"] and c["playing"] for c in row["weapon_components"]),"observed Rifle component does not match the triggered cache")
    require(report["authored_settings_unchanged"],"authored audio settings changed during runtime probe")
    return dict(status="passed",weapon=report["selected_weapon"],actual_input_shots=2,actual_native_initialized_taps=8,
        actual_weapon_components=sum(len(row["weapon_components"]) for row in report["effect_shots"]),physical_audio_output_tested=False,waveform_output_accepted=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
