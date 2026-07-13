"""Unit tests for CLI argument parser"""

import argparse

from locstat.argparser import initialize_parser, parse_arguments

from tests.fixtures import mock_config, mock_dir


def test_exclusive_groups(mock_config, mock_dir) -> None:
    parser: argparse.ArgumentParser = initialize_parser(mock_config)

    illegal_combinations: tuple[str, ...] = (
        "-it py -xt js",
        "-if foo.py -xf bar.py",
        "-id foo -xd bar",
    )

    base_args: str = f"-d {mock_dir}"

    for combination in illegal_combinations:
        failed: bool = False
        try:
            parse_arguments(" ".join((base_args, combination)).split(), parser)
        except SystemExit:
            failed = True
        finally:
            assert (
                failed
            ), f"Illegal argument combination '{combination}' accepted by argument parser"


def test_allowed_combinations(mock_config, mock_dir):
    parser: argparse.ArgumentParser = initialize_parser(mock_config)

    temp_files: list[str] = ["foo.py", "bar.py"]
    temp_subdirs: list[str] = ["foo", "bar"]
    for temp_file in temp_files:
        (mock_dir / temp_file).touch()
    for temp_subdir in temp_subdirs:
        (mock_dir / temp_subdir).mkdir()

    legal_args: tuple[str, ...] = (
        "-it py cpp c",
        "-xt py cpp c",
        f"-if {' '.join(temp_files)}",
        f"-xf {' '.join(temp_files)}",
        f"-id {' '.join(temp_subdirs)}",
        f"-xd {' '.join(temp_subdirs)}",
    )

    base_args: str = f"-d {mock_dir}"

    for arg in legal_args:
        cli_arg: str = " ".join((base_args, arg))
        try:
            parse_arguments(cli_arg.split(), parser)
        except SystemExit as e:
            e.add_note(f"Original argument: {cli_arg}")
            raise e


def test_target_existence(mock_config, mock_dir):
    parser: argparse.ArgumentParser = initialize_parser(mock_config)

    mock_subdir = mock_dir / "_temp_subdir"
    mock_file = mock_subdir / "_temp_file.py"

    arg_mapping: dict[str, type[BaseException]] = {
        f"-f {mock_file}": SystemExit,
        f"-d {mock_subdir}": SystemExit,
    }

    for arg, expected_exception in arg_mapping.items():
        failed: bool = False
        arg_sequence: list[str] = arg.split()
        try:
            parse_arguments(arg_sequence, parser)
        except SystemExit as e:
            assert isinstance(e, expected_exception), " ".join(
                (
                    f"Non-existing target {arg_sequence[-1]} rejected with unexpected error",
                    f"Expected: {expected_exception}",
                    f"Raised: {e}",
                )
            )
            failed = True
        assert failed, f"Non-existing target {arg_sequence[-1]} accepted"

    mock_subdir.mkdir()
    mock_file.touch()

    for arg in arg_mapping:
        parse_arguments(arg.split(), parser)
