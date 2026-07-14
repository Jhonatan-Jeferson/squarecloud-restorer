from typing import Any, ParamSpec, TypeVar, cast
from collections.abc import Callable
from functools import wraps
from .__main__ import RestorerClient
from getpass import getpass

P = ParamSpec("P")
R = TypeVar("R")

def get_api_key(f: Callable[P, R]) -> Callable[P, R]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        client: RestorerClient = cast(RestorerClient, args[0])
        client.api_key = getpass("Insert Square Cloud API Key: ", echo_char="*")
        return f(*args, **kwargs)

    return wrapper


def sort_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_list = sorted(snapshots, key=lambda snapshot: snapshot["modified"])
    return sorted_list