from __future__ import annotations

import logging
import textwrap
from collections.abc import Mapping
from itertools import islice
from typing import Any, Callable, Sequence

from rich.logging import RichHandler


# Taken from Python 3.12 documentation.
def batched(iterable, n):
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


class IndentingRichHandler(RichHandler):
    _INDENT = ""
    _SINGLE_INDENT = "    "

    @classmethod
    def indent(cls):
        cls._INDENT += cls._SINGLE_INDENT

    @classmethod
    def dedent(cls):
        cls._INDENT = cls._INDENT[len(cls._SINGLE_INDENT) :]

    def emit(self, record: logging.LogRecord) -> None:
        if isinstance(record.msg, str):
            record.msg = textwrap.indent(record.msg, self._INDENT)
        return super().emit(record)


def format_table(
    headers: list[str],
    rows: Sequence[Mapping[str, Any]],
    row_selector: Callable[[str], str] | None = None,
    prefix="",
    rich_header: bool = True,
) -> list[str]:
    """Very simple table formatter"""
    lines = []
    row_selector = row_selector or (lambda x: x)
    max_lens = [
        max(len(h), *[len(row[row_selector(h)]) for row in rows]) for h in headers
    ]
    headings = [f"{h:{w}}" for h, w in zip(headers, max_lens)]
    if rich_header:
        headings = [f"[b]{x}[/b]" for x in headings]
    lines.append(prefix + " ".join(headings))
    for row in rows:
        lines.append(
            prefix
            + " ".join(
                [f"{row[row_selector(h)]:{w}}" for h, w in zip(headers, max_lens)]
            )
        )
    return lines
