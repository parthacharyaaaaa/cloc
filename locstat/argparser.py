import argparse
from functools import partial
import json
import os
import sys
from types import NoneType
from typing import Any, Final, Sequence

from locstat import __tool_name__
from locstat.data_structures.config import ClocConfig
from locstat.data_structures.parse_modes import ParseMode
from locstat.data_structures.verbosity import Verbosity
from locstat.utilities.core import resolve_relative_paths
from locstat.utilities.presentation import OUTPUT_MAPPING, dump_std_output

__all__ = ("initialize_parser", "parse_arguments")


def _validate_directory(arg: str) -> str:
    arg = arg.strip()
    if not os.path.isdir(arg):
        sys.stderr.write(f"Directory {arg} could not be found\n")
        sys.exit(1)
    return arg


def _validate_filepath(arg: str) -> str:
    arg = arg.strip()
    if not os.path.isfile(arg):
        sys.stderr.write(f"File {arg} could not be found\n")
        sys.exit(1)
    return arg


def _validate_min_chars(arg: str) -> int:
    min_chars: int = int(arg)
    if min_chars < 0:
        sys.stderr.write("Minimum characters cannot be negative\n")
        sys.exit(1)
    elif min_chars == 0:
        sys.stdout.write(
            "Note: minimum characters of 0 implies empty lines also contribute to LOC\n"
        )
    return min_chars


def _validate_parsing_mode(arg: str) -> ParseMode:
    arg = arg.strip().upper()
    try:
        return ParseMode(arg)
    except ValueError:
        sys.stderr.write(
            f"Invalid parsing mode {arg}, supported parsing modes: {', '.join((k for k in ParseMode._value2member_map_.keys()))}\n"
        )
        sys.exit(1)


def _validate_max_depth(arg: str) -> int:
    try:
        depth: int = int(arg)
    except ValueError:
        sys.stderr.write("Traversal depth must be integer value\n")
        sys.exit(1)
    return depth


def _validate_verbosity(arg: str) -> Verbosity:
    arg = arg.strip().upper()
    try:
        return Verbosity(arg)
    except ValueError:
        sys.stderr.write(
            " ".join(
                (
                    f"Invalid verbosity mode {arg},",
                    "Supported:",
                    ", ".join((k for k in Verbosity._value2member_map_)),
                    "\n",
                )
            )
        )
        sys.exit(1)


def _validate_config_args(config: ClocConfig, arg: str, /, copy: list[str] = []) -> str:
    if (arg := arg.lower()) not in config.configurable and (len(copy) % 2 == 0):
        sys.stdout.write(
            " ".join(
                (
                    f"No such configurable option: {arg}.\n",
                    "Available configurations:\n",
                    ", ".join(config.configurable),
                    "\n",
                )
            )
        )
        sys.exit(1)
    copy.append(arg)
    return arg


def _process_langauge_metadata_filepath(config: ClocConfig, arg: str) -> str:
    if not arg.endswith(".json"):
        sys.stdout.write("Language metadata file must have JSON extension")
        sys.exit(1)

    if not os.path.isfile(arg):
        sys.stdout.write(f"Language metadata filepath {arg} not found")
        sys.exit(1)

    with open(arg, "r") as language_metadata_file:
        language_metadata: dict[str, Any] = json.load(language_metadata_file)
        for language, comment_symbols in language_metadata.items():
            if not (
                isinstance(comment_symbols, list)
                and len(comment_symbols) == 3
                and all(isinstance(s, (str, NoneType)) for s in comment_symbols)
            ):
                sys.stdout.write(
                    ", ".join(
                        (
                            f"Invalid comment metadata for extension {language}",
                            "comment symbols must be a list of 3 strings/null",
                            'example: ["#", null, null] for Python\n',
                        )
                    )
                )
                sys.stdout.write(f"Failed at: {comment_symbols}\n")
                sys.exit(1)

        config.update_languages_metadata(language_metadata)
        return arg


def initialize_parser(config: ClocConfig) -> argparse.ArgumentParser:
    """Instantiate and return an argument parser

    :param config: Configuration instance used to add additional validation/parsing rules
    :type config: ClocConfig

    :return: argparse.ArgumentParser"""

    parser: Final[argparse.ArgumentParser] = argparse.ArgumentParser(
        prog=__tool_name__, description="CLI tool to count lines of code"
    )

    required_group: argparse._MutuallyExclusiveGroup = (
        parser.add_mutually_exclusive_group(required=True)
    )
    # Tool identification
    required_group.add_argument(
        "-v",
        "--version",
        help=f"Current version of {__tool_name__}",
        action="store_true",
    )

    # Configurations
    required_group.add_argument(
        "-c",
        "--config",
        help=" ".join(
            (
                f"View and edit default configurations for {__tool_name__}.",
                "Available configurations:",
                ", ".join(config.configurable),
            )
        ),
        nargs="*",
        type=partial(_validate_config_args, config),
    )

    required_group.add_argument(
        "-rc",
        "--restore-config",
        help="Restore configurations to defaults",
        action="store_true",
    )

    required_group.add_argument(
        "-clm",
        "--copy-language-metadata",
        help="Copy language metadata to a specified file",
    )

    # Target
    required_group.add_argument(
        "-d",
        "--dir",
        type=_validate_directory,
        help="Specify the directory to scan. Either this or '-f' must be used",
    )

    required_group.add_argument(
        "-f",
        "--file",
        type=_validate_filepath,
        help="Specify the file to scan. Either this or '-d' must be used",
    )

    # Parsing logic manipulation
    parser.add_argument(
        "-mc",
        "--min-chars",
        type=_validate_min_chars,
        help=" ".join(
            (
                "Specify the minimum number of non-whitespace characters a line",
                "should have to be considered an LOC",
            )
        ),
        default=config.minimum_characters,
    )

    parser.add_argument(
        "-lm",
        "--language-metadata",
        type=partial(
            _process_langauge_metadata_filepath, config
        ),  # kinda hacky, but we move
        help=" ".join(
            (
                "Specify JSON file to supply",
                "additional comment data for languages."
                "This file is read and used in",
                "addition to the default language metadata file,",
                "overwriting any overlapping entries",
            )
        ),
        default={},
    )

    # Directory parsing logic
    parser.add_argument(
        "-md",
        "--max-depth",
        help=" ".join(
            (
                "Recursively scan sub-directories upto the given level",
                "Negative values are treated as infinite depth",
            )
        ),
        type=_validate_max_depth,
        default=config.max_depth,
    )

    file_filter_group: argparse._MutuallyExclusiveGroup = (
        parser.add_mutually_exclusive_group()
    )

    file_filter_group.add_argument(
        "-xf", "--exclude-file", nargs="+", help="Exclude files by name"
    )

    file_filter_group.add_argument(
        "-if", "--include-file", nargs="+", help="Include files by name"
    )

    dir_filter_group: argparse._MutuallyExclusiveGroup = (
        parser.add_mutually_exclusive_group()
    )

    dir_filter_group.add_argument(
        "-xd", "--exclude-dir", nargs="+", help="Exclude sub-directories by name"
    )

    dir_filter_group.add_argument(
        "-id", "--include-dir", nargs="+", help="Include sub-directories by name"
    )

    type_filter_group: argparse._MutuallyExclusiveGroup = (
        parser.add_mutually_exclusive_group()
    )
    type_filter_group.add_argument(
        "-xt", "--exclude-type", nargs="+", help="Exclude files by extension"
    )

    type_filter_group.add_argument(
        "-it",
        "--include-type",
        nargs="+",
        help=" ".join(
            (
                "Include files by extension, useful for specificity",
                "when working with directories with files for different languages",
            )
        ),
    )

    # Output control
    parser.add_argument(
        "-vb",
        "--verbosity",
        type=_validate_verbosity,
        help=" ".join(
            (
                "Determine amount of details reported.",
                "Available:",
                ", ".join(k for k in Verbosity._value2member_map_),
            )
        ),
        default=config.verbosity,
    )

    parser.add_argument(
        "-o",
        "--output",
        help=" ".join(
            (
                "Specify output file to dump counts into.",
                "If not specified, output is dumped to stdout.",
                "If output file is in",
                f"{', '.join(k for k,v in OUTPUT_MAPPING.items() if v != dump_std_output)}",
                "then output is formatted differently.",
            )
        ),
    )

    parser.add_argument(
        "-pm",
        "--parsing-mode",
        type=_validate_parsing_mode,
        default=ParseMode.BUFFERED,
        help=" ".join(
            (
                "Override default file parsing behaviour.",
                "Available options:",
                ", ".join(ParseMode._value2member_map_.keys()),
            )
        ),
    )

    return parser


def parse_arguments(
    line: Sequence[str], parser: argparse.ArgumentParser
) -> argparse.Namespace:
    parsed_arguments: argparse.Namespace = parser.parse_args(line)

    # Additional validation rules not covered in parse_args
    configurations_args_length: int = len(parsed_arguments.config or [])
    if configurations_args_length % 2 != 0:
        raise ValueError(
            "Invalid syntax for configuration, must either be empty or in pairs"
        )

    # Format parsed_arguments.config into list of key, value pairs
    parsed_arguments.config = [
        (parsed_arguments.config[i], parsed_arguments.config[i + 1])
        for i in range(0, configurations_args_length - 1, 2)
    ]

    # Resolve file and directory paths relative to target directory
    if parsed_arguments.dir:
        for path_attribute in [
            "exclude_file",
            "include_file",
            "exclude_dir",
            "include_dir",
        ]:
            if paths := getattr(parsed_arguments, path_attribute, None):
                resolved_paths: list[str] = resolve_relative_paths(
                    parsed_arguments.dir, paths
                )
                setattr(parsed_arguments, path_attribute, resolved_paths)

        for path_attribute in ["include_file", "include_dir"]:
            missing_paths: list[str] = [
                path
                for path in getattr(parsed_arguments, path_attribute, []) or []
                if not os.path.exists(path)
            ]
            if missing_paths:
                raise SystemExit(
                    " ".join(
                        (
                            f"Inclusion path{'s' if len(missing_paths) > 1 else ''}",
                            "specified but missing:",
                            ", ".join(missing_paths),
                        )
                    )
                )

    return parsed_arguments
