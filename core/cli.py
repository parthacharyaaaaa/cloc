import argparse
import os
from utils import formatOutputLine
import json

def findCommentSymbols(extension: str, root: os.PathLike = os.path.dirname(__file__)) -> bytes | tuple[bytes, bytes] | tuple[bytes, tuple[bytes, bytes]]:
    with open(os.path.join(root, "config.json"), 'rb') as config:
        languageMetadata = json.loads(config.read())
        singleLineCommentSymbol: str = languageMetadata["symbols"].get(extension)
        multiLineCommentSymbolPair: str = languageMetadata["multilined"].get(extension)
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

def parseFile(filepath: os.PathLike, singleCommentSymbol: str, multiLineStart: str | None = None, multiLineEnd: str | None = None) -> tuple[int, int]:
    loc: int = 0
    currentLine: int = 0
    with open(filepath, 'rb') as file:
        commentedBlock: bool = False            # Multiple multilineStarts will still have the same effect as one, so a single flag is enough
        for line in file:
            line: bytes = line.strip()

            # Deal with empty lines, irrespective of whether they are in a commented block or not
            if not line:
                currentLine+=1
                continue

            # Deal with multiline comments, if the language supports it
            if multilineStart:
                # Scan entire line
                idx: int = 0
                validLine: bool = False
                multlineStartLength: int = len(multilineStart)
                multlineEndLength: int = len(multilineEnd)
                while idx < len(line):
                    if line[idx:idx+multlineStartLength] == multilineStart:
                        commentedBlock = True
                        idx += multlineStartLength
                        continue
                    elif line[idx:idx+multlineEndLength] == multilineEnd:
                        commentedBlock = False
                        idx += multlineEndLength
                        continue
                    elif not commentedBlock:
                        validLine = True

                    idx += 1
                
                if validLine:
                    loc+=1
                currentLine+=1

            # Finally, deal with single line comments
            if singleLine:
                if line[:len(singleLine)] == singleLine:
                    currentLine+=1
                elif not multilineStart:
                    loc+=1
                    currentLine += 1

        return loc, currentLine
     

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
    
    # Either inclusion or exclusion can be specified, but not both
    bInclusion: bool = bool(args.include_type or args.include_file)
    if ((args.exclude_file or args.exclude_type) and bInclusion):
        print(f"ERROR: Only one of inclusion (-it, -if) or exclusion (-xf, xt) can be specified, but not both")
        exit(500)

    bDirInclude: bool = False

    # Can use short circuit now since we are sure that only inclusion or exclusion has been specified
    extensions: list[str] = args.exclude_type or args.include_type or []
    files: list[str] = args.exclude_file or args.include_file or []
    dirs : list[str] = args.exclude_dir or args.include_dir or []

    # Casting to set for faster lookups
    extensionSet: frozenset = frozenset(extension for extension in extensions)
    fileSet: frozenset = frozenset(file for file in files)
    dirSet: frozenset = frozenset(dir for dir in dirs)

    # File inclusion logic (If !bInclusion, then conditions are just complemented)
    isValid = lambda file: (file.split(".")[-1] in extensionSet or file in fileSet) if bInclusion else (file.split(".")[-1] not in extensionSet and file not in fileSet)

    # Directory inclusion/exclusion logic
    # scanDir = lambda dir: (dir in dirSet) if bDirInclude

    # Traverse through directory, count files
    locMetadata: dict[str[str, int]] = {}

    root: os.PathLike = os.path.abspath(args.dir)
    root_data = os.walk(root)