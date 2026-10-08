from collections.abc import Generator
from typing import Any

from plastron.context import PlastronContext


class BaseCommand:
    def __init__(self, context: PlastronContext):
        self.context = context
        self.result = None

    @property
    def config(self) -> dict[str, Any]:
        name = self.__module__.split('.')[-1]
        if name == 'importcommand':
            name = 'import'
        return self.context.config.get('COMMANDS', {}).get(name.upper(), {})

    def _run(self, command: Generator[dict[str, Any], None, dict[str, Any]]):
        # delegating generator; each progress step is passed to the calling
        # method, and the return value from the command is stored as the result
        self.result = yield from command

    def run(self, command: Generator[Any, None, dict[str, Any]]) -> dict[str, Any]:
        # Run the delegating generator to exhaustion, discarding the intermediate
        # yielded values. Return the final result.
        for _ in self._run(command):
            pass
        return self.result
