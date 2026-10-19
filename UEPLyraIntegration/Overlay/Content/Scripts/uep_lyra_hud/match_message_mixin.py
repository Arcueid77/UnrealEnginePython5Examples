"""Match result/style policy; localized literals and UMG primitives stay native."""
import unreal_engine as ue
from unreal_engine.structs import SlateBrush

CLASS = "/ShooterCore/GameplayCues/W_MatchDecided_Message.W_MatchDecided_Message_C"
AFTER_TEXT = "UEPMatchAfterLiteralText"
TEXT_ENTRIES = ("UEPMatchDrawLiteral", "UEPMatchVictoryLiteral", "UEPMatchDefeatLiteral")
IMAGES = (("TextShadow", "TextBorder_Red", "TextBorder_Blue"),
    ("GlowStripe", "Stripe_Red", "Stripe_Blue"), ("LogoGlow", "RedTeam_Glow", "BlueTeam_Glow"),
    ("Logo", "RedTeam", "BlueTeam"), ("SoftGlow", "SoftGlow_Red", "SoftGlow_Blue"))
ROOT = "/Game/UI/Menu/Art/MI_UI_Teams_"


def lib(name): return ue.find_class(name).get_cdo()


def evidence(widget):
    if not hasattr(widget, "_uep_match_message"):
        widget._uep_match_message = dict(python_materials=0, fallback_materials=0, diagnostic_materials=0,
            python_construct=0, fallback_construct=0, literal_calls=0, fallback_literals=0,
            font_writes=0, brush_writes=0, animations=0, stingers=0, sounds=0)
    return widget._uep_match_message


def material(index, red, blue):
    if index == 0: return None
    name = ROOT+(red if index == 1 else blue)
    return ue.load_object(ue.find_class("MaterialInterface"), name+"."+name.rsplit("/",1)[-1])


def materials(widget):
    counts = evidence(widget); counts["python_materials"] += 1; team = int(widget.get_property("Team"))
    if team not in (0,1,2):
        counts["diagnostic_materials"] += 1; return widget.call_mixin_original("SetTeamMaterials")
    text = widget.get_property("VictoryMessage"); old = text.get_property("Font")
    font = lib("SlateFontInfoBlueprintLibrary").call_function("MakeSlateFontInfo", FontObject=old.FontObject,
        FontMaterial=material(team,"Text_Red","Text_Blue"), OutlineSettings=old.OutlineSettings,
        TypefaceFontName=old.TypefaceFontName, Size=old.Size, LetterSpacing=old.LetterSpacing,
        SkewAmount=0., bForceMonospaced=False, bMaterialIsStencil=False, MonospacedWidth=1.)
    text.call_function("SetFont",font); counts["font_writes"] += 1
    for field,red,blue in IMAGES:
        image = widget.get_property(field); brush = image.get_property("Brush")
        image.call_function("SetBrush",SlateBrush(TintColor=brush.TintColor, DrawAs=brush.DrawAs, Tiling=brush.Tiling,
            Mirroring=brush.Mirroring, ImageSize=brush.ImageSize, Margin=brush.Margin,
            ResourceObject=material(team,red,blue), OutlineSettings=brush.OutlineSettings)); counts["brush_writes"] += 1


def team(widget):
    subsystem = lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",widget,ue.find_class("LyraTeamSubsystem"))
    found,index = subsystem.call_function("FindTeamFromActor",widget.call_function("GetOwningPlayer"))
    return bool(found),int(index)


def construct(widget, params):
    counts = evidence(widget); counts["python_construct"] += 1
    _,index = team(widget); widget.set_property("Team",index); widget.call_function("SetTeamMaterials")
    # Source reads AbilityLevel; it does not round or otherwise use RawMagnitude.
    ability = int(params.AbilityLevel); result = 0 if ability == 0 else 1 if index == ability else 2
    widget.call_function(TEXT_ENTRIES[result])
    widget.call_function("PlayAnimationForward",widget.get_property("DefeatIntro" if result == 2 else "VictoryIntro"),1.,False); counts["animations"] += 1
    if result != 2:
        ue.load_class("/Game/Audio/Blueprints/GeneralAudioFunctions.GeneralAudioFunctions_C").get_cdo().call_function("FireStinger",True,widget); counts["stingers"] += 1
    sound = "/Game/Audio/Sounds/SFX/Lyra_EndOfRound-"+("Defeat" if result == 2 else "Victory")+"_01"
    lib("GameplayStatics").call_function("PlaySound2D",WorldContextObject=widget,Sound=ue.load_object(ue.find_class("SoundBase"),sound+"."+sound.rsplit("/",1)[-1]),
        VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,OwningActor=None,bIsUISound=True); counts["sounds"] += 1


class LyraMatchMessagePythonProfile:
    def SetTeamMaterials(self): return materials(self)
    def ConstructFromCueParams(self, Params): return construct(self,Params)
    def AfterText(self, Kind): evidence(self)["literal_calls"] += 1; return False
    AfterText.override = AFTER_TEXT


class LyraMatchMessageBlueprintFallbackProfile:
    def SetTeamMaterials(self): evidence(self)["fallback_materials"] += 1; return self.call_mixin_original("SetTeamMaterials")
    def ConstructFromCueParams(self, Params): evidence(self)["fallback_construct"] += 1; return self.call_mixin_original("ConstructFromCueParams",Params)
    def AfterText(self, Kind): evidence(self)["fallback_literals"] += 1; return True
    AfterText.override = AFTER_TEXT
