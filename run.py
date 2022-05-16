from __future__ import annotations

from orgparse import load, loads
import argparse
import sys
from pprint import pprint
from dataclasses import dataclass,field

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--files",  nargs="+", type=str , help="input files")
args = parser.parse_args()

@dataclass
class OrgNode:
    name: str
    level : int
    parent: OrgNode
    children : list = field(default_factory=lambda: [])
    tags: list = field(default_factory=lambda: [])
    localTime: int = 0
    totalTime: int = 0
    

clock_root  = OrgNode(name="root", parent=None, level=-1 ) 

def explore(parent, node):
    localT = 0.
    if hasattr(node, "clock"):
        for cl in node.clock:
            localT += (cl.end - cl.start).seconds // 60
    print(node.heading)
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


for f in args.files:
    node = load(f)
    node.heading = f.split("/")[-1]
    explore(clock_root, node)


add_time(clock_root)

# pprint(clock_root, compact=True)
    
    
