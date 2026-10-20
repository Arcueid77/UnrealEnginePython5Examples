"""Compare complete T3D payloads while allowing reordered sibling subobjects."""
def canonical_cdo(text):
    roots=[];stack=[]
    for raw in text.splitlines():
        line=raw.strip()
        if not line:continue
        if line.startswith('Begin Object '):
            node=[line,[],[]]
            (stack[-1][2] if stack else roots).append(node);stack.append(node)
        elif line=='End Object':
            if not stack:raise ValueError('unbalanced CDO object end')
            stack.pop()
        else:
            if not stack:raise ValueError('CDO payload outside an object')
            stack[-1][1].append(line)
    if stack or len(roots)!=1:raise ValueError('incomplete CDO object tree')
    def freeze(node):return (node[0],tuple(node[1]),tuple(sorted(freeze(child) for child in node[2])))
    return freeze(roots[0])
