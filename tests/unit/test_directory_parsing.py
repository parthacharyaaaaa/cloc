from array import array
import os
from pathlib import Path
from typing import Iterable

from locstat.parsing.directory import parse_directory
from tests.fixtures import mock_config, mock_dir
from locstat.parsing.extensions import _parsing


def _create_forbidden_files(mock_dir, dirnames: Iterable[str]) -> list[str]:
    path_sequence: list[Path] = [(mock_dir / dirname) for dirname in dirnames]
    for path in path_sequence:
        path.touch(0o777)

    return [str(path.resolve()) for path in path_sequence]


def _create_forbidden_dirs(mock_dir, dirnames: Iterable[str]) -> list[str]:
    path_sequence: list[Path] = [(mock_dir / dirname) for dirname in dirnames]
    for path in path_sequence:
        path.mkdir(0o777)
    return [str(path.resolve()) for path in path_sequence]


def test_forbidden_files(monkeypatch, mock_config, mock_dir) -> None:
    forbidden_file_names: tuple[str, ...] = ("foo.py", "bar.py", "foobar.py")

    real_file_parser = _parsing._parse_file

    def mock_file_parser(
        filename: str,
        singleline_symbol: bytes | None = None,
        multiline_start_symbol: bytes | None = None,
        multiline_end_symbol: bytes | None = None,
        minimum_characters: int = 0,
    ):
        print(filename)
        if filename.endswith(forbidden_file_names):
            raise PermissionError
        return real_file_parser(
            filename,
            singleline_symbol,
            multiline_start_symbol,
            multiline_end_symbol,
            minimum_characters,
        )

    monkeypatch.setattr(_parsing, "_parse_file", mock_file_parser)

    forbidden_paths = _create_forbidden_files(mock_dir, forbidden_file_names)
    setattr(mock_config, "symbol_mapping", {"py": (b"#", None, None)})
    output_array: array = array("L", (0, 0, 0))
    forbidden_files: list[str] = []
    parse_directory(
        os.scandir(mock_dir),
        mock_config,
        output_array,
        -1,
        _parsing._parse_file,
        [],
        forbidden_files,
    )

    if residue := set(forbidden_paths) - set(forbidden_files):
        raise ValueError(
            "\n".join(
                (
                    "Failed to detect all forbidden files.",
                    f"Remaining: {', '.join(residue)}",
                    f"Detected: {', '.join(forbidden_files)}",
                    f"Expected: {', '.join(forbidden_paths)}",
                )
            )
        )


def test_forbidden_directories(monkeypatch, mock_config, mock_dir) -> None:
    forbidden_dir_names: list[str] = ["foo", "bar", "foobar"]

    real_scandir = os.scandir

    def mock_os_scandir(path):
        if str(path).endswith(tuple(forbidden_dir_names)):
            raise PermissionError
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", mock_os_scandir)

    forbidden_paths = _create_forbidden_dirs(mock_dir, forbidden_dir_names)

    setattr(mock_config, "symbol_mapping", {"py": (b"#", None, None)})
    output_array: array = array("L", (0, 0, 0))
    forbidden_dirs: list[str] = []
    parse_directory(
        os.scandir(mock_dir),
        mock_config,
        output_array,
        -1,
        _parsing._parse_file,
        forbidden_dirs,
        [],
        directory_filter_function=lambda _: True,
    )

    if residue := set(forbidden_paths) - set(forbidden_dirs):
        raise ValueError(
            "\n".join(
                (
                    "Failed to detect all forbidden subdirectories.",
                    f"Remaining: {', '.join(residue)}",
                    f"Detected: {', '.join(forbidden_dirs)}",
                    f"Expected: {', '.join(forbidden_paths)}",
                )
            )
        )
