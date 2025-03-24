'''Module to hold all parsing logic, at both file and directory levels'''
import os
from typing import Any, Callable, Iterator
from utils import findCommentSymbols
import warnings

def parseFile(filepath: os.PathLike, singleCommentSymbol: str, multiLineStartSymbol: str | None = None, multiLineEndSymbol: str | None = None) -> tuple[int, int]:
    loc: int = 0
    currentLine: int = 0
    singleCommentSymbolLength: int = 0 if not singleCommentSymbol else len(singleCommentSymbol)
    multiCommentStartSymbolLength: int = 0 if not multiLineStartSymbol else len(multiLineStartSymbol)
    multiCommentEndSymbolLength: int = 0 if not multiLineEndSymbol else len(multiLineEndSymbol)
    with open(filepath, 'rb') as file:
        commentedBlock: bool = False            # Multiple multilineStarts will still have the same effect as one, so a single flag is enough
        for line in file:
            line: bytes = line.strip()

            # Deal with empty lines, irrespective of whether they are in a commented block or not
            if not line:
                currentLine+=1
                continue

            # Firstly, deal with single line comments if the language supports it (Looking at you, HTML, even if I don't consider you a language)
            if singleCommentSymbol and line[:singleCommentSymbolLength] == singleCommentSymbol:
                # Line is commented, increment line counter and continue
                currentLine+=1
                continue

            # Deal with multiline comments, if the language supports it
            if multiLineStartSymbol:
                # Scan entire line
                idx: int = 0
                validLine: bool = False
                while idx < len(line):
                    if line[idx:idx+multiCommentStartSymbolLength] == multiLineStartSymbol:
                        commentedBlock = True
                        idx += multiCommentStartSymbolLength
                        continue
                    elif line[idx:idx+multiCommentEndSymbolLength] == multiLineEndSymbol:
                        commentedBlock = False
                        idx += multiCommentEndSymbolLength
                        continue
                    elif line[idx:idx+singleCommentSymbolLength] == singleCommentSymbol:
                        # Single comment symbol appears, anything after this is irrelevent
                        break
                    elif not commentedBlock:
                        validLine = True

                    idx += 1
                
                if validLine:
                    loc+=1
            else:
                # Multiline logic ended, and check for single line symbol at start of the line has yielded False
                loc+=1

            currentLine+=1

        return loc, currentLine+1
     
def parseDirectoryNoVerbose(dirData: Iterator[tuple[Any, list[Any], list[Any]]], fileFilterFunction: Callable = lambda outputMapping: True, directoryFilterFunction: Callable = lambda outputMapping : False, recurse:bool = False, level:int = 0, loc: int = 0, totalLines: int = 0, outputMapping: dict = None) -> dict[str, str | int]:
    materialisedDirData: list = list(dirData)
    rootDirectory: os.PathLike = materialisedDirData[0][0]

    print("Scanning dir: ", rootDirectory, level)
    if not outputMapping:
        outputMapping = {"loc" : 0, "total" : 0}

    for file in materialisedDirData[0][2]:
        # File excluded
        if not fileFilterFunction(file):
            continue

        symbolData = findCommentSymbols(file.split(".")[-1])  
        singleLine, multilineStart, multilineEnd = None, None, None

        if isinstance(symbolData, bytes):
            singleLine = symbolData
        elif isinstance(symbolData[1], bytes):
            multilineStart, multilineEnd = symbolData
        else:
            singleLine, (multilineStart, multilineEnd) = symbolData

        l, tl = parseFile(os.path.join(rootDirectory, file), singleLine, multilineStart, multilineEnd)
        totalLines += tl
        loc += l

    outputMapping["loc"] = loc
    outputMapping["total"] = totalLines
    
    if not recurse:
        return outputMapping

    # All files have been parsed in this directory, recurse
    for dir in materialisedDirData[0][1]:
        if not directoryFilterFunction(dir):
            print("Skipping directory:", dir)
            continue
        # Walk over and parse subdirectory
        subdirectoryData = os.walk(os.path.join(rootDirectory, dir))
        op = parseDirectory(subdirectoryData, fileFilterFunction, directoryFilterFunction, True, level+1)

        localLOC, localTotal = op.pop("general").values()
        outputMapping["loc"] = outputMapping["loc"] + localLOC
        outputMapping["total"] = outputMapping["total"] + localTotal
        outputMapping.update(op)


    return outputMapping

def parseDirectory(dirData: Iterator[tuple[Any, list[Any], list[Any]]], fileFilterFunction: Callable = lambda outputMapping: True, directoryFilterFunction: Callable = lambda outputMapping : False, recurse:bool = False, level:int = 0, loc: int = 0, totalLines: int = 0, outputMapping: dict = None) -> tuple[int, int] | None:
    '''#### Iterate over every file in given root directory, and optionally perform the same for every file within its subdirectories\n
    #### args:
    dirData: Output of os.walk() on root directory\n
    Function: Function to handle inclusion/exclusion logic at the file level (file names and file extensions)\n
    directoryFilterFunction: Function to handle inclusion/exclusion logic at the directory level
    level: Count of how many directories deep the current function is searching, increases per recursion

    #### returns:
    integer pair of loc and total lines scanned if no output path specified, else None
    '''
    ...
    # TODO: Remove complete materialisation of dirData
    materialisedDirData: list = list(dirData)
    rootDirectory: os.PathLike = materialisedDirData[0][0]

    print("Scanning dir: ", rootDirectory, level)
    if not outputMapping:
        outputMapping = {"general" : {}}
    for file in materialisedDirData[0][2]:
        # File excluded
        if not fileFilterFunction(file):
            continue

        symbolData = findCommentSymbols(file.split(".")[-1])  
        singleLine, multilineStart, multilineEnd = None, None, None

        if isinstance(symbolData, bytes):
            singleLine = symbolData
        elif isinstance(symbolData[1], bytes):
            multilineStart, multilineEnd = symbolData
        else:
            singleLine, (multilineStart, multilineEnd) = symbolData

        l, tl = parseFile(os.path.join(rootDirectory, file), singleLine, multilineStart, multilineEnd)
        totalLines += tl
        loc += l
        if not outputMapping.get(rootDirectory):
            outputMapping[rootDirectory] = {}
        outputMapping[rootDirectory][file] = {"loc" : l, "total_lines" : tl}
    outputMapping["general"]["loc"] = loc
    outputMapping["general"]["total"] = totalLines
    
    if not recurse:
        return outputMapping

    # All files have been parsed in this directory, recurse
    for dir in materialisedDirData[0][1]:
        if not directoryFilterFunction(dir):
            print("Skipping directory:", dir)
            continue
        # Walk over and parse subdirectory
        subdirectoryData = os.walk(os.path.join(rootDirectory, dir))
        op = parseDirectory(subdirectoryData, fileFilterFunction, directoryFilterFunction, True, level+1)

        localLOC, localTotal = op.pop("general").values()
        outputMapping["general"]["loc"] = outputMapping["general"]["loc"] + localLOC
        outputMapping["general"]["total"] = outputMapping["general"]["total"] + localTotal
        outputMapping.update(op)


    return outputMapping

@warnings.warn("This method of parsing a directory is a failed implementation using collections.deque to reduce stack usage", category=type[DeprecationWarning])
def parseDirectoryDeque(dir: os.PathLike, fileFilterFunction: Callable = lambda outputMapping: True, directoryFilterFunction: Callable = lambda outputMapping : False, recurse: bool = False) -> tuple[int, int] | None:
    from collections import deque
    directories: deque = deque()
    directories.append(dir)
    outputMapping: dict = {"general" : {"loc" : 0, "total" : 0}}
    
    while directories:
        currentScanDir: os.PathLike = directories.popleft()
        print("Scanning dir: ", currentScanDir)

        try:
            for entry in os.scandir(currentScanDir):
                    if entry.is_dir() and directoryFilterFunction(entry.name) and recurse:  
                            print("Adding dir:", entry)
                            directories.append(entry.path)
                    elif entry.is_file() and fileFilterFunction(entry.name):
                        # File good to be parsed
                        print("Scanning file:", entry.name)
                        singleLine, multilineStart, multilineEnd = None, None, None
                        symbolData = findCommentSymbols(entry.name.split(".")[-1])  

                        if isinstance(symbolData, bytes):
                            singleLine = symbolData
                        elif isinstance(symbolData[1], bytes):
                            multilineStart, multilineEnd = symbolData
                        else:
                            singleLine, (multilineStart, multilineEnd) = symbolData
                        
                        loc, total_lines = parseFile(entry.path, singleLine, multilineStart, multilineEnd)
                        outputMapping["general"]["loc"] += loc
                        outputMapping["general"]["total"] += total_lines
                        outputMapping.setdefault(currentScanDir, {})[entry.name] = {
                            "loc": loc, "total_lines": total_lines
                        }
                    else:
                        print("skipped:", entry.name)
        except PermissionError:
            print(f"Skipping {currentScanDir} due to permission error.")

    return outputMapping