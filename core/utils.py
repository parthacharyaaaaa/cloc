'''Helper functions'''
import json
import xml.etree.ElementTree as ETree
import os
from config import LANGUAGES

def findCommentSymbols(extension: str, symbolMapping: dict[str, dict[str, str]] | None = None) -> bytes | tuple[bytes, bytes] | tuple[bytes, tuple[bytes, bytes]]:
        '''### Find symbols that denote a comment for a specific language
        
        #### args
        extension: File extension of the language\n
        symbolMapping: Mapping of file extensions and their corresponding symbols. Keys are `symbols` for single-line comments and `multilined` for multi-line comments. See `languages.json` for the actual mapping'''

        if not symbolMapping:
            symbolMapping = LANGUAGES

        singleLineCommentSymbol: str = symbolMapping["symbols"].get(extension)
        multiLineCommentSymbolPair: str = symbolMapping["multilined"].get(extension)
        if multiLineCommentSymbolPair:
            multiLineCommentSymbolPair = multiLineCommentSymbolPair.split(" ")

        if not (singleLineCommentSymbol or multiLineCommentSymbolPair):        
            print(f"No comment symbols found for extension .{extension}")
            exit(500)

        if not multiLineCommentSymbolPair:
            return singleLineCommentSymbol.encode()
        if not singleLineCommentSymbol:
            return multiLineCommentSymbolPair[0].encode(), multiLineCommentSymbolPair[1].encode()
        
        return singleLineCommentSymbol.encode(), (multiLineCommentSymbolPair[0].encode(), multiLineCommentSymbolPair[1].encode())


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

def dumpOutputSTD(outputMapping: dict, fpath: os.PathLike) -> None:
    '''Dump output to a standard text/log file'''
    with open(fpath, "w+") as file:
        mainMetadata: str = "\n".join(tuple(f"{k} : {v}" for k,v in outputMapping.pop("general").items()))
        file.write(mainMetadata)
        return

def dumpOutputJSON(outputMapping: dict, fpath: os.PathLike) -> None:
    '''Dump output to JSON file, with proper formatting'''
    with open(os.path.join(os.getcwd(), fpath), "w+") as dumpFile:
        dumpFile.write(json.dumps(outputMapping, skipkeys=True,
                                  ensure_ascii=True,
                                  indent="\t"))

def dumpOutputXML(outputMapping: dict, fpath: os.PathLike) -> None:
    '''Dump output to XML file, with proper formatting'''
    root = castMappingToXML(outputMapping)
    tree = ETree.ElementTree(root)          # What am I even trying to do here man
    fpath = fpath if fpath[-4:] == ".xml" else fpath + ".xml"
    with open(os.path.join(os.getcwd(), fpath), "wb+") as dumpFile:
        tree.write(dumpFile, 'utf-8', True) # omfg there's no indentation function

def dumpOutputSQL(outputMapping: dict, fpath: os.PathLike) -> None:
    '''Dump output to a SQLite database (.db, .sql)'''
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
                         CREATE TABLE IF NOT EXISTS file_data (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         directory VARCHAR(1024) NOT NULL,
                         _name VARCHAR(1024) NOT NULL,
                         LOC INTEGER DEFAULT 0,
                         total_lines INTEGER DEFAULT 0);
                        ''')
        dbConnection.commit()

        # DML
        # Clear out all previous data
        for table in ("general","file_data"):
            dbConnection.execute(f"DELETE FROM {table}")
        dbConnection.commit()

        dbConnection.execute("INSERT INTO general VALUES (?, ?, ?, ?)", (outputMapping['general']["LOC"], outputMapping['general']["Total"], outputMapping['general']["time"], outputMapping['general']["platform"]))
        
        outputMapping.pop("general")
        for directory, fileMapping in outputMapping.items():
            dbCursor.executemany("INSERT INTO file_data (directory, _name, LOC, total_lines) VALUES (?, ?, ?, ?);",
                                 ([directory, filename, fileData["loc"], fileData["total_lines"]] for filename, fileData in fileMapping.items()))
        dbConnection.commit()
    finally:
        if dbCursor:
            dbCursor = None
        dbConnection.close()
        dbConnection = None
