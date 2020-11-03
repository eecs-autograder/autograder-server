import sys
from typing import Optional


def stderr(
    *values: object,
    sep: Optional[str] = None,
    end: Optional[str] = None,
    flush: bool = False
) -> None:
    """
    Thin wrapper for print() that sends output to stderr.
    Use for debugging schema generation.
    """
    print(*values, sep=sep, end=end, file=sys.stderr, flush=flush)
