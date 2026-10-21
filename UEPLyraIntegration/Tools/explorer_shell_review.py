"""Pure structural classification; preserve original candidate paths and parents."""
ALLOWED={'K2Node_FunctionEntry','K2Node_Event','K2Node_CallParentFunction','EdGraphNode_Comment'}
FORWARDS={'UserConstructionScript','ReceiveBeginPlay','ReceiveTick','ReceiveActorBeginOverlap'}
def classify_actor(graphs):
    nodes=[n for values in graphs.values() for n in values]
    if any(n['cls'] not in ALLOWED for n in nodes):raise RuntimeError('independent actor business still requires migration')
    names=[]
    for values in graphs.values():
        by_name={n['node']:n for n in values}
        for n in values:
            if n['cls']=='K2Node_CallParentFunction':
                name=n['function']['name']
                if name not in FORWARDS:raise RuntimeError('unexpected parent business forwarding')
                execute=next(p for p in n['pins'] if p['name']=='execute')
                if len(execute['links'])!=1:raise RuntimeError('parent forwarder execution source differs')
                source=by_name[execute['links'][0].rsplit('.',1)[0]]
                if source['cls'] not in ('K2Node_FunctionEntry','K2Node_Event'):raise RuntimeError('forwarder contains independent execution')
                for p in n['pins']:
                    if p['name'] in ('DeltaSeconds','OtherActor') and p['links']!=[source['node']+'.'+p['name']]:raise RuntimeError('parent event argument forwarding changed')
                names.append(name)
    return dict(independent_business_nodes=0,retained_parent_forwarders=sorted(names),empty_or_forwarding_only=True,inherited_parent_business_migrated=False)
def classify_prompt(graphs):
    nodes=graphs['EventGraph'];by_name={n['node']:n for n in nodes}
    if len(nodes)!=7 or {n['cls'] for n in nodes}!={'K2Node_Event','K2Node_CallFunction','K2Node_DynamicCast'}:raise RuntimeError('interaction prompt source footprint differs')
    for name in ('K2Node_Event_0','K2Node_Event_1','K2Node_Event_2'):
        if any(p['category']=='exec' and p['links'] for p in by_name[name]['pins']):raise RuntimeError('prompt lifecycle event has independent business')
    cast=by_name['K2Node_DynamicCast_0']
    if any(p['direction']==1 and p['category']=='exec' and p['links'] for p in cast['pins']):raise RuntimeError('prompt cast now executes business')
    getter=by_name['K2Node_CallFunction_3']
    if getter['function']['name']!='GetComponentByClass' or any(p['direction']==1 and p['links'] for p in getter['pins']):raise RuntimeError('prompt component lookup has an observable consumer')
    if by_name['K2Node_CallFunction_1']['function']['name']!='GetDataObject':raise RuntimeError('prompt indicator data source differs')
    return dict(independent_business_nodes=0,empty_lifecycle_events=['PreConstruct','Construct','Tick'],unused_bind_result_and_unconnected_cast_branches=True,retained_native_bind_indicator=True)
