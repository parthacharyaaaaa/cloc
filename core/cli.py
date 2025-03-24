import argparse
import os
from utils import formatOutputLine, dumpOutputJSON, dumpOutputXML, dumpOutputSQL
import json
from typing import Callable, Iterator, Any

with open(os.path.join(os.path.dirname(__file__), "config.json"), 'rb') as config:
    CONFIG: dict = json.loads(config.read())

def findCommentSymbols(extension: str, symbolMapping: dict[str, dict[str, str]] = CONFIG) -> bytes | tuple[bytes, bytes] | tuple[bytes, tuple[bytes, bytes]]:
        '''### Find symbols that denote a comment for a specific language
        
        #### args
        extension: File extension of the language\n
        symbolMapping: Mapping of file extensions and their corresponding symbols. Keys are `symbols` for single-line comments and `multilined` for multi-line comments. See `config.json` for the actual mapping'''
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

def parseFile(filepath: os.PathLike, singleCommentSymbol: str, multiLineStartSymbol: str | None = None, multiLineEndSymbol: str | None = None) -> tuple[int, int]:
    loc: int = 0
    currentLine: int = 0
    singleCommentSymbolLength: int = len(singleCommentSymbol)
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
     
def parseDirectory(dirData: Iterator[tuple[Any, list[Any], list[Any]]], fileFilterFunction: Callable = lambda x: True, directoryFilterFunction: Callable = lambda x : False, recurse:bool = False, level:int = 0, loc: int = 0, totalLines: int = 0, outputMapping: dict = {"general" : {}}) -> tuple[int, int] | None:
    '''#### Iterate over every file in given root directory, and optionally perform the same for every file within its subdirectories\n
    #### args:
    dirData: Output of os.walk() on root directory\n
    Function: Function to handle inclusion/exclusion logic at the file level (file names and file extensions)\n
    directoryFilterFunction: Function to handle inclusion/exclusion logic at the directory level
    level: Count of how many directories deep the current function is searching, increases per recursion

    #### returns:
    integer pair of LOC and total lines scanned if no output path specified, else None
    '''
    ...
    # TODO: Remove complete materialisation of dirData
    materialisedDirData: list = list(dirData)
    print(materialisedDirData)
    rootDirectory: os.PathLike = materialisedDirData[0][0]

    # Directory excluded
    if not directoryFilterFunction(rootDirectory) and level != 0:
        print("Skipping dir: ", rootDirectory)
        return None
    print("Scanning dir: ", rootDirectory, level)
    for file in materialisedDirData[0][2]:
        # File excluded
        if not fileFilterFunction(file):
            print("Skipping file: ", file)
            continue
        print("Scanning file: ", file)

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
        outputMapping["general"]["LOC"] = loc
        outputMapping["general"]["Total"] = totalLines
    
    if not recurse:
        return outputMapping

    # All files have been parsed in this directory, recurse
    for dir in materialisedDirData[0][1]:
        if not directoryFilter(dir):
            continue
        subdirectoryData = os.walk(os.path.join(rootDirectory, dir))
        outputMapping = parseDirectory(subdirectoryData, fileFilterFunction, directoryFilterFunction, recurse, level+1, loc, totalLines)

    return outputMapping

def formatOutputTOML(outputMapping: dict, fpath: os.PathLike): ...
def formatOutputYAML(outputMapping: dict, fpath: os.PathLike): ...
def formatOutputSQL(outputMapping: dict, fpath: os.PathLike): ...
parser: argparse.ArgumentParser = argparse.ArgumentParser(description="A simple CLI tool to count lines of code (LOC) of your files")

parser.add_argument("-v", "--version", help="Current version of cloc", action="store_true")
parser.add_argument("-d", "--dir", nargs=1, help="Specify the directory to scan. Either this or '-d' must be used")
parser.add_argument("-f", "--file", nargs=1, help="Specify the file to scan. Either this or '-d' must be used")
parser.add_argument("-cs", "--comment-symbol", nargs="+", help="[OPTIONAL] Specify the comment symbols. By default, the comments are identified via file extension itself, Note that if this flag is specified with the directory flag, then all files within that directory are checked against this comment symbol")
parser.add_argument("-xf", "--exclude-file", nargs="+", help="[OPTIONAL] Exclude files by name")
parser.add_argument("-xd", "--exclude-dir", nargs="+", help="[OPTIONAL] Exclude directories by name")
parser.add_argument("-xt", "--exclude-type", nargs="+", help="[OPTIONAL] Exclude files by extension")
parser.add_argument("-id", "--include-dir", nargs="+", help="[OPTIONAL] Include directories by name")
parser.add_argument("-if", "--include-file", nargs="+", help="[OPTIONAL] Include files by name")
parser.add_argument("-it", "--include-type", nargs="+", help="[OPTIONAL] Include files by extension, useful for specificity when working with directories with files for different languages")
parser.add_argument("-o", "--output", nargs=1, help="[OPTIONAL] Specify output file to dump counts into. If not specified, output is dumped to stdout. If output file is in .json, .toml, .yaml, or .db/.sql format, then output is ordered differently.")
parser.add_argument("-g", "--group", help="[OPTIONAL] Group LOC counts by file types", action="store_true")
parser.add_argument("-r", "--recurse", help="[OPTIONAL] Recursively scan every sub-directory too", action="store_true")

if __name__ == "__main__":
    args = parser.parse_args()

    bCustomSymbols: bool = False
    bIsFile: bool = False

    if(args.dir and args.file):
        print("ERROR: Both target directory and target file specified. Please specify only one")
        exit(500)

    if args.file:
        args.file = args.file[0]    # Fetch first (and only) entry from list since `nargs` param in parser.add_argument returns the args as a list
        bIsFile = True

    if args.comment_symbol:
        symbolData: frozenset = frozenset(*args.comment_symbol)
    else:
        symbolData = None

    # Single file, no need to check and validate other flags
    if bIsFile:     
        if not os.path.exists(args.file):
            print(f"ERROR: {args.file} not found")       
            exit(404)
        if not os.path.isfile(args.file):
            print(f"ERROR: {args.file} is not a valid file")
            exit(500)

        # Fetch comment symbols if not specified via -cs
        if not symbolData:
            symbolData = findCommentSymbols(args.file.split(".")[-1])
            if isinstance(symbolData, bytes):
                # Single line only
                singleLine: bytes = symbolData
                multilineEnd, multilineStart = None, None
            elif isinstance(symbolData[1], bytes):
                # Multiline only
                singleLine = None
                multilineStart: bytes = symbolData[0]
                multilineEnd: bytes = symbolData[1]
            else:
                # Both single line and multiline
                singleLine: bytes = symbolData[0]
                multilineStart: bytes = symbolData[1][0]
                multilineEnd: bytes = symbolData[1][1]

        loc, currentLine = parseFile(args.file, singleLine, multilineStart, multilineEnd)
        if not args.output:
            print(formatOutputLine(args.file, loc))
            print(currentLine)
            print("Scan ended")
        exit(200)


    # Directory
    if not args.dir:
        print(f"ERROR: File or directory must be specified")
        exit(500)

    args.dir = args.dir[0]  # Fetch first (and only) entry from list since `nargs` param in parser.add_argument returns the args as a list
    if not os.path.isdir(args.dir):
        print(f"ERROR: {args.dir} is not a valid directory")
        exit(500)
    
    ### Handle file-level filtering logic, if any ###
    bFileFilter: bool = False

    # Either inclusion or exclusion can be specified, but not both
    bInclusion: bool = bool(args.include_type or args.include_file)
    if bInclusion or (args.exclude_file or args.exclude_type):
        bFileFilter = True

    if ((args.exclude_file or args.exclude_type) and bInclusion):
        print(f"ERROR: Only one of inclusion (-it, -if) or exclusion (-xf, xt) can be specified, but not both")
        exit(500)

    # Can use short circuit now since we are sure that only inclusion or exclusion has been specified
    extensions: list[str] = args.exclude_type or args.include_type or []
    files: list[str] = args.exclude_file or args.include_file or []
    dirs : list[str] = args.exclude_dir or args.include_dir or []

    # Casting to set for faster lookups
    extensionSet: frozenset = frozenset(extension for extension in extensions)
    fileSet: frozenset = frozenset(file for file in files)

    # Function for determining valid files
    if bFileFilter:
        fileFilter = lambda file: (file.split(".")[-1] in extensionSet or file in fileSet) if bInclusion else (file.split(".")[-1] not in extensionSet and file not in fileSet)
    else:
        fileFilter = lambda _ : True    # No file filter logic given, return True blindly
    
    ### Handle direcotory-level filtering logic, if any ###
    bDirFilter: bool = args.include_dir or args.exclude_dir

    if bDirFilter:
        bDirInclusion: bool = False
        directories: set = {}
        if (args.include_dir and args.exclude_dir):
            print(f"ERROR: Both directory inclusion and exclusion rules cannot be specified together")
            exit(500)
        
        if args.include_dir:
            directories = set(args.include_dir)
            bDirInclusion = True
        directories = set(args.exclude_dir)

        # Cast for faster lookups
        dirSet: frozenset = frozenset(dir for dir in directories)
        
        directoryFilter = lambda dir : dir in dirSet if bInclusion else dir not in dirSet
    else:
        directoryFilter = lambda _ : False if not args.recurse else True          # No directory filters given, accept subdirectories based on recurse flag

    root: os.PathLike = os.path.abspath(args.dir)
    root_data = os.walk(root)

    x = parseDirectory(root_data, fileFilter, directoryFilter, True)
    if args.output:
        args.output = args.output[0]
        extension: str = args.output.split(".")[-1].lower()

        if extension == "json":
            dumpOutputJSON(x, args.output)
        elif extension == "xml":
            dumpOutputXML(x, args.output)
        elif extension == "sql" or extension == "db":
            dumpOutputSQL(x, args.output)