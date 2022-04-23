import sys
from typing import Any, TypedDict

class A:
    """
    Ansi helpers
    """
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    gray = "\033[37m"

    clear = "\033[0m"

class Verbosity(TypedDict):
    value: int

verbosity: Verbosity = { "value": 1 }

def pprint(*args: Any, **kwargs: Any) -> None:
    """
    A pretty print helper functions. Takes an additional keyword "color"
    """
    if verbosity["value"] >= 1:
        needs_clear = False

        if "color" in kwargs:
            sys.stdout.write(kwargs["color"])
            needs_clear = True
            del kwargs["color"]

        print(*args, **kwargs)

        if needs_clear:
            sys.stdout.write(A.clear)
