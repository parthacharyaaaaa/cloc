'''Helper functions'''
import json, yaml, toml, xml

import xml.etree.ElementTree as ETree
import os
import platform
from datetime import datetime

def castMappingToXML(mapping: dict, tag: str | None = None) -> ETree.Element:
    tree: ETree = ETree.Element(tag or "cloc dumps")
    for k,v in mapping.items():
        if isinstance(v, dict):
            tree.append(castMappingToXML(mapping[k], k))
            continue
        subTag = ETree.SubElement(tree, k)
        subTag.text = str(v)
    return tree

def formatOutputLine(fname: str, loc: int) -> str:
    return f"{fname}: {loc} LOC\n"

def dumpOutputJSON(outputMapping: dict, fpath: os.PathLike):
    outputMapping["general"]["time"] = datetime.now().strftime("%d/%m/%y, at %G:%M:%S")
    outputMapping["general"]["platform"] = platform.system()
    with open(os.path.join(os.getcwd(), fpath), "w+") as dumpFile:
        dumpFile.write(json.dumps(outputMapping, skipkeys=True,
                                  ensure_ascii=True,
                                  indent="\t"))

def dumpOutputXML(outputMapping: dict, fpath: os.PathLike):
    outputMapping["general"]["time"] = datetime.now().strftime("%d/%m/%y, at %G:%M:%S")
    outputMapping["general"]["platform"] = platform.system()
    
    root = castMappingToXML(outputMapping)
    tree = ETree.ElementTree(root)          # What am I even trying to do here man
    fpath = fpath if fpath[-4:] == ".xml" else fpath + ".xml"
    with open(os.path.join(os.getcwd(), fpath), "wb+") as dumpFile:
        tree.write(dumpFile, 'utf-8', True) # omfg there's no indentation function