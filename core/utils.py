'''Helper functions'''
import json

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

def dumpOutputSQL(outputMapping: dict, fpath: os.PathLike):
    outputMapping["general"]["time"] = datetime.now().strftime("%d/%m/%y, at %G:%M:%S")
    outputMapping["general"]["platform"] = platform.system()
    # Best language fr, has SQL API built-in
    import sqlite3
    
    dbConnection: sqlite3.Connection = sqlite3.connect(fpath, isolation_level="IMMEDIATE")
    dbCursor: sqlite3.Cursor = dbConnection.cursor()

    # No context manager protocol in sqlite3 cursors :(
    try:
        # Enable Foreign Keys if this current driver hasn't done so already
        dbCursor.execute("PRAGMA foreign_keys = ON;")

        # DDL
        dbCursor.execute('''
                         CREATE TABLE IF NOT EXISTS general (LOC INTEGER DEFAULT 0,
                         total_lines INTEGER DEFAULT 0,
                         time DATETIME,
                         platform VARCHAR(32));
                         ''')
        
        dbCursor.execute('''
                         CREATE TABLE IF NOT EXISTS directory (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         _name VARCHAR(1024) NOT NULL UNIQUE);
                         ''')
        
        dbCursor.execute('''
                         CREATE TABLE IF NOT EXISTS file_data (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         directory INTEGER NOT NULL,
                         _name VARCHAR(1024) NOT NULL,
                         LOC INTEGER DEFAULT 0,
                         total_lines INTEGER DEFAULT 0,
                         FOREIGN KEY (directory) references directory(ID));
                        ''')
        dbConnection.commit()

        # DML
        for table in ("general","file_data", "directory"):
            dbConnection.execute(f"DELETE FROM {table}")
        dbConnection.commit()

        dbConnection.execute("INSERT INTO general VALUES (?, ?, ?, ?)", (outputMapping['general']["LOC"], outputMapping['general']["Total"], outputMapping['general']["time"], outputMapping['general']["platform"]))
        
        outputMapping.pop("general")
        for directory, fileMapping in outputMapping.items():
            print(fileMapping)
            dbCursor.execute("INSERT INTO directory (_name) VALUES (?) RETURNING ID", (directory,))
            _id: int = dbCursor.fetchone()[0]
            dbCursor.executemany("INSERT INTO file_data (directory, _name, LOC, total_lines) VALUES (?, ?, ?, ?);",
                                 ([_id, filename, fileData["loc"], fileData["total_lines"]] for filename, fileData in fileMapping.items()))
        dbConnection.commit()
    finally:
        if dbCursor:
            dbCursor = None
        dbConnection.close()
        dbConnection = None
