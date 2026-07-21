import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from injector import Injector

from jjjexperiment.common import (
    clear_current_injector,
    get_current_injector,
    injector_context,
    set_current_injector,
)


def test_legacy_set_and_clear_api_remains_compatible():
    injector = Injector()

    set_current_injector(injector)
    assert get_current_injector() is injector

    clear_current_injector()
    assert get_current_injector() is None


def test_injector_context_restores_nested_state():
    outer = Injector()
    inner = Injector()

    assert get_current_injector() is None

    with injector_context(outer):
        assert get_current_injector() is outer

        with injector_context(inner):
            assert get_current_injector() is inner

        assert get_current_injector() is outer

    assert get_current_injector() is None


def test_injector_context_restores_state_after_error():
    injector = Injector()

    with pytest.raises(RuntimeError, match="calculation failed"):
        with injector_context(injector):
            assert get_current_injector() is injector
            raise RuntimeError("calculation failed")

    assert get_current_injector() is None


def test_injector_context_is_isolated_between_threads():
    injectors = [Injector(), Injector()]
    barrier = Barrier(len(injectors))

    def current_in_context(injector):
        with injector_context(injector):
            barrier.wait()
            return get_current_injector()

    with ThreadPoolExecutor(max_workers=2) as executor:
        actual = list(executor.map(current_in_context, injectors))

    assert actual == injectors
    assert get_current_injector() is None


def test_injector_context_is_isolated_between_async_tasks():
    injectors = [Injector(), Injector()]

    async def current_after_yield(injector):
        with injector_context(injector):
            await asyncio.sleep(0)
            return get_current_injector()

    async def run_tasks():
        return await asyncio.gather(*(current_after_yield(item) for item in injectors))

    assert asyncio.run(run_tasks()) == injectors
    assert get_current_injector() is None
