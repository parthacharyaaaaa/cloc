from array import array
from typing import Optional

from locstat.data_structures.typing import FileLineData, FileParsingFunction
from locstat.data_structures.output_keys import OutputKeys


def file_parsing_wrapper(
    file_parsing_function: FileParsingFunction,
    filepath: str,
    singleline_symbol: bytes | None = None,
    multiline_start_symbol: bytes | None = None,
    multiline_end_symbol: bytes | None = None,
    minimum_characters: int = 0,
) -> FileLineData:
    try:
        return file_parsing_function(
            filepath,
            singleline_symbol,
            multiline_start_symbol,
            multiline_end_symbol,
            minimum_characters,
        )
    except PermissionError:
        raise SystemExit(f"Insufficient permissions to parse: {filepath}")


def bare_file_parsing_wrapper(
    filepath: str,
    line_data: array,
    file_parsing_function: FileParsingFunction,
    forbidden_files: list[str],
    singleline_symbol: Optional[bytes] = None,
    multiline_start_symbol: Optional[bytes] = None,
    multiline_end_symbol: Optional[bytes] = None,
    minimum_characters: int = 0,
    /,
) -> None:
    """Wrapper over C-extension file parsing functions to catch permission errors"""
    try:
        tl, l, c, *_ = file_parsing_function(
            filepath,
            singleline_symbol,
            multiline_start_symbol,
            multiline_end_symbol,
            minimum_characters,
        )
        line_data[0] += tl
        line_data[1] += l
        line_data[2] += c

    except PermissionError:
        forbidden_files.append(filepath)


def report_file_parsing_wrapper(
    filepath: str,
    extension: str,
    line_data: array,
    language_record: dict[str, dict[str, int]],
    file_parsing_function: FileParsingFunction,
    forbidden_files: list[str],
    singleline_symbol: Optional[bytes] = None,
    multiline_start_symbol: Optional[bytes] = None,
    multiline_end_symbol: Optional[bytes] = None,
    minimum_characters: int = 0,
    /,
) -> None:
    """Wrapper over C-extension file parsing functions to catch permission errors"""
    try:
        tl, l, c, *_ = file_parsing_function(
            filepath,
            singleline_symbol,
            multiline_start_symbol,
            multiline_end_symbol,
            minimum_characters,
        )
        line_data[0] += tl
        line_data[1] += l
        line_data[2] += c

        language_record[extension][OutputKeys.TOTAL] += tl
        language_record[extension][OutputKeys.LOC] += l
        language_record[extension][OutputKeys.COMMENTED] += c
        language_record[extension][OutputKeys.FILES] += 1
    except PermissionError:
        forbidden_files.append(filepath)


def verbose_file_parsing_wrapper(
    filepath: str,
    extension: str,
    language_record: dict[str, dict[str, int]],
    file_parsing_function: FileParsingFunction,
    forbidden_files: list[str],
    singleline_symbol: Optional[bytes] = None,
    multiline_start_symbol: Optional[bytes] = None,
    multiline_end_symbol: Optional[bytes] = None,
    minimum_characters: int = 0,
    /,
) -> FileLineData:
    """Wrapper over C-extension file parsing functions to catch permission errors"""
    try:
        file_total, file_loc, commented, blank = file_parsing_function(
            filepath,
            singleline_symbol,
            multiline_start_symbol,
            multiline_end_symbol,
            minimum_characters,
        )

        language_record[extension][OutputKeys.TOTAL] += file_total
        language_record[extension][OutputKeys.LOC] += file_loc
        language_record[extension][OutputKeys.COMMENTED] += commented
        language_record[extension][OutputKeys.FILES] += 1

        return file_total, file_loc, commented, blank
    except PermissionError:
        forbidden_files.append(filepath)
        return (-1, -1, -1, -1)
