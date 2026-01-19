from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.resources
import logging
from enum import Enum, auto
from typing import Iterator, NamedTuple

import pint
from build123d import FontStyle, Path

logger = logging.getLogger(__name__)


class LabelStyle(Enum):
    EMBOSSED = auto()
    DEBOSSED = auto()
    EMBEDDED = auto()

    @classmethod
    def _missing_(cls, value):
        for kind in cls:
            if kind.name.lower() == value.lower():
                return kind

    def __str__(self):
        return self.name.lower()


class FontOptions(NamedTuple):
    font: str | None = None
    font_style: FontStyle = FontStyle.REGULAR
    font_path: Path | None = None

    # The font height, in mm. If this is unspecified, then the font will
    # be scaled to maximum area height, and then scaled down accordingly.
    # Setting this can explicitly cause overflow, as the text will be
    # unable to scale down if required.
    font_height_mm: float | None = None
    # Whether this is specifying exact font height
    font_height_exact: bool = True

    def get_allowed_height(self, requested_height: float) -> float:
        """Calculate the font height, accounting for option specifications"""
        if not requested_height:
            raise ValueError("Requested zero height")
        if self.font_height_exact:
            return self.font_height_mm or requested_height
        else:
            return min(self.font_height_mm or requested_height, requested_height)

    @contextlib.contextmanager
    def font_options(self) -> Iterator:
        """
        Handle loading of any font files, generating the kwargs to pass to build123d.Text
        """

        kwargs = {"font_style": self.font_style}
        if self.font_path:
            kwargs["font_path"] = str(self.font_path)
        # Need to work out if path is enough or if we also need name
        if self.font:
            kwargs["font"] = self.font

        with contextlib.ExitStack() as stack:
            # If we have no font, and no font path, then use the built-in ones
            if not self.font and not self.font_path:
                logger.debug("Falling back to internal font OpenSans")
                # This is a bit noisy but the way you are supposed to do it
                fontfile = stack.enter_context(
                    importlib.resources.as_file(
                        importlib.resources.files("gflabel").joinpath(
                            f"resources/OpenSans-{self.font_style.name.title()}"
                        )
                    )
                )

                kwargs["font_path"] = str(fontfile)

            yield kwargs


class RenderOptions(NamedTuple):
    line_spacing_mm: float = 0.1
    margin_mm: float = 0.4
    font: FontOptions = FontOptions()
    # Overheight fragments cause the entire line to be scaled down in
    # height so that they can fit. Is this allowed, or will they scale
    # like everything else?
    allow_overheight: bool = True
    column_gap: float = 0.4

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> RenderOptions:
        font_style = [
            x for x in FontStyle if x.name.lower() == args.font_style.lower()
        ][0]
        margin_mm = args.margin
        if isinstance(args.margin, pint.Quantity):
            if not args.margin.check("[length]"):
                raise ValueError(
                    "Got non-length dimension pint quantity for args.margin"
                )
            margin_mm = args.margin.to("mm").magnitude
        assert margin_mm is not None, (
            "Margin should have been set either by user or defaults"
        )
        return cls(
            margin_mm=margin_mm,
            font=FontOptions(
                font=args.font,
                font_style=font_style,
                font_height_mm=args.font_size or args.font_size_maximum,
                font_height_exact=not args.font_size_maximum,
                font_path=args.font_path,
            ),
            allow_overheight=not args.no_overheight,
            column_gap=args.column_gap,
        )
