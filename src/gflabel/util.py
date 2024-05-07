from __future__ import annotations

import logging
import textwrap
from typing import Callable

from rich.logging import RichHandler


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
    rows: list[dict[str, str]],
    row_selector: Callable[[str], str] | None = None,
    prefix="",
) -> list[str]:
    """Very simple table formatter"""
    lines = []
    row_selector = row_selector or (lambda x: x)
    max_lens = [
        max(len(h), *[len(row[row_selector(h)]) for row in rows]) for h in headers
    ]
    lines.append(prefix + " ".join([f"{h:{w}}" for h, w in zip(headers, max_lens)]))
    for row in rows:
        lines.append(
            prefix
            + " ".join(
                [f"{row[row_selector(h)]:{w}}" for h, w in zip(headers, max_lens)]
            )
        )
    return lines
