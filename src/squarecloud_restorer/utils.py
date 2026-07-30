from typing import Any, ParamSpec, TypeVar, cast, TYPE_CHECKING
from collections.abc import Callable
from functools import wraps
from getpass import getpass

if TYPE_CHECKING:
    from .__main__ import RestorerClient

P = ParamSpec("P")
R = TypeVar("R")

def require_api_key(f: Callable[P, R]) -> Callable[P, R]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        client = cast("RestorerClient", args[0])
        client.api_key = getpass("Insert Square Cloud API Key: ", echo_char="*")
        return f(*args, **kwargs)

    return wrapper


def sort_snapshots(snapshots: list[dict[str, Any]], reverse: bool = False) -> list[dict[str, Any]]:
    sorted_list = sorted(snapshots, key=lambda snapshot: snapshot["modified"], reverse=reverse)
    return sorted_list