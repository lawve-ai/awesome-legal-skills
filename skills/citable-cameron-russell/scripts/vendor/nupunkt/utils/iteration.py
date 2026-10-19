"""
Iteration utilities for nupunkt.

This module provides utility functions for iterating through sequences
with specialized behaviors needed for the Punkt algorithm.
"""

from typing import Any, Iterable, Iterator, Sequence, TypeVar

T = TypeVar("T")


def pair_iter(iterable: Iterable[Any]) -> Iterator[tuple[Any, Any | None]]:
    """
    Iterate through pairs of items from an iterable, where the second item
    can be None for the last item.

    Args:
        iterable: The input iterable (list, tuple, or any iterable)

    Yields:
        Pairs of (current_item, next_item) where next_item is None for the last item
    """
    it = iter(iterable)
    prev = next(it, None)
    if prev is None:
        return
    for current in it:
        yield prev, current
        prev = current
    yield prev, None


def pair_iter_fast(items: Sequence[T]) -> Iterator[tuple[T, T | None]]:
    """
    Fast implementation of pair iteration for sequences (lists, tuples).
    This avoids the iterator overhead for known sequence types.

    Args:
        items: A sequence (list or tuple) to iterate through in pairs

    Yields:
        Pairs of (current_item, next_item) where next_item is None for the last item
    """
    length = len(items)
    if length == 0:
        return

    # Handle all but the last item
    for i in range(length - 1):
        yield items[i], items[i + 1]

    # Handle the last item (with None as the next item)
    yield items[length - 1], None
