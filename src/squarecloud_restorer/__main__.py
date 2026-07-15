import sys
import importlib
from typing import Any, Callable, Self, Optional


cmd = importlib.import_module(".commands",package="squarecloud_restorer")

class RestorerClient:
    COMMANDS: dict[str, Callable[[Self], None]] = dict(
        filter(lambda data: (data[0] not in ['TYPE_CHECKING', 'json'] and not data[0].startswith('_') and data[1].__module__ == "squarecloud_restorer.commands"), cmd.__dict__.copy().items())
    )
    def __init__(self): 
        self.cli_args: list[str] = []
        self.exit_code: int = 0
        self.api_key: str = ""

    def error_handler(self, error: Exception):
        self.exit_code = 1
        print(str(error))

    def run(self, cli_args: list[str]):
        """This is the main entry of the CLI"""

        if len(cli_args) < 2: 
            self.COMMANDS["help"](self)
        else: 
            try: 
                command: tuple[str, ...] = tuple(filter(lambda arg: arg in self.COMMANDS.keys(), cli_args[1:]))
                self.cli_args = cli_args[1:]
                del self.cli_args[0]
                self.COMMANDS.get(command[0], self.COMMANDS["help"])(self)
            except Exception as error:
                self.error_handler(error)
            finally:
                sys.exit(self.exit_code)
                

def main(): 
    RestorerClient().run(sys.argv)

if __name__ == "__main__":
    main()