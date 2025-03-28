'''Module to hold all parsing logic, at both file and directory levels'''
import os
from typing import Any, Callable, Iterator
from itertools import islice
import ctypes

from cloc.ctypes_interfacing import lib, BatchScanResult
from cloc.utils import findCommentSymbols

def parseFile(filepath: os.PathLike, singleCommentSymbol: str, multiLineStartSymbol: str | None = None, multiLineEndSymbol: str | None = None, minChars: int = 0) -> tuple[int, int]:
    loc: int = 0
    total: int = 0
    singleCommentSymbolLength: int = 0 if not singleCommentSymbol else len(singleCommentSymbol)
    multiCommentStartSymbolLength: int = 0 if not multiLineStartSymbol else len(multiLineStartSymbol)
    multiCommentEndSymbolLength: int = 0 if not multiLineEndSymbol else len(multiLineEndSymbol)
    with open(filepath, 'rb') as file:
        commentedBlock: bool = False            # Multiple multilineStarts will still have the same effect as one, so a single flag is enough

        while batch := list(islice(file, 100)):
            batchSize = len(batch)
            
            batchScanResult: BatchScanResult = lib.scanBatch((ctypes.c_char_p * batchSize)(*batch), batchSize, commentedBlock, minChars, singleCommentSymbol, singleCommentSymbolLength, multiLineStartSymbol, multiCommentStartSymbolLength, multiLineEndSymbol, multiCommentEndSymbolLength)

            loc += batchScanResult.validLines
            total += batchSize

            commentedBlock = batchScanResult.commentedBlock
        return loc, total
  

def parseDirectoryNoVerbose(dirData: Iterator[tuple[Any, list[Any], list[Any]]], customSymbols: dict = None, fileFilterFunction: Callable = lambda outputMapping: True, directoryFilterFunction: Callable = lambda outputMapping : False, minChars:int = 0, recurse:bool = False, level:int = 0, loc: int = 0, totalLines: int = 0, outputMapping: dict = None) -> dict[str, str | int]:
    materialisedDirData: list[os.PathLike] = next(dirData)
    rootDirectory: os.PathLike = materialisedDirData[0]

    if not outputMapping:
        outputMapping = {"loc" : 0, "total" : 0}

    for file in materialisedDirData[2]:
        # File excluded
        if not fileFilterFunction(file):
            continue
        
        singleLine, multiLineStart, multiLineEnd = None, None, None
        if not customSymbols:
            symbolData = findCommentSymbols(file.split(".")[-1])  

            if isinstance(symbolData, bytes):
                singleLine = symbolData
            elif isinstance(symbolData[1], bytes):
                multiLineStart, multiLineEnd = symbolData
            else:
                singleLine, (multiLineStart, multiLineEnd) = symbolData
        else:
            # Custom symbols given
            singleLine = customSymbols.get("single")
            multiLineStart = customSymbols.get("multistart")
            multiLineEnd = customSymbols.get("multiend")

        l, tl = parseFile(os.path.join(rootDirectory, file), singleLine, multiLineStart, multiLineEnd)
        totalLines += tl
        loc += l

    outputMapping["loc"] = loc
    outputMapping["total"] = totalLines
    
    if not recurse:
        return outputMapping

    # All files have been parsed in this directory, recurse
    for dir in materialisedDirData[1]:
        if not directoryFilterFunction(dir):
            continue
        # Walk over and parse subdirectory
        subdirectoryData = os.walk(os.path.join(rootDirectory, dir))
        op = parseDirectory(subdirectoryData, customSymbols ,fileFilterFunction, directoryFilterFunction, True, level+1)

        localLOC, localTotal = op.pop("general").values()
        outputMapping["loc"] = outputMapping["loc"] + localLOC
        outputMapping["total"] = outputMapping["total"] + localTotal
        outputMapping.update(op)

    return outputMapping

def parseDirectory(dirData: Iterator[tuple[Any, list[Any], list[Any]]], customSymbols: dict = None, fileFilterFunction: Callable = lambda outputMapping: True, directoryFilterFunction: Callable = lambda outputMapping : False, minChars: int = 0, recurse:bool = False, level:int = 0, loc: int = 0, totalLines: int = 0, outputMapping: dict = None) -> tuple[int, int] | None:
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
    materialisedDirData: list = next(dirData)
    rootDirectory: os.PathLike = materialisedDirData[0]

    if not outputMapping:
        outputMapping = {"general" : {}}
    for file in materialisedDirData[2]:
        # File excluded
        if not fileFilterFunction(file):
            continue
        singleLine, multiLineStart, multiLineEnd = None, None, None
        if not customSymbols:
            symbolData = findCommentSymbols(file.split(".")[-1])  
            if isinstance(symbolData, bytes):
                singleLine = symbolData
            elif isinstance(symbolData[1], bytes):
                multiLineStart, multiLineEnd = symbolData
            else:
                singleLine, (multiLineStart, multiLineEnd) = symbolData
        else:
            # Custom symbols given
            singleLine = customSymbols.get("single")
            multiLineStart = customSymbols.get("multistart")
            multiLineEnd = customSymbols.get("multiend")

        l, tl = parseFile(os.path.join(rootDirectory, file), singleLine, multiLineStart, multiLineEnd)
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
    for dir in materialisedDirData[1]:
        if not directoryFilterFunction(dir):
            print("Skipping directory:", dir)
            continue
        # Walk over and parse subdirectory
        subdirectoryData = os.walk(os.path.join(rootDirectory, dir))
        op = parseDirectory(subdirectoryData, customSymbols, fileFilterFunction, directoryFilterFunction, True, level+1)

        localLOC, localTotal = op.pop("general").values()
        outputMapping["general"]["loc"] = outputMapping["general"]["loc"] + localLOC
        outputMapping["general"]["total"] = outputMapping["general"]["total"] + localTotal
        outputMapping.update(op)


    return outputMapping