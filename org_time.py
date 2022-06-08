from __future__ import annotations
from orgparse import load, loads
import sys
from pprint import pprint
from dataclasses import dataclass,field
import time

@dataclass
class OrgNode:
    name: str
    level : int
    parent: OrgNode
    children : list = field(default_factory=lambda: [])
    tags: list = field(default_factory=lambda: [])
    localTime: int = 0
    totalTime: int = 0
    totalFraction: float = 0.
    parentFraction: float = 0.
    

def explore(parent, node, start_time=None, end_time=None):
    localT = 0.
    if hasattr(node, "clock"):
        for cl in node.clock:
            if start_time:
                if cl.start < start_time: continue
            if end_time:
                if cl.end > end_time: continue
            localT += (cl.end - cl.start).seconds / (60*60)
    #print("Loading: ", node.heading)
    orgnode = OrgNode(name=node.heading,
                      level=node.level,
                      localTime=localT,
                      totalTime=localT,
                      tags=node.tags,
                      parent=parent)
    parent.children.append(orgnode)
    for children in node.children:
        explore(orgnode, children, start_time, end_time)

#Now traverse to get the total time
def add_time(node):
    for ch in node.children:
        add_time(ch)
    if node.parent:
        node.parent.totalTime += node.totalTime


def relative_time(node, total, parent):
    node.totalFraction = node.totalTime/total
    node.parentFraction = node.totalTime/parent
    if node.totalTime == 0: return
    for ch in node.children:
        relative_time(ch, total, node.totalTime)


def get_json_time(node):
    if len(node.children):
        obj = {
            "name": node.name,
            "children": [
            ],
            "relTot": f"{100*node.totalFraction:.3f}",
            "relParent": f"{100*node.parentFraction:.3f}"
        }
        if node.localTime > 0:
            obj["children"].append({
                "name":"self",
                "value": node.localTime,
                "relTot": f"{100*node.localTime / (node.totalTime/ node.totalFraction) :.3f}",
                "relParent": f"{100*node.localTime/node.totalTime:.3f}"
            })
        for ch in node.children:
            obj["children"].append(get_json_time(ch))
        return obj
    else:
        return {
            "name": node.name,
            "value": node.totalTime,
            "relTot": f"{100*node.totalFraction:.3f}",
            "relParent": f"{100*node.parentFraction:.3f}"
        }



def load_files(files, start_time=None, end_time=None):
    t0 = time.time()
    clock_root  = OrgNode(name="root", parent=None, level=-1 ) 
    for f in files:
        node = load(f)
        explore(clock_root, node, start_time, end_time)
        clock_root.children[-1].name = f.split("/")[-1][:-4]
    ## Accumulate the time
    add_time(clock_root)
    ## Compute relative time
    relative_time(clock_root, clock_root.totalTime, clock_root.totalTime)
    t1 = time.time()
    print(f"Loaded in {t1-t0:.4f} s")
    return clock_root
    


    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--files",  nargs="+", type=str , help="input files")
    args = parser.parse_args()
    clock_root = load_files(args.files)
    output = get_json_time(clock_root)

    
    
    
