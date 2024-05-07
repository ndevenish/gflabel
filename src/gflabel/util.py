from __future__ import annotations

import logging
import textwrap

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
