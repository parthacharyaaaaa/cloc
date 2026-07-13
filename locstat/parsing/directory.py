import os
from array import array
from typing import Any, Callable, Iterator, Optional

from locstat.data_structures.config import ClocConfig
from locstat.data_structures.typing import FileParsingFunction
from locstat.data_structures.output_keys import OutputKeys
from locstat.parsing.file import (
    bare_file_parsing_wrapper,
    report_file_parsing_wrapper,
    verbose_file_parsing_wrapper,
)

__all__ = ("parse_directory", "parse_directory_record", "parse_directory_verbose")


def parse_directory(
    directory_data: Iterator[os.DirEntry[str]],
    config: ClocConfig,
    line_data: array,
    depth: int,
    file_parsing_function: FileParsingFunction,
    forbidden_directories: list[str],
    forbidden_files: list[str],
    file_filter_function: Callable[[str, str], bool] = lambda filename, extension: True,
    directory_filter_function: Callable = lambda _: False,
    minimum_characters: int = 0,
) -> None:
    """
    Parse directory and calculate LOC and total lines

    :param directory_data: Iterator over top directory
    :type directory_data: Iterator[os.DirEntry[str]]

    :param config: Caller's configuration instance
    :type config: ClocConfig

    :param line_data: 2-element integer sequence to store total lines and LOC
    :type line_data: array.array

    :param file_parsing_function: Parsing function called for each file
    :type config: FileParsingFunctionWrapper

    :param file_filter_function: Filter function to include/exclude files
    :type file_filter_function: Callable

    :param directory_filter_function: Filter function to exclude/include directories
    :type directory_filter_function: Callable

    :param minimum_characters: Minimum characters per line for it to be counted as a line of code
    :type minimum_characters: int

    :param depth: Sub-directory traversal depth
    :type depth: int

    :return: Passed line_data array is updated
    :rtype: NoneType
    """
    for dir_entry in directory_data:
        if dir_entry.is_symlink():
            continue
        if dir_entry.is_file(follow_symlinks=False):
            extension = dir_entry.name.rsplit(".", 1)[-1]
            if not file_filter_function(dir_entry.path, extension):
                continue

            single, multi_start, multi_end = config.symbol_mapping.get(
                extension, (None, None, None)
            )
            if not (single or multi_start):
                continue

            bare_file_parsing_wrapper(
                dir_entry.path,
                line_data,
                file_parsing_function,
                forbidden_files,
                single,
                multi_start,
                multi_end,
                minimum_characters,
            )
            continue

        if not depth:
            return
        if not directory_filter_function(dir_entry.path):
            continue

        try:
            parse_directory(
                os.scandir(dir_entry.path),
                config,
                line_data,
                depth - 1,
                file_parsing_function,
                forbidden_directories,
                forbidden_files,
                file_filter_function,
                directory_filter_function,
                minimum_characters,
            )
        except PermissionError:
            forbidden_directories.append(dir_entry.path)


def parse_directory_record(
    directory_data: Iterator[os.DirEntry[str]],
    config: ClocConfig,
    line_data: array,
    language_record: dict[str, dict[str, int]],
    depth: int,
    file_parsing_function: FileParsingFunction,
    forbidden_directories: list[str],
    forbidden_files: list[str],
    file_filter_function: Callable[[str, str], bool] = lambda filename, extension: True,
    directory_filter_function: Callable = lambda _: False,
    minimum_characters: int = 0,
) -> None:
    """
    Parse directory and calculate LOC and total lines, aggregating by file extensions as well

    :param directory_data: Iterator over top directory
    :type directory_data: Iterator[os.DirEntry[str]]

    :param config: Caller's configuration instance
    :type config: ClocConfig

    :param line_data: 2-element integer sequence to store total lines and LOC
    :type line_data: array.array

    :param language_record: Mapping to store total lines and LOC per file extension
    :type language_record: dict[str, dict[str, int]]

    :param file_parsing_function: Parsing function called for each file
    :type config: FileParsingFunctionWrapper

    :param file_filter_function: Filter function to include/exclude files
    :type file_filter_function: Callable

    :param directory_filter_function: Filter function to exclude/include directories
    :type directory_filter_function: Callable

    :param minimum_characters: Minimum characters per line for it to be counted as a line of code
    :type minimum_characters: int

    :param depth: Sub-directory traversal depth
    :type depth: int

    :return: Passed line_data array is updated
    :rtype: NoneType
    """
    for dir_entry in directory_data:
        if dir_entry.is_symlink():
            continue
        if dir_entry.is_file(follow_symlinks=False):
            extension = dir_entry.name.rsplit(".", 1)[-1]
            if not file_filter_function(dir_entry.path, extension):
                continue

            single, multi_start, multi_end = config.symbol_mapping.get(
                extension, (None, None, None)
            )
            if not (single or multi_start):
                continue

            language_record.setdefault(
                extension,
                {
                    OutputKeys.TOTAL: 0,
                    OutputKeys.LOC: 0,
                    OutputKeys.COMMENTED: 0,
                    OutputKeys.FILES: 0,
                },
            )
            report_file_parsing_wrapper(
                dir_entry.path,
                extension,
                line_data,
                language_record,
                file_parsing_function,
                forbidden_files,
                single,
                multi_start,
                multi_end,
                minimum_characters,
            )
            continue

        if not depth:
            return

        if not directory_filter_function(dir_entry.path):
            continue

        try:
            parse_directory_record(
                os.scandir(dir_entry.path),
                config,
                line_data,
                language_record,
                depth - 1,
                file_parsing_function,
                forbidden_directories,
                forbidden_files,
                file_filter_function,
                directory_filter_function,
                minimum_characters,
            )

            for extension in language_record:
                language_record[extension][OutputKeys.BLANK] = (
                    language_record[extension][OutputKeys.TOTAL]
                    - language_record[extension][OutputKeys.LOC]
                    - language_record[extension][OutputKeys.COMMENTED]
                )
        except PermissionError:
            forbidden_directories.append(dir_entry.path)


def parse_directory_verbose(
    directory_data: Iterator[os.DirEntry[str]],
    config: ClocConfig,
    language_record: dict[str, dict[str, int]],
    depth: int,
    file_parsing_function: FileParsingFunction,
    forbidden_directories: list[str],
    forbidden_files: list[str],
    file_filter_function: Callable[[str, str], bool] = lambda filename, extension: True,
    directory_filter_function: Callable = lambda _: False,
    minimum_characters: int = 0,
    *,
    output_mapping: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Parse directory and include aggregate data for all children files and subdirectories

    :param directory_data: Iterator over top directory
    :type directory_data: Iterator[os.DirEntry[str]]

    :param config: Caller's configuration instance
    :type config: ClocConfig

    :param language_record: Mapping to store total lines and LOC per file extension
    :type language_record: dict[str, dict[str, int]]

    :param file_parsing_function: Parsing function called for each file
    :type config: FileParsingFunctionWrapper

    :param file_filter_function: Filter function to include/exclude files
    :type file_filter_function: Callable

    :param directory_filter_function: Filter function to exclude/include directories
    :type directory_filter_function: Callable

    :param minimum_characters: Minimum characters per line for it to be counted as a line of code
    :type minimum_characters: int

    :param depth: Sub-directory traversal depth
    :type depth: int

    :param output_mapping: Mapping returned in recursive calls for aggregation.
    There is no need to pass arguments for this paraneter
    :type output_mapping: Optional[dict[str, Any]]

    :return: Mapping of LOC and line information
    :rtype: dict[str, Any]
    """

    if output_mapping is None:
        output_mapping = {}

    directory_total = directory_loc = directory_commented = 0
    files: dict[str, Any] = {}
    subdirectories: dict[str, Any] = {}

    for dir_entry in directory_data:
        if dir_entry.is_symlink():
            continue
        if dir_entry.is_file(follow_symlinks=False):
            extension = dir_entry.name.rsplit(".", 1)[-1]
            if not file_filter_function(dir_entry.path, extension):
                continue

            single, multi_start, multi_end = config.symbol_mapping.get(
                extension, (None, None, None)
            )

            if not (single or multi_end):
                continue
            language_record.setdefault(
                extension,
                {
                    OutputKeys.TOTAL: 0,
                    OutputKeys.LOC: 0,
                    OutputKeys.COMMENTED: 0,
                    OutputKeys.FILES: 0,
                },
            )

            file_total, file_loc, commented, blank = verbose_file_parsing_wrapper(
                dir_entry.path,
                extension,
                language_record,
                file_parsing_function,
                forbidden_files,
                single,
                multi_start,
                multi_end,
                minimum_characters,
            )
            if file_total > -1:
                language_record[extension][OutputKeys.TOTAL] += file_total
                language_record[extension][OutputKeys.LOC] += file_loc
                language_record[extension][OutputKeys.COMMENTED] += commented
                language_record[extension][OutputKeys.FILES] += 1

                directory_total += file_total
                directory_loc += file_loc
                directory_commented += commented

                files[dir_entry.path] = {
                    OutputKeys.LOC: file_loc,
                    OutputKeys.TOTAL: file_total,
                    OutputKeys.COMMENTED: commented,
                    OutputKeys.BLANK: blank,
                }

        elif depth and dir_entry.is_dir() and directory_filter_function(dir_entry.path):
            try:
                child = parse_directory_verbose(
                    os.scandir(dir_entry.path),
                    config,
                    language_record,
                    depth - 1,
                    file_parsing_function,
                    forbidden_directories,
                    forbidden_files,
                    file_filter_function,
                    directory_filter_function,
                    minimum_characters,
                )
            except PermissionError:
                forbidden_directories.append(dir_entry.path)
                continue

            subdirectories[dir_entry.name] = child
            directory_total += child[OutputKeys.TOTAL]
            directory_loc += child[OutputKeys.LOC]
            directory_commented += child[OutputKeys.COMMENTED]

    output_mapping.update(
        {
            OutputKeys.FILES: files,
            OutputKeys.SUBDIRECTORIES: subdirectories,
            OutputKeys.TOTAL: directory_total,
            OutputKeys.LOC: directory_loc,
            OutputKeys.COMMENTED: directory_commented,
            OutputKeys.BLANK: directory_total - directory_loc - directory_commented,
        }
    )

    for extension in language_record:
        language_record[extension][OutputKeys.BLANK] = (
            language_record[extension][OutputKeys.TOTAL]
            - language_record[extension][OutputKeys.LOC]
            - language_record[extension][OutputKeys.COMMENTED]
        )

    return output_mapping
