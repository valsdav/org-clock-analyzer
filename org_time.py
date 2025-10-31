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
            # Skip clock entries that are not closed (end is None)
            if cl.end is None:
                continue
            if start_time:
                if cl.start < start_time: continue
            if end_time:
                if cl.end > end_time: continue
            try:
                localT += (cl.end - cl.start).seconds / (60*60)
            except  Exception as e:
                print(f"Error in node: {node}")
                print(f"Clock entry: {cl}")
                print(f"Error details: {e}")
                localT = 0
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
            #"value": node.totalTime,
            "relTot": f"{100*node.totalFraction:.2f}",
            "relParent": f"{100*node.parentFraction:.2f}"
        }
        if node.localTime > 0:
            obj["children"].append({
                "name":"self",
                "value": node.localTime,
                "relTot": f"{100*node.localTime / (node.totalTime/ node.totalFraction) :.2f}",
                "relParent": f"{100*node.localTime/node.totalTime:.2f}"
            })
        for ch in node.children:
            obj["children"].append(get_json_time(ch))
        return obj
    else:
        return {
            "name": node.name,
            "value": node.totalTime,
            "relTot": f"{100*node.totalFraction:.2f}",
            "relParent": f"{100*node.parentFraction:.2f}"
        }

from dataclasses import dataclass
@dataclass
class ClockSummary:
    name: str
    parent: str
    value: int
    relTot: float
    relParent: float

def flatten_result(json_time):
    results = []
    def flatten(node, parent=None):
        parent_name = parent["name"] if parent else ""
        children = node.get('children', [])
        if node["value"] == 0: return
        yield ClockSummary(name=node["name"],
                            parent=parent_name,
                            value=node["value"],
                            relTot=node["relTot"],
                            relParent=node["relParent"])
        for child in children:
            yield from flatten(child, node)
    for n in json_time["children"]:
        results.extend(flatten(n))
    return results
    

def load_files(files, start_time=None, end_time=None):
    t0 = time.time()
    clock_root  = OrgNode(name="root", parent=None, level=-1 ) 
    for f in files:
        try:
            node = load(f)
        except Exception as e:
            print("Error in file:", f)
            print("Error details:", e)
            continue
        explore(clock_root, node, start_time, end_time)
        clock_root.children[-1].name = f.split("/")[-1][:-4]
    ## Accumulate the time
    add_time(clock_root)
    ## Compute relative time (guard against zero total)
    if clock_root.totalTime > 0:
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

    
    
    
