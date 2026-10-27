"""Explicit test-only paired widgets over the unchanged real weapon network producer.

Left column: original BlueprintFallback. Right column: Python. Additional widgets
only read the same local native item. They do not replace the production HUD,
replay its lifecycle or write ammo/inventory/ability state.
"""
import copy
from pathlib import Path
import sys
import types

if '-UEPLyraBatch1AVisual' not in sys.argv:
    raise RuntimeError('Batch1A visual module requires its explicit test flag')

import unreal_engine as ue
from unreal_engine.structs import Geometry, Vector2D
import ue_site  # Normal opt-in startup creates the unchanged network producer once.
from uep_lyra_weapon_network import runtime, PANEL, panel_state
from uep_lyra_hud import weapon_observer
from uep_lyra_network_io import atomic_write
from uep_lyra_network_protocol import require
from uep_lyra_network_screenshots import FrameScreenshotQueue


PHASES = {'A': ('fire_a','reload_a','switch_a','respawn_a'), 'B0': ('empty_b',), 'B1': (), 'server': ()}


def material_state(image):
    material=image.call_function('GetDynamicMaterial')
    return {name:float(material.call_function('K2_GetScalarParameterValue',name))
            for name in ('Rounds_Max','Rounds_Current','IsLowAmmo')}


def counter_state(widget):
    return {'bar':material_state(widget.AmmoCounter_Bar),'glow':material_state(widget.AmmoCounter_Glow)}


class VisualSession:
    def __init__(self, probe):
        self.probe=probe;self.world=None;self.panels=[];self.counters=[];self.style=None
        self.excluded_panels=set();self.current=None;self.captures=[];self.created=0;self.closed=0
        self.queue=FrameScreenshotQueue(self.emit)

    def close_widgets(self, widgets):
        for widget in widgets:
            if weapon_observer.valid(widget):
                widget.RemoveFromParent();widget.remove_from_root();self.closed+=1
        widgets.clear()

    def close(self):
        self.close_widgets(self.counters);self.close_widgets(self.panels)
        self.excluded_panels.clear();self.world=None;self.style=None;self.current=None

    def pair(self, controller, path, y, *, panel=False):
        cls=ue.load_class(path);ue.register_declared_mixin(cls);widgets=[]
        for column,profile in enumerate(('BlueprintFallback','Python')):
            widget=controller.create_widget(cls);widget.add_to_root();self.created+=1
            ue.set_mixin_profile(widget,profile)
            if panel and profile == 'Python':self.excluded_panels.add(widget.get_path_name())
            widget.AddToViewport(300)
            widget.SetPositionInViewport(Vector2D(X=850.0+column*400.0,Y=float(y)),False)
            widget.SetDesiredSizeInViewport(Vector2D(X=500.0,Y=100.0))
            widgets.append(widget)
        return widgets

    def actual_hud(self, controller):
        matches=[]
        for path in weapon_observer.snapshot()['active_widgets']:
            widget=ue.find_object(path)
            if (path not in self.excluded_panels and weapon_observer.valid(widget) and
                widget.get_class().get_name() == 'W_WeaponAmmoAndName_C' and
                widget.call_function('GetOwningPlayer') == controller):matches.append(widget)
        require(len(matches)<=1,'Actual production panel duplication (test panels excluded by exact identity)')
        return matches[0] if matches else None

    def observe(self):
        probe=self.probe
        if probe.current_hud is None or probe.player is None:return
        controller=ue.find_object(probe.player['controller_path'])
        if self.world != probe.player['world_token']:
            self.close();self.world=probe.player['world_token']
            self.panels=self.pair(controller,PANEL,500,panel=True)
        weapon=probe.current_weapon;definition=weapon['definition'].lower()
        style=next((name for name in ('Pistol','Rifle','Shotgun') if name.lower() in definition),None)
        require(style is not None,'Unreviewed weapon counter style')
        if style != self.style:
            self.close_widgets(self.counters)
            path='/ShooterCore/Weapons/'+style+'/W_AmmoCounter_'+style+'.W_AmmoCounter_'+style+'_C'
            self.counters=self.pair(controller,path,660);self.style=style
        item=ue.find_object(weapon['item'])
        for widget in self.counters:
            if widget.InventoryInstance != item:
                widget.InventoryInstance=item;widget.call_function('OnWeaponInitialized')
        for widget in self.panels+self.counters:widget.call_function('Tick',Geometry(),0.016)
        weapon_observer.refresh()
        panels=[panel_state(w) for w in self.panels];counters=[counter_state(w) for w in self.counters]
        names=[str(w.WeaponNameWidget.call_function('GetText')) for w in self.panels]
        require(names[0] == names[1],'Visible original/Python weapon names differ')
        expected={'magazine':str(weapon['magazine']),'spare':format(weapon['spare'],','),'visibility':0}
        require(panels[0] == panels[1] == expected,'Visible panel pair differs from native item')
        require(counters[0] == counters[1],'Visible counter BP/Python material mismatch')
        threshold={'Pistol':2,'Rifle':4,'Shotgun':1}[style]
        expected_counter={'Rounds_Max':float(weapon['maximum']),'Rounds_Current':float(weapon['magazine']),
                          'IsLowAmmo':float(weapon['magazine']<=threshold)}
        require(all(value == expected_counter for value in counters[0].values()),'Counter native values differ')
        self.current=dict(controller=controller.get_path_name(),world=probe.player['world_token'],
            pawn=probe.player['pawn_path'],player_id=probe.player['player_id'],item=weapon['item'],definition=weapon['definition'],style=style,
            native=copy.deepcopy(weapon),panels=panels,weapon_names=names,counters=counters,
            profiles=[ue.get_mixin_profile(w) for w in self.panels],
            counter_profiles=[ue.get_mixin_profile(w) for w in self.counters],
            production_widget=probe.current_hud['widget'],test_owned_widget_paths=[w.get_path_name() for w in self.panels+self.counters])

    def capture(self, phase):
        require(self.current is not None,'Visual phase has no converged paired widgets')
        path=str(self.probe.root/('batch1a-'+self.probe.peer+'-'+phase+'.png'))
        self.queue.request(path,self.probe.world,ue.find_object(self.probe.player['controller_path']))
        self.captures.append(dict(phase=phase,image=path,**copy.deepcopy(self.current)))

    def emit(self, path, world, controller):
        require(weapon_observer.valid(world) and weapon_observer.valid(controller),'Visual image crossed native world teardown')
        ue.find_class('KismetSystemLibrary').get_cdo().call_function('ExecuteConsoleCommand',world,
            'Shot SHOWUI -nosuffix filename="'+path+'"',controller)

    def flush(self, error):
        require(self.queue.snapshot()['pending_count']==0,'Pending visual screenshot at teardown')
        atomic_write(self.probe.root/('batch1a-'+self.probe.peer+'.json'),dict(schema_version=1,
            status='failed' if error else 'passed',peer=self.probe.peer,run_id=self.probe.run_id,
            scope='test-owned original-BP-left Python-right presenters over real native input',
            native_gameplay_state_written=False,production_lifecycle_replayed=False,full_visual_acceptance=False,
            captures=self.captures,screenshot_queue=self.queue.snapshot(),
            widgets_created=self.created,widgets_closed=self.closed,active_test_widgets=len(self.panels)+len(self.counters),error=error))


session=VisualSession(runtime)
original_observe=runtime._observe_client;original_client_tick=runtime._client_tick;original_finish=runtime._finish


def observe(self):
    original_observe();session.observe()


def client_tick(self):
    previous=self.last_phase;original_client_tick()
    if self.last_phase != previous and self.history:
        phase=self.history[-1]['phase']
        if phase in PHASES[self.peer]:session.capture(phase)


def finish(self,error=None):
    session.close();session.flush(error);original_finish(error)


runtime._actual_hud=types.MethodType(lambda self,controller:session.actual_hud(controller),runtime)
runtime._observe_client=types.MethodType(observe,runtime)
runtime._client_tick=types.MethodType(client_tick,runtime)
runtime._finish=types.MethodType(finish,runtime)


def visual_frame(delta):
    session.queue.drain_one()
    return not runtime.finished


visual_ticker=ue.add_ticker(visual_frame)
ue.log('UEP_BATCH1A_VISUAL_INSTALLED '+runtime.peer)
