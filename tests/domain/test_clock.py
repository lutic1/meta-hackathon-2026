"""Story 1.8: `Clock` is a Protocol in the domain with no implementation (AD-1, AD-10)."""

import ast
import inspect
import sys
from typing import Protocol

from src.domain import clock as clock_module
from src.domain.clock import Clock


def test_clock_is_the_only_class_and_is_a_protocol():
    classes = [cls for _, cls in inspect.getmembers(clock_module, inspect.isclass) if cls.__module__ == clock_module.__name__]
    assert classes == [Clock]
    assert Protocol in Clock.__mro__ and getattr(Clock, "_is_protocol", False)
    assert Clock.__protocol_attrs__ == {"now_ms"}


def test_any_object_with_a_reading_satisfies_the_port():
    class Fixed:
        def now_ms(self) -> int:
            return 42_000

    def tick(clock: Clock) -> int:
        return clock.now_ms()

    assert tick(Fixed()) == 42_000


def test_the_module_reads_no_wall_clock_and_imports_only_the_standard_library():
    source = inspect.getsource(clock_module)
    assert "datetime" not in source and "import time" not in source and "perf_counter" not in source
    tops = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            tops.add((node.module or "").split(".")[0])
    assert tops and tops <= set(sys.stdlib_module_names) | {"__future__"}, tops
