import json
import os
from io import TextIOWrapper
from types import MappingProxyType
from typing import Any, Final, Optional, Sequence, Union

from locstat.data_structures.typing import OutputFunction
from locstat.data_structures.output_keys import OutputKeys

__all__ = ("dump_std_output", "dump_json_output", "OUTPUT_MAPPING")


def _format_row(row: Sequence[Union[str, int]], widths: Sequence[int]) -> str:
    return (
        f"{row[0]:<{widths[0]}}  "
        f"{row[1]:>{widths[1]}}  "
        f"{row[2]:>{widths[2]}}  "
        f"{row[3]:>{widths[3]}}  "
        f"{row[4]:>{widths[4]}}  "
        f"{row[5]:>{widths[5]}}\n"
    )


def _dump_directory_tree(
    file: TextIOWrapper,
    name: str,
    node: dict[str, Any],
    prefix: str = "",
    is_last: bool = True,
) -> None:
    connector: str = "└── " if is_last else "├── "
    next_prefix: str = prefix + ("    " if is_last else "│   ")
    total, loc, commented, blank = (
        node.get(OutputKeys.TOTAL),
        node.get(OutputKeys.LOC),
        node.get(OutputKeys.COMMENTED),
        node.get(OutputKeys.BLANK),
    )
    header = f"{name}/ ({OutputKeys.TOTAL}={total}, {OutputKeys.LOC}={loc}, {OutputKeys.COMMENTED}={commented}, {OutputKeys.BLANK}={blank})"

    file.write(f"{prefix}{connector}{header}\n")

    files: dict[str, Any] = node.get(OutputKeys.FILES, {})
    file_items: list[tuple[str, dict[str, int]]] = sorted(files.items())

    for idx, (path, meta) in enumerate(file_items):
        is_last_file: bool = idx == len(file_items) - 1 and not node.get(
            OutputKeys.SUBDIRECTORIES
        )
        file_connector: str = "└── " if is_last_file else "├── "
        fname = os.path.basename(path)

        write_data: str = ", ".join(
            (
                f"total={meta.get(OutputKeys.TOTAL)}",
                f"loc={meta.get(OutputKeys.LOC)})",
                f"commented={meta.get(OutputKeys.COMMENTED)}",
                f"blank={meta.get(OutputKeys.BLANK)}",
            )
        )
        file.write(f"{next_prefix}{file_connector}" f"{fname} {write_data}\n")

    subdirs = node.get(OutputKeys.SUBDIRECTORIES, {})
    sub_items = sorted(subdirs.items())

    for idx, (subname, subnode) in enumerate(sub_items):
        _dump_directory_tree(
            file,
            subname,
            subnode,
            prefix=next_prefix,
            is_last=idx == len(sub_items) - 1,
        )


def _sort_output_mapping(output_mapping: dict[str, Any]) -> None:
    output_mapping[OutputKeys.GENERAL] = dict(
        sorted(
            output_mapping[OutputKeys.GENERAL].items(),
            key=lambda x: x[0]
            in (OutputKeys.FORBIDDEN_DIRECTORIES, OutputKeys.FORBIDDEN_FILES),
        )
    )


def dump_std_output(
    output_mapping: dict[str, Any], filepath: Union[str, os.PathLike[str], int]
) -> None:
    """
    Dump output to a standard text/log file

    :param output_mapping: resultant mapping
    :type output_mapping: dict[str, Any]

    :param filepath: Output file to write results to, can be stdout
    :type filepath: Union[str, os.PathLike[str], int]

    :param mode: Writing mode
    :type mode: Literal["w+", "a"]
    """
    assert isinstance(output_mapping[OutputKeys.GENERAL], dict)
    _sort_output_mapping(output_mapping)
    with open(filepath, "w") as file:
        file.write(f"{OutputKeys.GENERAL.capitalize()}:\n")
        file.write(
            "\n".join(
                f"{field.capitalize()} : {value}"
                for field, value in (output_mapping[OutputKeys.GENERAL]).items()
            )
        )

        file.write("\n\n")

        languages: Optional[dict[str, dict[str, int]]] = output_mapping.pop(
            OutputKeys.LANGUAGES, None
        )
        if languages:
            headers: list[str] = [
                "Extension",
                OutputKeys.FILES.capitalize(),
                OutputKeys.TOTAL.capitalize(),
                OutputKeys.LOC.upper(),
                OutputKeys.COMMENTED.capitalize(),
                OutputKeys.BLANK.capitalize(),
            ]

            rows = [
                (
                    lang,
                    data[OutputKeys.FILES],
                    data[OutputKeys.TOTAL],
                    data[OutputKeys.LOC],
                    data[OutputKeys.COMMENTED],
                    data[OutputKeys.BLANK],
                )
                for lang, data in languages.items()
            ]

            widths = [
                max(len(str(col)) for col in column) for column in zip(headers, *rows)
            ]

            file.write(f"{OutputKeys.LANGUAGES.capitalize()}\n")
            file.write(_format_row(headers, widths))
            file.write("-" * (sum(widths) + 12))
            file.write("\n")

            for row in rows:
                file.write(_format_row(row, widths))

        tree = output_mapping.get(OutputKeys.SUBDIRECTORIES)
        if tree:
            file.write(
                f"\n{OutputKeys.FILES.capitalize()} & {OutputKeys.SUBDIRECTORIES.capitalize()}\n"
            )
            for idx, (name, node) in enumerate(sorted(tree.items())):
                _dump_directory_tree(
                    file,
                    name,
                    node,
                    prefix="",
                    is_last=idx == len(tree) - 1,
                )


def dump_json_output(
    output_mapping: dict[str, Any], filepath: Union[str, os.PathLike[str], int]
) -> None:
    """Dump output to JSON file, with proper formatting"""
    _sort_output_mapping(output_mapping)
    is_file_descriptor: bool = isinstance(filepath, int)
    if not (is_file_descriptor or os.path.abspath(filepath)):
        filepath = os.path.join(os.getcwd(), filepath)

    with open(filepath, mode="w") as output_file:
        output_file.write(json.dumps(output_mapping, indent=2))


OUTPUT_MAPPING: Final[MappingProxyType[str, OutputFunction]] = MappingProxyType(
    {
        "json": dump_json_output,
    }
)
