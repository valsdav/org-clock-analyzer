from __future__ import annotations

from orgparse import load, loads
import sys
from pprint import pprint
from dataclasses import dataclass,field

@dataclass
class OrgNode:
    name: str
    level : int
    parent: OrgNode
    children : list = field(default_factory=lambda: [])
    tags: list = field(default_factory=lambda: [])
    localTime: int = 0
    totalTime: int = 0
    


def explore(parent, node):
    localT = 0.
    if hasattr(node, "clock"):
        for cl in node.clock:
            localT += (cl.end - cl.start).seconds // 60
    
    orgnode = OrgNode(name=node.heading,
                      level=node.level,
                      localTime=localT,
                      totalTime=localT,
                      tags=node.tags,
                      parent=parent)
    parent.children.append(orgnode)
    for children in node.children:
        explore(orgnode, children)

#Now traverse to get the total time
def add_time(node):
    for ch in node.children:
        add_time(ch)
    if node.parent:
        node.parent.totalTime += node.totalTime


def get_json_time(node):
    if len(node.children):
        obj = {
            "name": node.name,
            "children": [{
                    "name":"self",
                    "value": node.localTime}
            ]
        }
        for ch in node.children:
            obj["children"].append(get_json_time(ch))
        return obj
    else:
        return {
            "name": node.name,
            "value": node.totalTime
        }



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--files",  nargs="+", type=str , help="input files")
    args = parser.parse_args()

    clock_root  = OrgNode(name="root", parent=None, level=-1 ) 
    
    for f in args.files:
        node = load(f)
        explore(clock_root, node)
        clock_root.children[-1].name = f.split("/")[-1][:-4]
        
        
    ## Accumulate the time
    add_time(clock_root)
    output = get_json_time(clock_root)

    
    
    
