"""Pure state/identity contracts; actual rendered PNG review remains separate."""
PHASES={'server':(), 'A':('fire_a','reload_a','switch_a','respawn_a'), 'B0':('empty_b',), 'B1':()}


def require(value,message):
    if not value:raise ValueError(message)


def validate(reports,run_id):
    require(set(reports)==set(PHASES),'Four native peers required')
    images=[]
    for peer,report in reports.items():
        require(report['status']=='passed' and report['peer']==peer and report['run_id']==run_id and
                report['native_gameplay_state_written'] is False and report['production_lifecycle_replayed'] is False and
                report['full_visual_acceptance'] is False and report['error'] is None,'Unsupported/failed visual evidence')
        require([r['phase'] for r in report['captures']]==list(PHASES[peer]),'Five actual visual phases required')
        require(type(report['widgets_created']) is int and report['widgets_created']==report['widgets_closed'] and
                report['widgets_created']>=4*int(peer!='server') and report['active_test_widgets']==0,'Visual widget/root leak or unexercised client')
        paths=[r['image'] for r in report['captures']];queue=report['screenshot_queue']
        require(queue['requested']==queue['issued']==paths and len(paths)==len(set(paths)) and
                queue['pending_count']==0 and queue['rendered_files_verified'] is False,'Visual shot queue incomplete')
        for row in report['captures']:
            weapon=row['native']
            expected=dict(magazine=str(weapon['magazine']),spare=format(weapon['spare'],','),visibility=0)
            require(row['profiles']==row['counter_profiles']==['BlueprintFallback','Python'] and
                    row['panels']==[expected,expected] and len(row['weapon_names'])==2 and
                    row['weapon_names'][0]==row['weapon_names'][1],'Original/Python visible pair differs')
            require(row['item']==weapon['item'] and row['definition']==weapon['definition'] and
                    row['controller'] and row['pawn'] and row['world'] and type(row['player_id']) is int,
                    'Visible widgets lost native player/item identity')
            require(len(row['test_owned_widget_paths'])==4 and len(set(row['test_owned_widget_paths']))==4 and
                    row['production_widget'] not in row['test_owned_widget_paths'],'Production HUD replaced/duplicated')
            threshold={'Pistol':2,'Rifle':4,'Shotgun':1}[row['style']]
            values=dict(Rounds_Max=float(weapon['maximum']),Rounds_Current=float(weapon['magazine']),
                        IsLowAmmo=float(weapon['magazine']<=threshold))
            require(row['counters']==[dict(bar=values,glow=values)]*2,'Visible material values differ from native ammo')
            images.append(dict(peer=peer,phase=row['phase'],path=row['image']))
    return dict(status='passed',visual_checkpoint_pairs=len(images),native_state_written=False,
                rendered_files_verified=False,full_visual_acceptance=False,images=images)
