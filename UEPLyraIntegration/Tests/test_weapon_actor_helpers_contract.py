"""Reject missing inherited branches and mismatched native helper readbacks."""
import unittest
from uep_lyra_weapons import weapon_actor_helpers_contract as policy


def report():
    data = dict(status="passed", error=None, native_mode="Standalone", fake_cases=[], stencil_cases=[], color_cases=[], audio_cases=[],
        actual_child_actor_recursion=True, production_classes_restored=True, test_actors_destroyed=True, all_original_pawn_health_unchanged=True)
    data.update({name:False for name in ("full_acceptance","network_acceptance","packaged_runtime","audio_playback_tested","real_firing_tested","health_properties_written","official_assets_modified","child_blueprints_modified")})
    for cls in policy.CLASSES:
        for profile in policy.PROFILES:
            for name, number, angle, wall in policy.FAKE_CASES:
                hits = max(number,0) if wall else 0
                data["fake_cases"].append(dict(name=name,profile=profile,**{"class":cls},number=number,angle=angle,wall_enabled=wall,
                    parent_dispatch_verified=True,positions=[[500.,0.,0.]]+[[990.,0.,0.]]*hits,normals=[[0.,0.,1.]]+[[-1.,0.,0.]]*hits,
                    surfaces=[0]*(1+hits),seed=[500.,0.,0.],wall_front_x=990.,start=[0.,0.,0.],delta=dict(traces=max(number,0),hits=hits)))
            for owner in policy.OWNERS:
                for team in policy.TEAMS:
                    value=0 if owner in ("player","bot") else max(0,min(255,team))
                    data["stencil_cases"].append(dict(profile=profile,**{"class":cls},owner=owner,team=team,parent_dispatch_verified=True,
                        child_components=1,values=[value]*3,depth_flags_unchanged=True))
            for valid, opt in ((False,True),(True,False),(True,True)):
                value=[.2,.4,.6,1.] if valid and opt else [.8,.8,.8,1.]
                data["color_cases"].append(dict(profile=profile,**{"class":cls},asset_valid=valid,opt_in=opt,parent_dispatch_verified=True,colors=[value,value],child_mesh_included=True))
            for existing in (False,True):
                data["audio_cases"].append(dict(profile=profile,**{"class":cls},existing=existing,parent_dispatch_verified=True,input_component_retained=existing,
                    output_is_null=not existing,delta=dict(audio_spawns=int(not existing),audio_triggers=int(existing))))
    return data


class TestWeaponActorHelpersContract(unittest.TestCase):
    def setUp(self): self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError): policy.validate(self.data)
    def test_native_matrix(self): self.assertEqual(policy.validate(self.data)["native_helper_cases"],132)
    def test_missing_class_disguised_as_duplicate(self): self.data["fake_cases"][-1]=self.data["fake_cases"][0];self.rejected()
    def test_missing_impact_seed(self): self.data["fake_cases"][2]["positions"][0]=[0.,0.,0.];self.rejected()
    def test_miss_appends_hits(self): self.data["fake_cases"][3]["positions"].append([990.,0.,0.]);self.rejected()
    def test_wrong_actual_wall(self): self.data["fake_cases"][2]["positions"][1]=[980.,0.,0.];self.rejected()
    def test_cone_points_outside_angle(self): self.data["fake_cases"][4]["positions"][1]=[990.,500.,0.];self.rejected()
    def test_local_bot_wrongly_treated_as_remote(self):
        row=next(r for r in self.data["stencil_cases"] if r["owner"]=="bot" and r["team"]==2);row["values"]=[2]*3;self.rejected()
    def test_child_primitive_omitted(self): self.data["stencil_cases"][0]["child_components"]=0;self.rejected()
    def test_stencil_enables_depth_rendering(self): self.data["stencil_cases"][0]["depth_flags_unchanged"]=False;self.rejected()
    def test_valid_team_color_never_applied(self): self.data["color_cases"][2]["colors"]=[[.8,.8,.8,1.]]*2;self.rejected()
    def test_child_material_omitted(self): self.data["color_cases"][2]["child_mesh_included"]=False;self.rejected()
    def test_existing_audio_replaced(self): self.data["audio_cases"][1]["input_component_retained"]=False;self.rejected()
    def test_null_spawn_claims_no_parent_dispatch(self): self.data["audio_cases"][0]["parent_dispatch_verified"]=False;self.rejected()
    def test_native_audio_playback_overclaim(self): self.data["audio_playback_tested"]=True;self.rejected()
    def test_health_changed(self): self.data["all_original_pawn_health_unchanged"]=False;self.rejected()
