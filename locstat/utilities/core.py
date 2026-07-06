from pathlib import Path
from typing import Callable, Iterable, Optional

from locstat.data_structures.parse_modes import ParseMode
from locstat.data_structures.typing import SupportsMembershipChecks, FileParsingFunction
from locstat.parsing.extensions._parsing import (
    _parse_file_vm_map,
    _parse_file,
    _parse_file_no_chunk,
)

__all__ = ("construct_file_filter", "construct_directory_filter", "derive_file_parser")


def construct_file_filter(
    extension_set: Optional[SupportsMembershipChecks[str]] = None,
    file_set: Optional[SupportsMembershipChecks[str]] = None,
    include_file: bool = False,
    exclude_file: bool = False,
    include_type: bool = False,
    exclude_type: bool = False,
) -> Callable[[str, str], bool]:
    if extension_set is None:
        extension_set = {}
    if file_set is None:
        file_set = {}

    def file_filter(file: str, extension: str) -> bool:
        file_match = (
            True
            if not (include_file or exclude_file)
            else file in file_set if include_file else file not in file_set
        )

        type_match = (
            True
            if not (include_type or exclude_type)
            else (
                extension in extension_set
                if include_type
                else extension not in extension_set
            )
        )

        return file_match and type_match

    return file_filter


def construct_directory_filter(
    directories: Iterable[str],
    exclude: bool = False,
    include: bool = False,
) -> Callable[[str], bool]:
    directory_paths: frozenset[Path] = frozenset(Path(d) for d in directories)
    if include:
        return lambda directory: (
            (path := Path(directory)) in directory_paths
            or any(inc in path.parents for inc in directory_paths)
        )

    if exclude:
        return lambda directory: Path(directory) not in directory_paths
    return lambda directory: True


def derive_file_parser(option: ParseMode) -> FileParsingFunction:
    if option == ParseMode.MMAP:
        return _parse_file_vm_map
    elif option == ParseMode.COMPLETE:
        return _parse_file_no_chunk
    return _parse_file


def resolve_relative_paths(parent_directory: str, paths: Iterable[str]) -> list[str]:
    parent_path: Path = Path(parent_directory)
    return [
        (
            str((parent_path / path).resolve()).rstrip("\\/")
            if not Path(path).is_absolute()
            else path.rstrip("\\/")
        )
        for path in paths
    ]
