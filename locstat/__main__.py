import argparse
import os
import platform
import sys
import time
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Final, NoReturn, Union

from locstat.argparser import initialize_parser, parse_arguments
from locstat import __version__, __tool_name__
from locstat.data_structures.config import ClocConfig
from locstat.data_structures.typing import FileParsingFunction, LanguageMetadata
from locstat.data_structures.verbosity import Verbosity
from locstat.data_structures.output_keys import OutputKeys
from locstat.parsing.directory import (
    parse_directory,
    parse_directory_record,
    parse_directory_verbose,
)
from locstat.utilities.core import (
    construct_directory_filter,
    construct_file_filter,
    derive_file_parser,
)
from locstat.utilities.presentation import (
    OUTPUT_MAPPING,
    OutputFunction,
    dump_std_output,
)

__all__ = ("main",)


def main() -> int:
    config: Final[ClocConfig] = ClocConfig.load_toml(
        Path(__file__).parent / "config.toml"
    )
    parser: Final[argparse.ArgumentParser] = initialize_parser(config)
    args: argparse.Namespace = parse_arguments(sys.argv[1:], parser)

    if args.version:
        print(f"{__tool_name__} {__version__}")
        return 0

    if args.restore_config:
        config.restore_configuration()
        return 0

    if args.copy_language_metadata:
        config.write_language_metadata(Path(args.copy_language_metadata))
        return 0

    # Because of nargs="*" in argparser's config argument,
    # the only way to determine whether --config was passed
    # is by negation of remaining args in the same mutually exclusive group
    if not (args.file or args.dir):
        if not args.config:  # View current configurations
            print(config.configurations_string)
            return 0

        for key, value in args.config:  # items in pairs
            config.update_configuration(key, value)
        return 0

    output_mapping: dict[str, Any] = {}

    file_parser_function: Final[FileParsingFunction] = derive_file_parser(
        args.parsing_mode
    )
    # Single file, no need to check and validate other default values
    if args.file:
        comment_data: LanguageMetadata = config.symbol_mapping.get(
            args.file.rsplit(".", 1)[-1], (None, None, None)
        )
        singleline_symbol, multiline_start_symbol, multiline_end_symbol = comment_data
        epoch: float = time.time()
        total, loc, commented_lines, blank = file_parser_function(
            args.file,
            singleline_symbol,
            multiline_start_symbol,
            multiline_end_symbol,
            args.min_chars,
        )

        output_mapping[OutputKeys.GENERAL] = {
            OutputKeys.LOC: loc,
            OutputKeys.TOTAL: total,
            OutputKeys.COMMENTED: commented_lines,
            OutputKeys.COMMENTED: blank,
        }

    else:
        extension_set: frozenset[str] = frozenset(
            extension for extension in (args.exclude_type or args.include_type or [])
        )
        file_set: frozenset[str] = frozenset(
            file for file in (args.exclude_file or args.include_file or [])
        )

        file_filter: Callable[[str, str], bool] = construct_file_filter(
            extension_set,
            file_set,
            bool(args.include_file),
            bool(args.exclude_file),
            bool(args.include_type),
            bool(args.exclude_type),
        )

        directory_filter: Callable[[str], bool] = lambda directory: True
        if args.include_dir or args.exclude_dir:
            directory_set: frozenset[str] = frozenset(
                directory for directory in (args.include_dir or args.exclude_dir)
            )
            directory_filter = construct_directory_filter(
                directory_set,
                include=bool(args.include_dir),
                exclude=bool(args.exclude_dir),
            )

        try:
            scandir_iterator: os._ScandirIterator = os.scandir(
                os.path.abspath(args.dir)
            )
        except PermissionError:
            raise SystemExit(f"Insufficient permissions to scan {args.dir}")

        kwargs: dict[str, Any] = {
            "directory_data": scandir_iterator,
            "config": config,
            "file_parsing_function": file_parser_function,
            "file_filter_function": file_filter,
            "directory_filter_function": directory_filter,
            "forbidden_files": [],
            "forbidden_directories": [],
            "minimum_characters": args.min_chars,
            "depth": args.max_depth,
        }
        output_mapping = {}
        epoch: float = time.perf_counter()
        if args.verbosity == Verbosity.BARE:
            line_data: array = array("L", (0, 0, 0))
            parse_directory(**kwargs, line_data=line_data)
            output_mapping[OutputKeys.GENERAL] = {
                OutputKeys.TOTAL: line_data[0],
                OutputKeys.LOC: line_data[1],
                OutputKeys.COMMENTED: line_data[2],
                OutputKeys.BLANK: line_data[0] - line_data[1] - line_data[2],
            }
        else:
            language_record: dict[str, dict[str, int]] = {}
            kwargs.update({"language_record": language_record})

            if args.verbosity == Verbosity.DETAILED:
                output_mapping.update(parse_directory_verbose(**kwargs))
                output_mapping[OutputKeys.GENERAL] = {
                    OutputKeys.TOTAL: output_mapping.pop(OutputKeys.TOTAL),
                    OutputKeys.LOC: output_mapping.pop(OutputKeys.LOC),
                    OutputKeys.COMMENTED: output_mapping.pop(OutputKeys.COMMENTED),
                    OutputKeys.BLANK: output_mapping.pop(OutputKeys.BLANK),
                }
            else:
                line_data: array = array("L", (0, 0, 0))
                parse_directory_record(**kwargs, line_data=line_data)
                output_mapping[OutputKeys.GENERAL] = {
                    OutputKeys.TOTAL: line_data[0],
                    OutputKeys.LOC: line_data[1],
                    OutputKeys.COMMENTED: line_data[2],
                    OutputKeys.BLANK: line_data[0] - line_data[1] - line_data[2],
                }

            output_mapping[OutputKeys.LANGUAGES] = language_record
        if kwargs["forbidden_files"]:
            output_mapping[OutputKeys.GENERAL][OutputKeys.FORBIDDEN_FILES] = (
                "\n" + "\n".join(kwargs["forbidden_files"])
            )
        if kwargs["forbidden_directories"]:
            output_mapping[OutputKeys.GENERAL][OutputKeys.FORBIDDEN_DIRECTORIES] = (
                "\n" + "\n".join(kwargs["forbidden_directories"])
            )

    general_metadata: dict[str, str] = {
        OutputKeys.TIME: f"{time.perf_counter()-epoch:.3f}s",
        OutputKeys.SCANNED_AT: datetime.now().strftime("%d/%m/%y, at %H:%M:%S"),
        OutputKeys.PLATFORM: platform.system(),
    }
    output_mapping[OutputKeys.GENERAL].update(general_metadata)  # type: ignore

    # Emit results
    output_file: Union[int, str] = sys.stdout.fileno()
    output_handler: OutputFunction = dump_std_output
    if args.output:
        assert isinstance(args.output, str)
        output_file = args.output.strip()
        output_extension: str = output_file.split(".")[-1]
        # Fetch output function based on file extension, default to standard write logic
        output_handler = OUTPUT_MAPPING.get(output_extension, output_handler)

    output_handler(output_mapping=output_mapping, filepath=output_file)
    return 0


def _run_guarded() -> NoReturn:
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stdout.write(f"{__tool_name__} interrupted\n")
        sys.exit()


if __name__ == "__main__":
    _run_guarded()
