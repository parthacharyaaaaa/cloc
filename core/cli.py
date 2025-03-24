import argparse
import os
from utils import formatOutputLine, dumpOutputJSON, dumpOutputXML, dumpOutputSQL, dumpOutputSTD, findCommentSymbols
from parsing import parseDirectory, parseDirectoryNoVerbose, parseFile
from datetime import datetime
import platform

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
parser.add_argument("-vb", "--verbose", help="Get LOC and total lines for every file scanned", action="store_true")
parser.add_argument("-o", "--output", nargs=1, help="[OPTIONAL] Specify output file to dump counts into. If not specified, output is dumped to stdout. If output file is in .json, .toml, .yaml, or .db/.sql format, then output is ordered differently.")
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

    if args.verbose:
        outputMapping = parseDirectory(root_data, fileFilter, directoryFilter, args.recurse)
    else:
        outputMapping = parseDirectoryNoVerbose(root_data, fileFilter, directoryFilter, args.recurse)
    outputMapping["general"]["time"] = datetime.now().strftime("%d/%m/%y, at %H:%M:%S")
    outputMapping["general"]["platform"] = platform.system()


    if args.output:
        args.output = args.output[0]
        outputTkns = args.output.split(".")
        if len(outputTkns) == 1:
            extension: str = None
        else:
            extension: str = outputTkns[-1]
        outputTkns = None

        if extension == "json":
            dumpOutputJSON(outputMapping, args.output)
        elif extension == "xml":
            dumpOutputXML(outputMapping, args.output)
        elif extension == "sql" or extension == "db":
            dumpOutputSQL(outputMapping, args.output)
        elif extension in {"txt", "log", "logs", None, ""}:
            dumpOutputSTD(outputMapping, args.output)