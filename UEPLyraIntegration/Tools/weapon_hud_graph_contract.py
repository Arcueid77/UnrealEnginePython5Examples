"""Compare original audited BP pins/links/member references with persisted widgets."""
import argparse
import json
from pathlib import Path


def compare(original,current):
    checks={}
    for label,asset in current['assets'].items():
        source=next(a for a in original['blueprints'] if a['path']==asset['package']);lookup={(n['id'],p['id']):n['name']+'.'+p['name'] for g in source['graphs'] for n in g['nodes'] for p in n['pins']};diffs=[]
        expected_graphs={g['name'] for g in source['graphs']}
        if set(asset['graphs'])!=expected_graphs|{'GetPythonMixinSet','GetPythonMixinProfile'}:diffs.append(dict(graph_names=True))
        for graph in source['graphs']:
            actual={n['node']:n for n in asset['graphs'].get(graph['name'],[])};expected={n['name']:n for n in graph['nodes']}
            if set(actual)!=set(expected):diffs.append(dict(graph=graph['name'],node_names=True));continue
            for name,n in expected.items():
                a=actual[name]
                if n['class']!=a['cls']:diffs.append(dict(node=name,cls=True))
                for old_key,new_key in (('FunctionReference','function'),('VariableReference','variable'),('EventReference','event'),('DelegateReference','delegate')):
                    ref=n['properties'].get(old_key)
                    if ref and (ref.get('MemberName'),ref.get('MemberParent'))!=(a.get(new_key,{}).get('name'),a.get(new_key,{}).get('owner')):diffs.append(dict(node=name,member_reference=old_key))
                ap={p['name']:p for p in a['pins']}
                if set(ap)!={p['name'] for p in n['pins']}:diffs.append(dict(node=name,pin_names=True));continue
                for p in n['pins']:
                    q=ap[p['name']];left=(p['direction'],p['category'],p['sub_category_object'],p['default_value'],p['default_object'],sorted(lookup[(l['node'],l['pin'])] for l in p['links']));right=(q['direction'],q['category'],q['object'],q['default'],q['default_object'],sorted(q['links']))
                    if left!=right:diffs.append(dict(node=name,pin=p['name'],expected=left,current=right))
        interfaces=sum(len(asset['graphs'].get(g,[])) for g in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interfaces!=5:diffs.append(dict(interface_footprint=True))
        checks[label]=dict(original_nodes=sum(len(g['nodes']) for g in source['graphs']),interface_nodes=interfaces,diffs=diffs)
    return dict(status='passed' if len(checks)==4 and all(not r['diffs'] for r in checks.values()) else 'failed',scope='original node names/classes/member references,pin names/directions/categories/object types/defaults and resolved links;only two interface graphs added',assets=checks)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',required=True);p.add_argument('--current',required=True);p.add_argument('--result',required=True);a=p.parse_args();report=compare(json.loads(Path(a.original).read_text(encoding='utf-8-sig')),json.loads(Path(a.current).read_text(encoding='utf-8-sig')));Path(a.result).write_text(json.dumps(report,indent=2),encoding='utf-8');print(report['status']);raise SystemExit(report['status']!='passed')
