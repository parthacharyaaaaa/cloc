from enum import StrEnum

__all__ = ("OutputKeys",)


class OutputKeys(StrEnum):
    GENERAL = "general"
    TOTAL = "total"
    LOC = "loc"
    COMMENTED = "comments"
    BLANK = "blank"

    FILES = "files"
    SUBDIRECTORIES = "subdirectories"
    LANGUAGES = "languages"

    TIME = "time"
    SCANNED_AT = "scanned"
    PLATFORM = "platform"

    FORBIDDEN_FILES = "FORBIDDEN_FILES"
    FORBIDDEN_DIRECTORIES = "FORBIDDEN_DIRECTORIES"
