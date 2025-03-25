import argparse
import os
from utils import findCommentSymbols
from utils import OUTPUT_MAPPING
from typing import Callable
from types import MappingProxyType
from parsing import parseDirectory, parseDirectoryNoVerbose, parseFile
from datetime import datetime
import platform
from config import FLAGS

parser: argparse.ArgumentParser = argparse.ArgumentParser(description="A simple CLI tool to count lines of code (LOC) of your files")

parser.add_argument("-v", "--version", help="Current version of cloc", action="store_true")
parser.add_argument("-d", "--dir", nargs=1, help="Specify the directory to scan. Either this or '-d' must be used")
parser.add_argument("-f", "--file", nargs=1, help="Specify the file to scan. Either this or '-d' must be used")
parser.add_argument("-ss", "--single-symbol", nargs=1, help="[OPTIONAL] Specify the single-line comment symbol. By default, the comments are identified via file extension itself, Note that if this flag is specified with the directory flag, then all files within that directory are checked against this comment symbol")
parser.add_argument("-ms", "--multiline-symbol", nargs=1, help="[OPTIONAL] Specify the multi-line comment symbols as a space-separated pair of opening and closing symbols. Behaves similiar to single-line comments")
parser.add_argument("-xf", "--exclude-file", nargs="+", help="[OPTIONAL] Exclude files by name")
parser.add_argument("-xd", "--exclude-dir", nargs="+", help="[OPTIONAL] Exclude directories by name")
parser.add_argument("-xt", "--exclude-type", nargs="+", help="[OPTIONAL] Exclude files by extension")
parser.add_argument("-id", "--include-dir", nargs="+", help="[OPTIONAL] Include directories by name")
parser.add_argument("-if", "--include-file", nargs="+", help="[OPTIONAL] Include files by name")
parser.add_argument("-it", "--include-type", nargs="+", help="[OPTIONAL] Include files by extension, useful for specificity when working with directories with files for different languages")
parser.add_argument("-vb", "--verbose", help="Get LOC and total lines for every file scanned", action="store_true", default=FLAGS.verbose)
parser.add_argument("-o", "--output", nargs=1, help="[OPTIONAL] Specify output file to dump counts into. If not specified, output is dumped to stdout. If output file is in .json, .toml, .yaml, or .db/.sql format, then output is ordered differently.")
parser.add_argument("-r", "--recurse", help="[OPTIONAL] Recursively scan every sub-directory too", action="store_true", default=FLAGS.recurse)

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

    symbolData: dict = {}
    if args.single_symbol:
        symbolData["single"] = args.single_symbol[0].strip().encode()
    if args.multiline_symbol:
        pairing = args.multiline_symbol[0].strip().split(" ")
        if len(pairing) != 2:
            print(f"ERROR: Multiline symbols f{args.multiline_symbol[0]} must be space-separated pair, such as '/* */'")
            exit(500)
        symbolData["multistart"] = pairing[0].encode()
        symbolData['multiend'] = pairing[1].encode()

    # Single file, no need to check and validate other flags
    if bIsFile:     
        if not os.path.exists(args.file):
            print(f"ERROR: {args.file} not found")       
            exit(404)
        if not os.path.isfile(args.file):
            print(f"ERROR: {args.file} is not a valid file")
            exit(500)

        # Fetch comment symbols if not specified via -cs
        singleLine, multiLineStart, multiLineEnd = None, None, None
        if not symbolData:
            symbolData = findCommentSymbols(args.file.split(".")[-1])
            if isinstance(symbolData, bytes):
                # Single line only
                singleLine: bytes = symbolData
            elif isinstance(symbolData[1], bytes):
                # Multiline only
                multiLineStart: bytes = symbolData[0]
                multiLineEnd: bytes = symbolData[1]
            else:
                # Both single line and multiline
                singleLine: bytes = symbolData[0]
                multiLineStart: bytes = symbolData[1][0]
                multiLineEnd: bytes = symbolData[1][1]
        else:
            singleLine = symbolData.get("single")
            multiLineStart = symbolData.get("multistart")
            multiLineEnd = symbolData.get("multiend")

        loc, total = parseFile(args.file, singleLine, multiLineStart, multiLineEnd)
        outputMapping: MappingProxyType = MappingProxyType({"loc" : loc, "total" : total, "time" : datetime.now().strftime("%d/%m/%y, at %H:%M:%S"), "platform" : platform.system()})
        if not args.output:
            print(outputMapping)
        else:
            outputFiletype: str = args.output[0].split(".")[-1].lower()

            # Fetch output function based on file extension, default to standard write logic
            outputFunction: Callable = OUTPUT_MAPPING.get(outputFiletype, OUTPUT_MAPPING[None])
            outputFunction(outputMapping=outputMapping, fpath=args.output[0])
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

    if args.verbose:
        outputMapping = parseDirectory(root_data, symbolData, fileFilter, directoryFilter, args.recurse)
        outputMapping["general"]["time"] = datetime.now().strftime("%d/%m/%y, at %H:%M:%S")
        outputMapping["general"]["platform"] = platform.system()
    else:
        outputMapping = parseDirectoryNoVerbose(root_data, symbolData, fileFilter, directoryFilter, args.recurse)
        outputMapping["time"] = datetime.now().strftime("%d/%m/%y, at %H:%M:%S")
        outputMapping["platform"] = platform.system()

    print("=================== SCAN COMPLETE ====================")
    if args.output:
        outputFiletype: str = args.output[0].split(".")[-1].lower()

        # Fetch output function based on file extension, default to standard write logic
        outputFunction: Callable = OUTPUT_MAPPING.get(outputFiletype, OUTPUT_MAPPING[None])
        outputFunction(outputMapping=outputMapping, fpath=args.output[0])
    else:
        print(outputMapping)
        exit(200)