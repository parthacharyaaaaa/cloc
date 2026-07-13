import textwrap
import array
import os
from tests.fixtures import mock_dir, mock_config
from pathlib import Path

from locstat.parsing.directory import parse_directory
from locstat.utilities.core import derive_file_parser
from locstat.data_structures.parse_modes import ParseMode


def _populate_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)

    src = directory / "src"
    tests = directory / "tests"
    data = directory / "data"
    utils = src / "utils"

    for d in (src, utils, tests, data):
        d.mkdir(parents=True, exist_ok=True)

    (src / "main.py").write_text(textwrap.dedent("""
            \"\"\"
            Entry point for the application.
            \"\"\"

            from utils.math_utils import add


            def main():
                # Simple execution flow
                result = add(2, 3)

                print("Result:", result)


            if __name__ == "__main__":
                main()
            """).strip() + "\n")

    (utils / "math_utils.py").write_text(textwrap.dedent("""
            \"\"\"
            Utility functions for math operations.
            \"\"\"


            def add(a: int, b: int) -> int:
                \"\"\"
                Add two integers.

                Args:
                    a: First integer
                    b: Second integer

                Returns:
                    The sum of a and b
                \"\"\"
                return a + b
            """).strip() + "\n")

    (tests / "test_math_utils.py").write_text(textwrap.dedent("""
            import pytest

            from src.utils.math_utils import add


            def test_add_basic():
                # Basic sanity check
                assert add(1, 2) == 3


            def test_add_negative_numbers():
                assert add(-1, -2) == -3
            """).strip() + "\n")

    (directory / "README.md").write_text(textwrap.dedent("""
            # Mock Project

            This is a fake project structure used for testing filesystem behavior.

            It intentionally includes:
            - Python code
            - Nested directories
            - Symlinks
            """).strip() + "\n")

    (data / "sample.txt").write_text(
        "This is a sample data file.\n\nIt has multiple lines.\n"
    )
    try:
        symlink_target = src / "main.py"
        symlink_path = directory / "main_link.py"

        if not symlink_path.exists():
            symlink_path.symlink_to(symlink_target)
    except (OSError, NotImplementedError):
        pass


def test_parse_mode_consistency(mock_dir, mock_config):
    _populate_directory(mock_dir)

    object.__setattr__(mock_config, "symbol_mapping", {"py": (b"#", None, None)})

    outputs: dict[ParseMode, array.array] = {}
    for parse_mode in ParseMode:
        result: array.array = array.array("L", (0, 0))
        mock_config.parsing_mode = parse_mode
        parse_directory(
            os.scandir(mock_dir),
            mock_config,
            result,
            -1,
            derive_file_parser(parse_mode),
            [],
            [],
        )
        outputs[parse_mode] = result

    assert len(set(tuple(o) for o in outputs.values())) == 1, " ".join(
        (
            "Parsing modes produce different outputs",
            "\n".join(
                f"{mode}: Total={total}, LOC={loc}"
                for mode, (total, loc) in outputs.items()
            ),
        )
    )
