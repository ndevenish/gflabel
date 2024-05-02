from __future__ import annotations

import argparse
from enum import Enum, auto
from typing import NamedTuple

from build123d import FontStyle


class LabelStyle(Enum):
    EMBOSSED = auto()
    DEBOSSED = auto()

    @classmethod
    def _missing_(cls, value):
        for kind in cls:
            if kind.name.lower() == value.lower():
                return kind

    def __str__(self):
        return self.name.lower()


class FontOptions(NamedTuple):
    font: str = "Futura"
    font_style: FontStyle = FontStyle.BOLD
    # The font height, in mm. If this is unspecified, then the font will
    # be scaled to maximum area height, and then scaled down accordingly.
    # Setting this can explicitly cause overflow, as the text will be
    # unable to scale down if required.
    font_height_mm: float | None = None


class RenderOptions(NamedTuple):
    line_spacing_mm: float = 0.1
    margin_mm: float = 0.4
    font: FontOptions = FontOptions()
    # Overheight fragments cause the entire line to be scaled down in
    # height so that they can fit. Is this allowed, or will they scale
    # like everything else?
    allow_overheight: bool = True

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> RenderOptions:
        font_style = [
            x for x in FontStyle if x.name.lower() == args.font_style.lower()
        ][0]
        return cls(
            margin_mm=args.margin,
            font=FontOptions(
                font=args.font,
                font_style=font_style,
                font_height_mm=args.font_size,
            ),
            allow_overheight=not args.no_overheight,
        )
